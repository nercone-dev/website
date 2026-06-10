import gzip
import zlib
import hashlib
import logging
import functools
import traceback
import ipaddress
import zstandard
import brotlicffi
from fourword.lib import FourWord
from fastapi import Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request, HTTPConnection
from starlette.types import ASGIApp, Scope, Receive, Send

import minify_html as rhtmin
import rjsmin
import rcssmin
from scour import scour

from ..constants import Directories, Files, Repository, Hostnames, Ports, TLS
from .logger import log_access, log_error
from .manager import PPManager, CSPManager, CCManager, TimingManager, NetworkManager, OptionManager
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
    return '"' + hashlib.sha256(body).hexdigest() + '"'

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

            logger = logging.getLogger("nercone_dev.website")

            scope.update({"nercone.dev": {
                "id": FourWord(),

                "logged": False,
                "compression": True,

                "logger": logger,
                "templates": templates,
                "accesscounter": accesscounter,

                "headers": dict(scope.get("headers", [])),

                "cc": CCManager(),
                "pp": PPManager(),
                "csp": CSPManager(),
                "timings": TimingManager(),
                "network": NetworkManager(address=ipaddress.ip_address(scope["client"][0]) if scope["client"][0] else None, host=scope["client"][0], port=scope["client"][1]),
                "options": OptionManager(HTTPConnection(scope=scope)),

                "directories": Directories,
                "files": Files,
                "repository": Repository,
                "hostnames": Hostnames,
                "ports": Ports,
                "tls": TLS
            }})

            scope["nercone.dev"]["timings"].start("total", "Total")

            host = scope["nercone.dev"]["headers"].get(b"host", b"").decode()
            hostname = host.split(":")[0].strip()

            subdomain = next((hostname[:-(len(candidate) + 1)] for candidate in Hostnames.all if hostname.endswith("." + candidate)), "")

            if not scope["nercone.dev"]["network"].trusted and not any([hostname == candidate or hostname.endswith("." + candidate) for candidate in Hostnames.public]):
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

            if not scope["nercone.dev"]["network"].trusted and scope["scheme"] == "http":
                path = scope.get("path", "/")
                query_string = scope.get("query_string", b"").decode()
                url = f"https://{host}{path}" + (f"?{query_string}" if query_string else "")
                response = RedirectResponse(url=url, status_code=301)
                await self.send(response, scope, receive, send)
                return

            if scope.get("method") == "OPTIONS":
                response = Response(status_code=204)
                await self.send(response, scope, receive, send)
                return

            scope["nercone.dev"]["timings"].start("receive", "Read body")
            body = await self.read_body(receive)
            scope["nercone.dev"]["timings"].stop("receive")

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
                id = scope.get("nercone.dev", {}).get("id", FourWord())
                logger = scope.get("nercone.dev", {}).get("logger", logging.getLogger("nercone_dev.website"))
                log_error(id, logger, traceback.format_exc())
                if not scope.get("nercone.dev", {}).get("logged", False):
                    log_access(logger, Request(scope=scope, receive=receive), status_code=500)
                    scope["nercone.dev"]["logged"] = True
                await self.send(render_error_page(Request(scope=scope, receive=receive), status_code=500), scope, cached_receive, send)
            except Exception:
                await self.send(PlainTextResponse("Internal Server Error", status_code=500), scope, cached_receive, send)

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

        scope["nercone.dev"]["timings"].start(key, description)
        await self.app(new_scope, receive, capture_send)
        scope["nercone.dev"]["timings"].stop(key)

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
        content_type = response.headers.get("content-type", "")

        if "text/html" in content_type:
            try:
                scope["nercone.dev"]["timings"].start("minify", "Minify HTML")
                response.body = minify_html(response.body)
                scope["nercone.dev"]["timings"].stop("minify")
            except Exception:
                pass

        elif "text/css" in content_type:
            try:
                scope["nercone.dev"]["timings"].start("minify", "Minify CSS")
                response.body = minify_css(response.body)
                scope["nercone.dev"]["timings"].stop("minify")
            except Exception:
                pass

        elif content_type.startswith(("text/javascript", "application/javascript")):
            try:
                scope["nercone.dev"]["timings"].start("minify", "Minify JavaScript")
                response.body = minify_js(response.body)
                scope["nercone.dev"]["timings"].stop("minify")
            except Exception:
                pass

        elif "image/svg" in content_type:
            try:
                scope["nercone.dev"]["timings"].start("minify", "Minify SVG")
                response.body = minify_svg(response.body)
                scope["nercone.dev"]["timings"].stop("minify")
            except Exception:
                pass

        if scope["nercone.dev"]["compression"] and response.body:
            accept_encoding = [encoding.strip().split(";")[0].strip() for encoding in scope["nercone.dev"]["headers"].get(b"accept-encoding", b"").decode().split(",")]

            scope["nercone.dev"]["timings"].start("compress", "Compress")

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

            scope["nercone.dev"]["timings"].stop("compress")

            if "content-encoding" in response.headers:
                response.headers["Vary"] = response.headers["vary"] + ", Accept-Encoding" if response.headers.get("vary") else "Accept-Encoding"

        response.headers["Content-Length"] = str(len(response.body))

        scope["nercone.dev"]["timings"].start("etag", "ETag (SHA-256)")
        etag = compute_etag(response.body)
        scope["nercone.dev"]["timings"].stop("etag")

        if scope["nercone.dev"]["headers"].get(b"if-none-match", b"").decode() == etag:
            response = Response(status_code=304)

        def set_header(key: str, value: str, override: bool = True):
            if override or key.lower() not in response.headers:
                response.headers[key.lower()] = value

        set_header("Server", f"nercone.dev ({Repository.version})")
        set_header("Link", "<https://nercone.dev/sitemap.xml>; rel=\"sitemap\", <https://nercone.dev/robots.txt>; rel=\"robots\"")

        set_header("X-Request-Id", scope["nercone.dev"]["id"].text)
        set_header("X-Powered-By", "nercone.dev")
        set_header("X-Frame-Options", "SAMEORIGIN")
        set_header("X-Content-Type-Options", "nosniff")

        set_header("ETag", etag)

        if not scope["nercone.dev"]["cc"].initial:
            set_header("Cache-Control", scope["nercone.dev"]["cc"].header)
        elif content_type.startswith(("font/", "image/", "text/css", "text/javascript", "application/javascript")):
            set_header("Cache-Control", "max-age=43200")
        else:
            set_header("Cache-Control", "no-cache")

        set_header("Referrer-Policy", "strict-origin-when-cross-origin")
        set_header("Permissions-Policy", scope["nercone.dev"]["pp"].header)
        set_header("Content-Security-Policy", scope["nercone.dev"]["csp"].header)

        set_header("Reporting-Endpoints", "default=\"https://nercone.dev/report/\", csp-endpoint=\"https://nercone.dev/report/csp/\"")

        if scope.get("scheme") == "https":
            set_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")

        if "text/html" in content_type:
            set_header("Cross-Origin-Opener-Policy", "same-origin", override=False)
            set_header("Cross-Origin-Embedder-Policy", "credentialless", override=False)

        if content_type.startswith(("font/", "image/", "text/css", "text/javascript", "application/javascript")):
            set_header("Access-Control-Allow-Origin", "*", override=False)
            set_header("Cross-Origin-Resource-Policy", "cross-origin", override=False)

        else:
            set_header("Cross-Origin-Resource-Policy", "same-origin", override=False)

            origin = scope["nercone.dev"]["headers"].get(b"origin", b"").decode().strip()
            origin_host = origin.removeprefix("https://").removeprefix("http://").split("/")[0].split(":")[0]

            if any(origin_host == candidate or origin_host.endswith("." + candidate) for candidate in Hostnames.all):
                vary = response.headers.get("vary", "") + ", Origin, User-Agent" if "vary" in response.headers else "Origin, User-Agent"
                set_header("Vary", vary)

                set_header("Access-Control-Allow-Origin", origin, override=False)
                set_header("Access-Control-Allow-Credentials", "true", override=False)

                if scope.get("method") == "OPTIONS":
                    set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS", override=False)
                    set_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With", override=False)
                    set_header("Access-Control-Max-Age", "86400", override=False)

        scope["nercone.dev"]["timings"].stop("total")
        set_header("Server-Timing", scope["nercone.dev"]["timings"].header)

        if not scope.get("nercone.dev", {}).get("logged", False):
            log_access(scope["nercone.dev"]["logger"], Request(scope=scope, receive=receive), response)
            scope["nercone.dev"]["logged"] = True

        try:
            await response(scope, receive, send)
        except:
            pass
