import gzip
import zlib
import xxhash
import functools
import traceback
import ipaddress
import zstandard
import brotlicffi
from fourword.lib import FourWord
from fastapi import Response
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.requests import Request, HTTPConnection

import minify_html as rhtmin
import rjsmin
import rcssmin
from scour import scour

from .constants import Directories, Files, Repository, Hostnames
from .logger import log_access, log_error
from .models import PPManager, CSPManager, CCManager, TimingManager, NetworkManager, OptionManager
from .renderer import render_error_page
from .databases import AccessCounter

templates = Jinja2Templates(directory=Directories.public)
accesscounter = AccessCounter()

scour_options = scour.generateDefaultOptions()
scour_options.newlines = False
scour_options.shorten_ids = True
scour_options.strip_comments = True

@functools.lru_cache(maxsize=512)
def compute_etag(body: bytes) -> str:
    return '"' + xxhash.xxh3_128(body).hexdigest() + '"'

@functools.lru_cache(maxsize=128)
def compress_zstd(body: bytes) -> bytes:
    return zstandard.ZstdCompressor(level=3).compress(body)

@functools.lru_cache(maxsize=128)
def compress_brotli(body: bytes) -> bytes:
    return brotlicffi.compress(body, quality=4)

@functools.lru_cache(maxsize=128)
def compress_gzip(body: bytes) -> bytes:
    return gzip.compress(body, compresslevel=6)

@functools.lru_cache(maxsize=128)
def compress_deflate(body: bytes) -> bytes:
    return zlib.compress(body, level=6)

@functools.lru_cache(maxsize=128)
def minify_html(body: bytes) -> bytes:
    return rhtmin.minify(body.decode("utf-8", errors="replace"), minify_js=True, minify_css=True, keep_comments=True, keep_html_and_head_opening_tags=True).encode("utf-8")

@functools.lru_cache(maxsize=128)
def minify_css(body: bytes) -> bytes:
    return rcssmin.cssmin(body.decode("utf-8", errors="replace")).encode("utf-8")

@functools.lru_cache(maxsize=128)
def minify_js(body: bytes) -> bytes:
    return rjsmin.jsmin(body.decode("utf-8", errors="replace")).encode("utf-8")

@functools.lru_cache(maxsize=64)
def minify_svg(body: bytes) -> bytes:
    return scour.scourString(body.decode("utf-8", errors="replace"), scour_options).encode("utf-8")

class Middleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        try:
            if scope["type"] not in ["http", "websocket"]:
                await self.app(scope, receive, send)
                return

            scope.update({"website": {
                "id": FourWord(),

                "logged": False,
                "compression": True,

                "templates": templates,
                "accesscounter": accesscounter,

                "cc": CCManager(),
                "pp": PPManager(),
                "csp": CSPManager(),
                "headers": dict(scope.get("headers", [])),
                "timings": TimingManager(),
                "network": NetworkManager(address=ipaddress.ip_address(scope["client"][0]) if scope["client"] and scope["client"][0] else None, host=scope["client"][0] if scope["client"] else None, port=scope["client"][1] if scope["client"] else None),
                "options": OptionManager(HTTPConnection(scope=scope)),

                "directories": Directories,
                "files": Files,
                "repository": Repository,
                "hostnames": Hostnames
            }})

            scope["website"]["timings"].start("total", "Total")

            host = scope["website"]["headers"].get(b"host", b"").decode()
            hostname = host.split(":")[0].strip()

            subdomain = next((hostname[:-(len(candidate) + 1)] for candidate in Hostnames.all if hostname.endswith("." + candidate)), "")

            if not scope["website"]["network"].trusted and not any([hostname == candidate or hostname.endswith("." + candidate) for candidate in Hostnames.public]):
                response = PlainTextResponse("許可されていないホスト名でのアクセスです。", status_code=403)
                await self.send(response, scope, receive, send)
                return

            if len(scope.get("path", "")) + len(scope.get("query_string", b"")) > 256:
                response = render_error_page(Request(scope=scope, receive=receive), status_code=414)
                await self.send(response, scope, receive, send)
                return

            if scope["type"] == "websocket":
                if subdomain not in ["", "www"]:
                    original_path = scope["path"] if scope["path"].strip() else "/"
                    subdomain_path = f"/{'/'.join(subdomain.split('.')[::-1])}{original_path}"
                    scope = dict(scope, path=subdomain_path)
                await self.app(scope, receive, send)
                return

            if scope.get("method") == "OPTIONS":
                response = Response(status_code=204)
                await self.send(response, scope, receive, send)
                return

            scope["website"]["timings"].start("receive", "Read body")
            body = await self.read_body(receive)
            scope["website"]["timings"].stop("receive")

            async def cached_receive():
                return {"type": "http.request", "body": body, "more_body": False}

            if subdomain in ["", "www"]:
                response = await self.get_response(scope, cached_receive, scope["path"], "app", "ASGI App Total")
                await self.send(response, scope, cached_receive, send)

            else:
                original_path = scope["path"] if scope["path"].strip() else "/"
                subdomain_path = f"/{'/'.join(subdomain.split('.')[::-1])}{original_path}"

                response = await self.get_response(scope, cached_receive, subdomain_path, "app", "ASGI App Total")
                if not 400 <= response.status_code < 500:
                    await self.send(response, scope, cached_receive, send)
                    return

                response = await self.get_response(scope, cached_receive, original_path, "app-retry", "ASGI App Total (Retry)")
                await self.send(response, scope, cached_receive, send)

        except Exception:
            try:
                id = scope.get("website", {}).get("id", FourWord())
                log_error(id, traceback.format_exc())
                if not scope.get("website", {}).get("logged", False):
                    log_access(Request(scope=scope, receive=receive), status_code=500)
                    scope["website"]["logged"] = True
                await self.send(render_error_page(Request(scope=scope, receive=receive), status_code=500), scope, receive, send)
            except Exception:
                await self.send(PlainTextResponse("Internal Server Error", status_code=500), scope, receive, send)

    async def get_response(self, scope: Scope, receive: Receive, path: str, key: str, description: str | None = None) -> Response:
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        new_scope = dict(scope, path=path)

        status_code = 200
        response_headers = []
        body_parts = []

        async def capture_send(message):
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        scope["website"]["timings"].start(key, description)
        await self.app(new_scope, receive, capture_send)
        scope["website"]["timings"].stop(key)

        response = Response(content=b"".join(body_parts), status_code=status_code)

        for k, v in response_headers:
            response.headers.raw.append((k, v))

        return response

    async def read_body(self, receive: Receive) -> bytes:
        parts = []
        while True:
            message = await receive()
            if chunk := message.get("body"):
                parts.append(chunk)
            if not message.get("more_body", False):
                break
        return b"".join(parts)

    async def send(self, response: Response, scope, receive, send):
        def set_header(key: str, value: str, override: bool = True, condition: bool = True):
            if condition and override or key.title() not in response.headers:
                response.headers[key.title()] = value

        def add_vary(*headers: str, condition: bool = True):
            if condition:
                vary = [v.strip() for v in response.headers.get("vary", "").split(",") if v.strip()]

                if "*" in vary:
                    return

                for header in headers:
                    if header == "*":
                        set_header("Vary", "*")
                        break

                    if not any(v.title() == header.title() for v in vary):
                        vary.append(header)

                set_header("Vary", ", ".join(vary))

        content_type = response.headers.get("content-type", "")

        if "text/html" in content_type:
            try:
                scope["website"]["timings"].start("minify", "Minify HTML")
                response.body = minify_html(response.body)
                scope["website"]["timings"].stop("minify")
            except Exception:
                pass

        elif "text/css" in content_type:
            try:
                scope["website"]["timings"].start("minify", "Minify CSS")
                response.body = minify_css(response.body)
                scope["website"]["timings"].stop("minify")
            except Exception:
                pass

        elif content_type.startswith(("text/javascript", "application/javascript")):
            try:
                scope["website"]["timings"].start("minify", "Minify JavaScript")
                response.body = minify_js(response.body)
                scope["website"]["timings"].stop("minify")
            except Exception:
                pass

        elif "image/svg" in content_type:
            try:
                scope["website"]["timings"].start("minify", "Minify SVG")
                response.body = minify_svg(response.body)
                scope["website"]["timings"].stop("minify")
            except Exception:
                pass

        if scope["website"]["compression"] and response.body:
            accept_encoding = [encoding.strip().split(";")[0].strip() for encoding in scope["website"]["headers"].get(b"accept-encoding", b"").decode().split(",")]

            scope["website"]["timings"].start("compress", "Compress")

            if "zstd" in accept_encoding:
                response.body = compress_zstd(response.body)
                response.headers["Content-Encoding"] = "zstd"

            elif "br" in accept_encoding:
                response.body = compress_brotli(response.body)
                response.headers["Content-Encoding"] = "br"

            elif "gzip" in accept_encoding:
                response.body = compress_gzip(response.body)
                response.headers["Content-Encoding"] = "gzip"

            elif "deflate" in accept_encoding:
                response.body = compress_deflate(response.body)
                response.headers["Content-Encoding"] = "deflate"

            scope["website"]["timings"].stop("compress")

            if "content-encoding" in response.headers:
                add_vary("Accept-Encoding")

        response.headers["Content-Length"] = str(len(response.body))

        scope["website"]["timings"].start("etag", "ETag (xxHash3)")
        etag = compute_etag(response.body)
        scope["website"]["timings"].stop("etag")

        # ETag / 304 Not Modified
        if scope["website"]["headers"].get(b"if-none-match", b"").decode() == etag:
            response = Response(status_code=304)

        set_header("ETag", etag)

        # Informations
        set_header("Server", f"nercone.dev ({Repository.version})")
        set_header("X-Powered-By", "nercone.dev")

        set_header("X-Request-Id", scope["website"]["id"].text)

        set_header("Link", "<https://nercone.dev/sitemap.xml>; rel=\"sitemap\", <https://nercone.dev/robots.txt>; rel=\"robots\"")

        # Proxy
        set_header("X-Content-Type-Options", "nosniff")

        # Report
        set_header("Reporting-Endpoints", "default=\"https://nercone.dev/report/\", csp-endpoint=\"https://nercone.dev/report/csp/\"")

        # Cache
        if not scope["website"]["cc"].initial:
            set_header("Cache-Control", scope["website"]["cc"].header)
        elif content_type.startswith("font/"):
            set_header("Cache-Control", "max-age=604800")
        elif content_type.startswith(("text/css", "text/javascript", "application/javascript")):
            set_header("Cache-Control", "max-age=43200")
        else:
            set_header("Cache-Control", "no-cache")

        # Security
        set_header("Referrer-Policy", "strict-origin-when-cross-origin")
        set_header("Permissions-Policy", scope["website"]["pp"].header)
        set_header("Content-Security-Policy", scope["website"]["csp"].header)

        set_header("X-Frame-Options", "SAMEORIGIN")

        # Security: Cross-Origin
        origin = scope["website"]["headers"].get(b"origin", b"").decode().strip()
        origin_host = origin.removeprefix("https://").removeprefix("http://").split("/")[0].split(":")[0]

        add_vary("Origin")

        if "text/html" in content_type:
            set_header("Cross-Origin-Opener-Policy", "same-origin", override=False)
            set_header("Cross-Origin-Embedder-Policy", "credentialless", override=False)

        if content_type.startswith(("text/css", "text/javascript", "application/javascript", "font/", "image/")):
            set_header("Cross-Origin-Resource-Policy", "cross-origin", override=False)

            set_header("Access-Control-Allow-Origin", "*", override=False)
            set_header("Access-Control-Allow-Headers", "*", override=False)

        else:
            set_header("Cross-Origin-Resource-Policy", "same-origin", override=False)

            if any(origin_host == candidate or origin_host.endswith("." + candidate) for candidate in Hostnames.all):
                add_vary("Origin")

                set_header("Access-Control-Allow-Origin", origin, override=False)
                set_header("Access-Control-Allow-Credentials", "true", override=False)

                if scope.get("method") == "OPTIONS":
                    set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS", override=False)
                    set_header("Access-Control-Allow-Headers", scope["website"]["headers"].get(b"access-control-request-headers", b"").decode() or "Content-Type, Authorization, X-Requested-With", override=False)
                    set_header("Access-Control-Max-Age", "86400", override=False)

        # Debug
        scope["website"]["timings"].stop("total")
        set_header("Server-Timing", scope["website"]["timings"].header)

        if not scope.get("website", {}).get("logged", False):
            log_access(Request(scope=scope, receive=receive), response)
            scope["website"]["logged"] = True

        response.headers._list[:] = [(k.title().encode("latin-1"), v.encode("latin-1")) for k, v in response.headers.items()]

        try:
            await response(scope, receive, send)
        except:
            pass
