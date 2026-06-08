import re
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse

from .logger import format_access
from .databases import MimeTypes
from .constants import Repositories
from .middleware import Middleware
from .resolver import resolve_file
from .renderer import default_response, render_error_page, render_thumbnail_png

MimeTypes.load()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(Middleware)

@app.api_route("/ping", methods=["GET"])
async def ping():
    return PlainTextResponse("pong!")

@app.api_route("/welcome", methods=["GET"])
async def welcome():
    return PlainTextResponse(
        f"""
■   ■ ■■■■■ ■■■■   ■■■■  ■■■  ■   ■ ■■■■■
■■  ■ ■     ■   ■ ■     ■   ■ ■■  ■ ■
■■  ■ ■     ■   ■ ■     ■   ■ ■■  ■ ■
■ ■ ■ ■■■■  ■■■■  ■     ■   ■ ■ ■ ■ ■■■■
■  ■■ ■     ■ ■   ■     ■   ■ ■  ■■ ■
■  ■■ ■     ■  ■  ■     ■   ■ ■  ■■ ■
■   ■ ■■■■■ ■   ■  ■■■■  ■■■  ■   ■ ■■■■■

nercone.dev ({Repositories.Server.version})
welcome to nercone.dev!
        """.strip() + "\n"
    )

@app.api_route("/echo", methods=["GET"])
async def echo(request: Request):
    return JSONResponse(format_access(request))

@app.api_route("/status", methods=["GET"])
async def status(request: Request):
    return JSONResponse(
        {
            "status": "ok",
            "version": Repositories.Server.version,
            "counter": request.scope["accesscounter"].get()
        }
    )

@app.api_route("/assets/images/thumbnail/template/{template}", methods=["GET"])
async def thumbnail(request: Request, template: str) -> Response:
    path = request.query_params.get("path", "/")
    title = request.query_params.get("title", "Untitled Page")
    description = request.query_params.get("description", "No description.")

    try:
        png = render_thumbnail_png(path=path, title=title, description=description, template=template)
        return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-cache"})
    except FileNotFoundError:
        return render_error_page(request=request, status_code=500, message="サムネイルの生成に必要なテンプレートが見つかりません。", joke_message="はにゃ？")
    except PermissionError:
        return render_error_page(request=request, status_code=403, message="ねえ、今サムネイル生成のエンドポイント悪用して攻撃しようとした？したよね？？ディレクトリトラバーサルでしょ？知ってるよ？怒ってないから正直に言って？ね？ね？？", joke_message="嘘つきには針千本プレゼント！このメッセージを読んだ後、100年以内限定！飲用補助サービスが無料でついてきます！今すぐ正直に言え！！")

@app.api_route("/error/{status_code}", methods=["GET"])
async def fake_error_page(request: Request, status_code: str):
    if status_code.isnumeric():
        return render_error_page(request=request, status_code=int(status_code))
    elif status_code == "server":
        return render_error_page(request=request, status_code=500)
    else:
        return render_error_page(request=request, status_code=400, message="errorエンドポイントのパスには「server」またはHTTPレスポンスステータスコードのみが使用可能です。", joke_message="HTTP/1.1 600 Not Normal")

@app.api_route("/assets/css/merge", methods=["GET"])
async def merge_css(request: Request) -> Response:
    path_param = request.query_params.get("path", "")
    if not path_param:
        return render_error_page(request=request, status_code=400, message="pathパラメータが必要です。")

    charset: str | None = None
    imports: list[str] = []
    seen_imports: set[str] = set()
    bodies: list[str] = []

    for name in (n.strip() for n in path_param.split(",")):
        try:
            if file := resolve_file(f"assets/css/{name}.css"):
                content = file.read_text(encoding="utf-8")
            else:
                return render_error_page(request=request, status_code=404, message=f"ファイルが見つかりません: {name}.css")
        except PermissionError:
            return render_error_page(request=request, status_code=403, message="ねえ、今CSSファイル統合用のエンドポイント悪用して攻撃しようとした？したよね？？ディレクトリトラバーサルでしょ？知ってるよ？新しく追加されたエンドポイントに脆弱性あるか気になっただけ？そんなこと関係ないよね。攻撃しようとしたのは事実でしょ？？怒ってないから正直に言って？ね？ね？？", joke_message="嘘つきには針千本プレゼント！このメッセージを読んだ後、100年以内限定！飲用補助サービスが無料でついてきます！今すぐ正直に言え！！")

        m = re.search(r'@charset\s+[^;]+;', content, re.IGNORECASE)
        if m and charset is None:
            charset = m.group(0)
        content = re.sub(r'@charset\s+[^;]+;', '', content, flags=re.IGNORECASE)

        for imp in re.findall(r'@import\b[^;]*;', content, re.DOTALL):
            key = re.sub(r'\s+', ' ', imp.strip())
            if key not in seen_imports:
                seen_imports.add(key)
                imports.append(key)
        body = re.sub(r'@import\b[^;]*;', '', content, flags=re.DOTALL).strip()
        if body:
            bodies.append(body)

    parts: list[str] = []
    if charset:
        parts.append(charset)
    if imports:
        parts.append('\n'.join(imports))
    parts.extend(bodies)

    return Response(content='\n\n'.join(parts), media_type="text/css")

@app.api_route("/assets/js/merge", methods=["GET"])
async def merge_js(request: Request) -> Response:
    path_param = request.query_params.get("path", "")
    if not path_param:
        return render_error_page(request=request, status_code=400, message="pathパラメータが必要です。")

    contents: list[str] = []
    for name in (n.strip() for n in path_param.split(",")):
        try:
            if file := resolve_file(f"assets/js/{name}.js"):
                contents.append(file.read_text(encoding="utf-8"))
            else:
                return render_error_page(request=request, status_code=404, message=f"ファイルが見つかりません: {name}.js")
        except PermissionError:
            return render_error_page(request=request, status_code=403, message="ねえ、今JSファイル統合用のエンドポイント悪用して攻撃しようとした？したよね？？ディレクトリトラバーサルでしょ？知ってるよ？新しく追加されたエンドポイントに脆弱性あるか気になっただけ？そんなこと関係ないよね。攻撃しようとしたのは事実でしょ？？怒ってないから正直に言って？ね？ね？？", joke_message="嘘つきには針千本プレゼント！このメッセージを読んだ後、100年以内限定！飲用補助サービスが無料でついてきます！今すぐ正直に言え！！")

    return Response(content=';\n'.join(c.strip() for c in contents if c.strip()), media_type="text/javascript")

@app.api_route("/{path:path}", methods=["GET", "POST", "HEAD"])
async def default_route(request: Request, path: str) -> Response:
    return default_response(path, request=request)
