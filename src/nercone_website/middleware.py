import ipaddress
from fourword.lib import FourWord

from aki import Request, Response, Headers, PlainTextResponse
from aki.models import Scope
from momiji import CommaHeader

from .logger import log_access
from .models import CCManager, PPManager, CSPManager, TimingManager, NetworkManager, OptionManager
from .renderer import render_error_page
from .constants import Startup, Hostnames, Repository, Ports

def clone_request(request: Request, *, method: str | None = None, target: str | None = None, client: tuple | None = None, scheme: str | None = None, secure: bool | None = None, protocol: str | None = None, headers: Headers | None = None, body: bytes | None = None, scope: Scope | None = None) -> Request:
    return Request(
        method=method or request.method,
        target=target or request.target,
        client=client or request.client,
        scheme=scheme or request.scheme,
        secure=secure or request.secure,
        protocol=protocol or request.protocol,
        headers=headers or request.headers,
        body=body or request.body,
        scope=scope or request.scope
    )

async def middleware(request: Request, next_handler):
    request.scope.update({
        "id": FourWord(),
        "logged": False,

        "cc": CCManager(),
        "pp": PPManager(),
        "csp": CSPManager(),
        "timings": TimingManager(),
        "network": NetworkManager(address=ipaddress.ip_address(request.client[0]) if request.client and request.client[0] else None, host=request.client[0] if request.client else None, port=request.client[1] if request.client else None),
        "options": OptionManager(request)
    })

    request.scope["timings"].start("total", "Total")

    if Startup.dev:
        for key in ("script-src", "style-src", "font-src", "img-src"):
            request.scope["csp"].append(key, f"localhost:{Ports.tcp}")

    host = request.headers.get("host", "")
    hostname = host.split(":")[0].strip()
    subdomain = next((hostname[:-(len(candidate) + 1)] for candidate in Hostnames.all if hostname.endswith("." + candidate)), "")

    if not request.scope["network"].trusted and not any([hostname == candidate or hostname.endswith("." + candidate) for candidate in Hostnames.public]):
        return await finalize(request, PlainTextResponse("許可されていないホスト名でのアクセスです。", status_code=403))

    if len(request.target) > 512:
        return await finalize(request, render_error_page(request, status_code=414))

    if request.method == "OPTIONS":
        return await finalize(request, Response(status_code=204, headers=Headers([])))

    original_path = request.url.path.rstrip("/")
    query_suffix = f"?{request.url.query}" if request.url.query else ""

    if subdomain in ("", "www"):
        dispatch_request = clone_request(request, target=original_path + query_suffix)

        request.scope["timings"].start("app", "App Total")
        response = await next_handler(dispatch_request)
        request.scope["timings"].stop("app")

    else:
        subdomain_path = f"/{'/'.join(subdomain.split('.')[::-1])}{original_path.rstrip('/')}"

        request.scope["timings"].start("app", "App Total")
        response = await next_handler(clone_request(request, target=subdomain_path + query_suffix))
        request.scope["timings"].stop("app")

        if 400 <= response.status_code < 500:
            request.scope["cc"] = CCManager()
            request.scope["pp"] = PPManager()
            request.scope["csp"] = CSPManager()

            if Startup.dev:
                for key in ("script-src", "style-src", "font-src", "img-src"):
                    request.scope["csp"].append(key, f"localhost:{Ports.tcp}")

            request.scope["timings"].start("app-retry", "App Total (Retry)")
            response = await next_handler(clone_request(request, target=original_path + query_suffix))
            request.scope["timings"].stop("app-retry")

    return await finalize(request, response)

async def finalize(request: Request, response: Response) -> Response:
    def set_header(key: str, value: str, override: bool = True, condition: bool = True):
        if condition and override or key.title() not in response.headers:
            response.headers[key.title()] = value

    def add_vary(*headers: str, condition: bool = True):
        if condition:
            vary = CommaHeader(response.headers.get("Vary", ""))
            for header in headers:
                vary.append(header)
            set_header("Vary", vary.build())

    content_type = response.headers.get("content-type", "")

    # Development
    if content_type.startswith(("text/html", "text/css", "text/javascript", "application/javascript", "text/svg")) and Startup.dev and isinstance(response.body, bytes):
        response.body = response.body.replace(b"https://assets.nercone.dev/", f"http://localhost:{Ports.tcp}/assets/".encode())

    # Informations
    set_header("Link", "<https://nercone.dev/sitemap.xml>; rel=\"sitemap\", <https://nercone.dev/robots.txt>; rel=\"robots\"")

    # Proxy
    set_header("X-Content-Type-Options", "nosniff")

    # Cache
    if not request.scope["cc"].initial:
        set_header("Cache-Control", request.scope["cc"].header)
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
    set_header("Permissions-Policy", request.scope["pp"].header)
    set_header("Content-Security-Policy", request.scope["csp"].header)

    set_header("X-Frame-Options", "SAMEORIGIN")

    # Security: Cross-Origin
    origin = request.headers.get("origin", "").strip()
    origin_hostname = origin.removeprefix("https://").removeprefix("http://").split("/")[0].split(":")[0]

    add_vary("Origin")

    if "text/html" in content_type:
        set_header("Cross-Origin-Opener-Policy", "same-origin", override=False)

    if content_type.startswith(("text/css", "text/javascript", "application/javascript", "font/", "image/")):
        set_header("Cross-Origin-Resource-Policy", "cross-origin", override=False)

        set_header("Access-Control-Allow-Origin", "*", override=False)
        set_header("Access-Control-Allow-Headers", "*", override=False)

    else:
        set_header("Cross-Origin-Resource-Policy", "same-origin", override=False)

        if any(origin_hostname == candidate or origin_hostname.endswith("." + candidate) for candidate in Hostnames.all):
            add_vary("Origin")

            set_header("Access-Control-Allow-Origin", origin, override=False)
            set_header("Access-Control-Allow-Credentials", "true", override=False)

            if request.method == "OPTIONS":
                set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS", override=False)
                set_header("Access-Control-Allow-Headers", request.headers.get("access-control-request-headers", "") or "Content-Type, Authorization, X-Requested-With", override=False)
                set_header("Access-Control-Max-Age", "86400", override=False)

    # Debug
    set_header("X-Request-Id", request.scope["id"].text)

    request.scope["timings"].stop("total")
    set_header("Server-Timing", request.scope["timings"].header)

    if not request.scope["logged"]:
        log_access(request, response)
        request.scope["logged"] = True

    return response
