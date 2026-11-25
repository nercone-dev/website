import asyncio

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse

from .helpers import add_report_route, Counter, MimeTypes, CSSBundler, JSBundler, SystemInfo
from .resolver import resolve_static
from .renderer import render_thumbnail_png, render_error_page, default_response
from .constants import Startup, Directories, Files
from .middleware import Middleware

MimeTypes.load()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(Middleware)

css_bundler = CSSBundler(Files.Bundles.css_entry, Files.Bundles.css_output, Directories.assets)
js_bundler  = JSBundler(Files.Bundles.js_entry, Files.Bundles.js_output, Directories.assets)
theme_bundlers = {path.stem: CSSBundler(path, path, Directories.assets) for path in Files.Bundles.themes}
system_info = SystemInfo()

add_report_route(app, "/report", "DEFAULT")
add_report_route(app, "/report/csp", "CSP")

@app.api_route("/ping", methods=["GET"])
async def ping() -> Response:
    return PlainTextResponse("pong!")

# API v1
@app.api_route("/api/v1/status", methods=["GET"])
async def status() -> Response:
    return JSONResponse(
        {
            "status": "ok",
            "counter": Counter(Files.access_counter).get(),
            "startup": {
                "id": Startup.id.text(),
                "version": Startup.version,
                "mode": Startup.mode.value,
            },
            "system": await asyncio.to_thread(system_info.snapshot),
        }
    )

# Access Counter Trigger
@app.api_route("/assets/images/counter.png", methods=["GET"])
async def access_counter_trigger(request: Request) -> Response:
    try:
        if file := resolve_static("/assets/images/checker.png", timings=request.scope["nercone"]["response"]["headers"]["server-timing"]):
            Counter(Files.access_counter).increase()
            request.scope["nercone"]["response"]["headers"]["cache-control"].set("no-store")
            return FileResponse(file)

        response = PlainTextResponse("Not Found: checker.png", status_code=404)
        return response

    except PermissionError:
        response = PlainTextResponse("Permission Error: checker.png", status_code=403)
        return response

# Auto-generated Thumbnail
@app.api_route("/assets/images/templates/thumbnail/generate/{template}", methods=["GET"])
async def generate_thumbnail(request: Request, template: str) -> Response:
    query_params = {key: values[0] for key, values in request.scope["nercone"]["request"]["url"].params.items()}
    path = query_params.get("path", "/")
    title = query_params.get("title", "Untitled Page")
    description = query_params.get("description", "No description.")

    try:
        png = render_thumbnail_png(path, title, description, template=template, timings=request.scope["nercone"]["response"]["headers"]["server-timing"])
        return Response(png, media_type="image/png")
    except FileNotFoundError:
        return await render_error_page(request=request, status_code=404, message="サムネイルの生成に必要なテンプレートが見つかりません。", joke_message="はにゃ？")
    except PermissionError:
        return await render_error_page(request=request, status_code=403, message="ねえ、今サムネイル生成のエンドポイント悪用して攻撃しようとした？したよね？？ディレクトリトラバーサルでしょ？知ってるよ？怒ってないから正直に言って？ね？ね？？", joke_message="嘘つきには針千本プレゼント！このメッセージを読んだ後、100年以内限定！飲用補助サービスが無料でついてきます！今すぐ正直に言え！！")

# Fake Error Page
@app.api_route("/error/{status_code}", methods=["GET"])
async def fake_error_page(request: Request, status_code: str) -> Response:
    if status_code.isdecimal():
        return await render_error_page(request=request, status_code=int(status_code))
    elif status_code == "server":
        return await render_error_page(request=request, status_code=500)
    else:
        return await render_error_page(request=request, status_code=400, message="errorエンドポイントのパスには「server」またはHTTPレスポンスステータスコードのみが使用可能です。", joke_message="HTTP/1.1 600 Not Normal")

# Bundle Styles
@app.api_route("/assets/style.css", methods=["GET"])
async def bundle_styles(request: Request) -> Response:
    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]
    timings.start("bundle", "Bundle Styles")
    content = css_bundler.build()
    timings.stop("bundle")
    return Response(content, media_type="text/css; charset=utf-8")

# Bundle Theme Style
@app.api_route("/assets/styles/themes/{name}.css", methods=["GET"])
async def bundle_theme(request: Request, name: str) -> Response:
    bundler = theme_bundlers.get(name)
    if bundler is None:
        return await default_response(f"assets/styles/themes/{name}.css", request=request)
    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]
    timings.start("bundle", "Bundle Theme")
    content = bundler.build()
    timings.stop("bundle")
    return Response(content, media_type="text/css; charset=utf-8")

# Bundle Scripts
@app.api_route("/assets/script.js", methods=["GET"])
async def bundle_scripts(request: Request) -> Response:
    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]
    timings.start("bundle", "Bundle Scripts")
    content = js_bundler.build()
    timings.stop("bundle")
    return Response(content, media_type="text/javascript; charset=utf-8")

# Default
@app.api_route("/{path:path}", methods=["GET", "POST", "HEAD"])
async def default_route(request: Request, path: str) -> Response:
    return await default_response(path, request=request)
