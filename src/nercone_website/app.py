import re
from aki import Aki, Request, Response, Headers, PlainTextResponse, JSONResponse

from .logger import format_access
from .resolver import resolve_file
from .renderer import default_response, render_error_page, render_thumbnail_png
from .constants import Repository
from .databases import AccessCounter
from .middleware import middleware

app = Aki()
app.add_middleware(middleware)

@app.route("/ping", methods=["GET"])
async def ping(request: Request):
    return PlainTextResponse("pong!")

@app.route("/welcome", methods=["GET"])
async def welcome(request: Request):
    return PlainTextResponse(
        f"""
■   ■ ■■■■■ ■■■■   ■■■■  ■■■  ■   ■ ■■■■■
■■  ■ ■     ■   ■ ■     ■   ■ ■■  ■ ■
■■  ■ ■     ■   ■ ■     ■   ■ ■■  ■ ■
■ ■ ■ ■■■■  ■■■■  ■     ■   ■ ■ ■ ■ ■■■■
■  ■■ ■     ■ ■   ■     ■   ■ ■  ■■ ■
■  ■■ ■     ■  ■  ■     ■   ■ ■  ■■ ■
■   ■ ■■■■■ ■   ■  ■■■■  ■■■  ■   ■ ■■■■■

nercone.dev ({Repository.version})
welcome to nercone.dev!
        """.strip() + "\n"
    )

@app.route("/echo", methods=["GET"])
async def echo(request: Request):
    if request.scope["network"].trusted:
        return JSONResponse(format_access(request))
    else:
        return render_error_page(request=request, status_code=403, message="/echoエンドポイントはデバッグ用途のため、信頼された接続元からのみ使用できます。", joke_message="悪いなのび太、このエンドポイント開発者専用なんだ")

@app.route("/status", methods=["GET"])
async def status(request: Request):
    return JSONResponse(
        {
            "status": "ok",
            "version": Repository.version,
            "counter": AccessCounter().get()
        }
    )

@app.route("/assets/images/thumbnail/template/{template}", methods=["GET"])
async def thumbnail(request: Request, template: str) -> Response:
    query_params = {key: values[0] for key, values in request.url.params.items()}
    path = query_params.get("path", "/")
    title = query_params.get("title", "Untitled Page")
    description = query_params.get("description", "No description.")

    try:
        png = render_thumbnail_png(path=path, title=title, description=description, template=template)
        return Response(body=png, headers=Headers([("Content-Type", ["image/png"])]))
    except FileNotFoundError:
        return render_error_page(request=request, status_code=404, message="サムネイルの生成に必要なテンプレートが見つかりません。", joke_message="はにゃ？")
    except PermissionError:
        return render_error_page(request=request, status_code=403, message="ねえ、今サムネイル生成のエンドポイント悪用して攻撃しようとした？したよね？？ディレクトリトラバーサルでしょ？知ってるよ？怒ってないから正直に言って？ね？ね？？", joke_message="嘘つきには針千本プレゼント！このメッセージを読んだ後、100年以内限定！飲用補助サービスが無料でついてきます！今すぐ正直に言え！！")

@app.route("/error/{status_code}", methods=["GET"])
async def fake_error_page(request: Request, status_code: str):
    if status_code.isdecimal():
        return render_error_page(request=request, status_code=int(status_code))
    elif status_code == "server":
        return render_error_page(request=request, status_code=500)
    else:
        return render_error_page(request=request, status_code=400, message="errorエンドポイントのパスには「server」またはHTTPレスポンスステータスコードのみが使用可能です。", joke_message="HTTP/1.1 600 Not Normal")

css_re_charset = re.compile(r'@charset\s+[^;]+;', re.IGNORECASE)
css_re_import = re.compile(r'@import\b[^;]*;', re.DOTALL)
css_re_whitespace = re.compile(r'\s+')

@app.route("/assets/css/merge", methods=["GET"])
async def merge_css(request: Request) -> Response:
    path_param = request.url.params.get("path", [""])[0]
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

        m = css_re_charset.search(content)
        if m and charset is None:
            charset = m.group(0)
        content = css_re_charset.sub('', content)

        for imp in css_re_import.findall(content):
            key = css_re_whitespace.sub(' ', imp.strip())
            if key not in seen_imports:
                seen_imports.add(key)
                imports.append(key)
        body = css_re_import.sub('', content).strip()
        if body:
            bodies.append(body)

    parts: list[str] = []
    if charset:
        parts.append(charset)
    if imports:
        parts.append('\n'.join(imports))
    parts.extend(bodies)

    return Response(body='\n\n'.join(parts).encode(), headers=Headers([("Content-Type", ["text/css"])]))

@app.route("/assets/js/merge", methods=["GET"])
async def merge_js(request: Request) -> Response:
    path_param = request.url.params.get("path", [""])[0]
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

    return Response(body=';\n'.join(c.strip() for c in contents if c.strip()).encode(), headers=Headers([("Content-Type", ["text/javascript"])]))

@app.route("/{path:path}", methods=["GET", "POST", "HEAD"])
async def default_route(request: Request, path: str) -> Response:
    return default_response(path, request=request)
