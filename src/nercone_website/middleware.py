import traceback

from aki import Request, Message, Method, Compression
from fourword import FourWord

from .logger import log_access, log_error
from .models import URL, CommaHeader, Minifier, Conditional, CCManager, PPManager, CSPManager, TimingManager, NetworkManager, OptionManager
from .renderer import render_error_page
from .constants import Startup, Hostnames, Ports

async def middleware(request: Request, next_handler):
    try:
        request.scope.update({
            "id": FourWord(),
            "logged": False,

            "url": URL.from_target(request.target or "/", "https" if request.secure else "http", request.header("host") or ""),
            "compression": True,

            "cc": CCManager(),
            "pp": PPManager(),
            "csp": CSPManager(),
            "timings": TimingManager(),
            "network": NetworkManager(request.client)
        })

        request.scope["options"] = OptionManager(request)

        request.scope["timings"].start("total", "Total")

        if Startup.dev:
            for key in ("script-src", "style-src", "font-src", "img-src"):
                request.scope["csp"].append(key, f"localhost:{Ports.tcp}")

        host = request.header("host") or ""
        hostname = host.split(":")[0].strip()
        subdomain = next((hostname[:-(len(candidate) + 1)] for candidate in Hostnames.all if hostname.endswith("." + candidate)), "")

        if not request.scope["network"].trusted and not any([hostname == candidate or hostname.endswith("." + candidate) for candidate in Hostnames.public]):
            response = Message.text("許可されていないホスト名でのアクセスです。", request.version)
            response.status_code = 403
            return await finalize(request, response)

        if len(request.target or "") > 512:
            return await finalize(request, await render_error_page(request, status_code=414))

        if request.method == Method.OPTIONS:
            return await finalize(request, Message.response(204, request.version))

        target = request.target

        original_path = request.scope["url"].path.rstrip("/") or "/"
        query_suffix = f"?{request.scope['url'].query}" if request.scope["url"].query else ""

        if subdomain in ("", "www"):
            request.target = original_path + query_suffix

            request.scope["timings"].start("app", "App Total")
            response = await next_handler(request)
            request.scope["timings"].stop("app")

        else:
            request.target = f"/{'/'.join(subdomain.split('.')[::-1])}{original_path.rstrip('/')}" + query_suffix

            request.scope["timings"].start("app", "App Total")
            response = await next_handler(request)
            request.scope["timings"].stop("app")

            if 400 <= response.status_code < 500:
                request.scope["cc"] = CCManager()
                request.scope["pp"] = PPManager()
                request.scope["csp"] = CSPManager()

                if Startup.dev:
                    for key in ("script-src", "style-src", "font-src", "img-src"):
                        request.scope["csp"].append(key, f"localhost:{Ports.tcp}")

                request.target = original_path + query_suffix

                request.scope["timings"].start("app-retry", "App Total (Retry)")
                response = await next_handler(request)
                request.scope["timings"].stop("app-retry")

        request.target = target

        return await finalize(request, response)

    except Exception:
        try:
            if not "id" in request.scope:
                request.scope["id"] = FourWord()

            log_error(request.scope["id"], traceback.format_exc())

            if not request.scope.get("logged", False):
                log_access(request, status_code=500)
                request.scope["logged"] = True

            return await finalize(request, await render_error_page(request, status_code=500))

        except Exception:
            response = Message.text("Internal Server Error", request.version)
            response.status_code = 500
            return response

async def finalize(request: Request, response: Message) -> Message:
    def set_header(key: str, value: str, override: bool = True, condition: bool = True):
        if condition and override or not response.headers.contains(key):
            response.insert_header(key, value)

    def add_vary(*headers: str, condition: bool = True):
        if condition:
            vary = CommaHeader(response.header("vary") or "")
            for header in headers:
                vary.append(header)
            set_header("Vary", vary.build())

    content_type = response.header("content-type") or ""

    # Development
    if content_type.startswith(("text/html", "text/css", "text/javascript", "application/javascript", "text/svg")) and Startup.dev:
        if (body := response.body_inline()) is not None:
            response.set_body(body.replace(b"https://assets.nercone.dev/", f"http://localhost:{Ports.tcp}/assets/".encode()))

    # Informations
    set_header("Link", "<https://nercone.dev/sitemap.xml>; rel=\"sitemap\", <https://nercone.dev/robots.txt>; rel=\"robots\"")

    # Proxy
    set_header("X-Content-Type-Options", "nosniff")

    # Cache
    if Startup.dev:
        set_header("Cache-Control", "no-store")
    elif not request.scope["cc"].initial:
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
    set_header("Integrity-Policy", "blocked-destinations=(script style)", condition=("text/html" in content_type and response.status_code < 500))
    set_header("Permissions-Policy", request.scope["pp"].header)
    set_header("Content-Security-Policy", request.scope["csp"].header)

    set_header("X-Frame-Options", "SAMEORIGIN")

    # Security: Cross-Origin
    origin = (request.header("origin") or "").strip()
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

        if any(origin_hostname == candidate or origin_hostname.endswith("." + candidate) for candidate in Hostnames.all):
            add_vary("Origin")

            set_header("Access-Control-Allow-Origin", origin, override=False)
            set_header("Access-Control-Allow-Credentials", "true", override=False)

            if request.method == Method.OPTIONS:
                set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS", override=False)
                set_header("Access-Control-Allow-Headers", request.header("access-control-request-headers") or "Content-Type, Authorization, X-Requested-With", override=False)
                set_header("Access-Control-Max-Age", "86400", override=False)

    # Minification
    Minifier.apply(response)

    # Cache: Conditional
    conditional = Conditional.apply(request, response)

    # Debug
    set_header("X-Request-Id", request.scope["id"].text)

    request.scope["timings"].stop("total")
    set_header("Server-Timing", request.scope["timings"].header)

    if not request.scope["logged"]:
        log_access(request, response)
        request.scope["logged"] = True

    if not conditional and request.scope.get("compression", True):
        response.compression = Compression.AUTO
    else:
        response.compression = None

    return response
