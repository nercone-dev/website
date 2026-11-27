import traceback

from fwid import FWID

from fastapi import Response
from fastapi.responses import PlainTextResponse

from typing import Optional

from starlette.types import ASGIApp, Message, Scope, Receive, Send
from starlette.requests import Request

from .logger import log_access, log_error
from .helpers import URL, CommaHeader, CacheControl, ContentSecurityPolicy, PermissionsPolicy, ServerTiming, Minifier, Compressor, compute_xxhash3
from .renderer import render_error_page
from .constants import Startup, StartupMode, Hostnames, Ports

class Middleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            if scope["type"] not in ["http", "websocket"]:
                await self.app(scope, receive, send)
                return

            request_headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
            request_host, request_port = URL.parse_authority(request_headers.get("host", ""))
            request_path = (scope.get("raw_path") or scope.get("path", "/").encode("utf-8")).decode("latin-1") or "/"

            scope.update({"nercone": {
                "logged": False,
                "request": {
                    "id": FWID(),
                    "url": URL(scope.get("scheme", "http"), request_host, request_port, request_path, scope.get("query_string", b"").decode("latin-1"), ""),
                    "headers": request_headers,
                },
                "response": {
                    "compression": True,
                    "headers": {
                        "cache-control": CacheControl(),
                        "content-security-policy": ContentSecurityPolicy(),
                        "permissions-policy": PermissionsPolicy(),
                        "server-timing": ServerTiming(),
                    },
                },
            }})

            state = scope["nercone"]
            timings: ServerTiming = state["response"]["headers"]["server-timing"]
            timings.start("total", "Total")

            if Startup.mode == StartupMode.DEVELOPMENT:
                for key in ("script-src", "style-src", "font-src", "img-src"):
                    state["response"]["headers"]["content-security-policy"].append(key, f"localhost:{Ports.tcp_port}")

            host = state["request"]["headers"].get("host", "")
            hostname = host.split(":")[0].strip()
            subdomain = next((hostname[:-(len(candidate) + 1)] for candidate in Hostnames.all if hostname.endswith("." + candidate)), "")

            if Startup.mode == StartupMode.DEVELOPMENT and not Hostnames.matches(hostname):
                response = PlainTextResponse("許可されていないホスト名でのアクセスです。", 403)
                await self.send(response, scope, receive, send)
                return

            if len(scope.get("path", "")) + len(scope.get("query_string", b"")) > 256:
                response = await render_error_page(Request(scope=scope, receive=receive), status_code=414)
                await self.send(response, scope, receive, send)
                return

            if scope["method"] == "OPTIONS":
                response = Response(status_code=204)
                await self.send(response, scope, receive, send)
                return

            timings.start("receive", "Read body")
            body = await self.read_body(receive)
            timings.stop("receive")

            if subdomain in ["", "www"]:
                response = await self.get_response(scope, Middleware.replay(body, receive), scope["path"], "app", "ASGI App Total")
                await self.send(response, scope, receive, send)

            else:
                original_path = scope["path"] if scope["path"].strip() else "/"
                subdomain_path = f"/{'/'.join(subdomain.split('.')[::-1])}{original_path}"

                response = await self.get_response(scope, Middleware.replay(body, receive), subdomain_path, "app", "ASGI App Total")
                if not 400 <= response.status_code < 500:
                    await self.send(response, scope, receive, send)
                    return

                response = await self.get_response(scope, Middleware.replay(body, receive), original_path, "app-retry", "ASGI App Total (Retry)")
                await self.send(response, scope, receive, send)

        except Exception:
            try:

                try:
                    id = scope["nercone"]["request"]["id"] if "nercone" in scope else FWID()
                    log_error(id, traceback.format_exc())
                except Exception:
                    pass

                await self.send(await render_error_page(Request(scope=scope, receive=receive), status_code=500), scope, receive, send)

            except Exception:
                await PlainTextResponse("Internal Server Error", status_code=500)(scope, receive, send)

    async def get_response(self, scope: Scope, receive: Receive, path: str, key: str, description: Optional[str] = None) -> Response:
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        new_scope = dict(scope, path=path)

        status_code = 200
        response_headers = []
        body_parts = []

        async def capture_send(message: Message) -> None:
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        timings: ServerTiming = scope["nercone"]["response"]["headers"]["server-timing"]
        timings.start(key, description)
        await self.app(new_scope, receive, capture_send)
        timings.stop(key)

        response = Response(content=b"".join(body_parts), status_code=status_code)

        for k, v in response_headers:
            response.headers.raw.append((k, v))

        return response

    @staticmethod
    def replay(body: bytes, receive: Receive) -> Receive:
        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return replay_receive

    async def read_body(self, receive: Receive) -> bytes:
        parts = []
        while True:
            message = await receive()
            if chunk := message.get("body"):
                parts.append(chunk)
            if not message.get("more_body", False):
                break
        return b"".join(parts)

    async def send(self, response: Response, scope: Scope, receive: Receive, send: Send) -> None:
        state = scope["nercone"]
        timings: ServerTiming = state["response"]["headers"]["server-timing"]

        def set_header(key: str, value: str, override: bool = True, condition: bool = True) -> None:
            if condition and (override or key.title() not in response.headers):
                response.headers[key.title()] = value

        def add_vary(*headers: str, condition: bool = True) -> None:
            if condition:
                vary = CommaHeader(response.headers.get("vary", ""))
                for header in headers:
                    vary.append(header)
                set_header("Vary", vary.build())

        content_type = response.headers.get("content-type", "")

        # Minification
        Minifier.apply(response)

        # Development
        if content_type.startswith(("text/html", "text/css", "text/javascript", "application/javascript", "image/svg+xml")) and Startup.mode == StartupMode.DEVELOPMENT:
            netloc = state["request"]["headers"].get("host", "") or f"localhost:{Ports.tcp_port}"
            origin = f"{scope.get('scheme', 'http')}://{netloc}"
            response.body = bytes(response.body).replace(b"https://api.nercone.dev/",    f"{origin}/api/".encode())
            response.body = bytes(response.body).replace(b"https://assets.nercone.dev/", f"{origin}/assets/".encode())

        # Compression
        if state["response"]["compression"] and "content-encoding" not in response.headers and Compressor.compressible(content_type, len(response.body)):
            encoding = Compressor.negotiate(state["request"]["headers"].get("accept-encoding"))
            if encoding is not None:
                timings.start("compress", f"Compress ({encoding})")
                response.body = Compressor.compress(bytes(response.body), encoding)
                timings.stop("compress")

                set_header("Content-Encoding", encoding)

        # Information
        set_header("Content-Length", str(len(response.body)))
        set_header("Link", "<https://nercone.dev/sitemap.xml>; rel=\"sitemap\", <https://nercone.dev/robots.txt>; rel=\"robots\"")

        # Proxy
        set_header("X-Content-Type-Options", "nosniff")

        # Cache
        if Startup.mode == StartupMode.DEVELOPMENT:
            set_header("Cache-Control", "no-store")
        elif not state["response"]["headers"]["cache-control"].initial:
            set_header("Cache-Control", state["response"]["headers"]["cache-control"].header)
        elif content_type.startswith("font/"):
            set_header("Cache-Control", "max-age=604800")
        elif content_type.startswith(("text/css", "text/javascript", "application/javascript")):
            set_header("Cache-Control", "max-age=43200")
        else:
            set_header("Cache-Control", "no-cache")

        # Report
        set_header("Reporting-Endpoints", "default=\"https://nercone.dev/report/\", csp-endpoint=\"https://nercone.dev/report/csp/\"")

        # Security
        set_header("Referrer-Policy", "strict-origin-when-cross-origin")
        set_header("Permissions-Policy", state["response"]["headers"]["permissions-policy"].header)
        set_header("Content-Security-Policy", state["response"]["headers"]["content-security-policy"].header)

        set_header("X-Frame-Options", "SAMEORIGIN")

        # Security: Cross-Origin
        origin = state["request"]["headers"].get("origin", "").strip()
        origin_hostname = origin.removeprefix("https://").removeprefix("http://").split("/")[0].split(":")[0]

        add_vary("Origin", "Accept-Encoding")

        if "text/html" in content_type:
            set_header("Cross-Origin-Opener-Policy", "same-origin", override=False)

        if content_type.startswith(("text/css", "text/javascript", "application/javascript", "font/", "image/")):
            set_header("Cross-Origin-Resource-Policy", "cross-origin", override=False)

            set_header("Access-Control-Allow-Origin", "*", override=False)
            set_header("Access-Control-Allow-Headers", "*", override=False)

        else:
            set_header("Cross-Origin-Resource-Policy", "same-origin", override=False)

            if Hostnames.matches(origin_hostname):
                add_vary("Origin")

                set_header("Access-Control-Allow-Origin", origin, override=False)
                set_header("Access-Control-Allow-Credentials", "true", override=False)

                if scope["method"] == "OPTIONS":
                    set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS", override=False)
                    set_header("Access-Control-Allow-Headers", state["request"]["headers"].get("access-control-request-headers") or "Content-Type, Authorization, X-Requested-With", override=False)
                    set_header("Access-Control-Max-Age", "86400", override=False)

        # ETag / 304 Not Modified
        timings.start("etag", "ETag (xxHash3)")
        etag = compute_xxhash3(bytes(response.body))
        timings.stop("etag")

        etag_matches = state["request"]["headers"].get("if-none-match", "") == etag
        if etag_matches:
            not_modified = Response(status_code=304)
            for key, value in response.headers.raw:
                if key.lower() not in (b"content-length", b"content-type", b"content-encoding"):
                    not_modified.headers.raw.append((key, value))
            response = not_modified

        set_header("ETag", etag)

        # Debug
        set_header("X-Request-Id", state["request"]["id"].text())

        timings.stop("total")
        set_header("Server-Timing", timings.header)

        if not state["logged"]:
            log_access(Request(scope=scope, receive=receive), response)
            state["logged"] = True

        await response(scope, receive, send)
