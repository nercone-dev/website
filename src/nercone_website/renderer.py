import io
import re
import yaml
import random
import mistune
import resvg_py
from typing import Any
from bs4 import BeautifulSoup
from html import escape
from http import HTTPStatus
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from markitdown import MarkItDown, StreamInfo
from starlette.types import Scope
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .constants import Directories
from .manager import TimingManager
from .resolver import resolve_file, resolve_page, resolve_redirects

class CustomHTMLRenderer(mistune.HTMLRenderer):
    _alert_re = re.compile(r'^\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\n(.*?))?</p>\s*', re.IGNORECASE | re.DOTALL,)

    def block_code(self, code, **attrs):
        return f'<pre>{mistune.escape(code)}</pre>\n'

    def block_quote(self, text):
        m = self._alert_re.match(text)
        if m:
            alert_type = m.group(1).upper()
            inline_content = m.group(2)
            rest = text[m.end():]
            label = alert_type.capitalize()
            css_class = alert_type.lower()
            inner = (f'<p>{inline_content}</p>\n' if inline_content and inline_content.strip() else '') + rest
            return f'<div class="block block-{css_class}">\n<b>{label}</b>\n{inner}</div>\n'
        return f'<blockquote>\n{text}</blockquote>\n'

markitdown = MarkItDown()
htmlitdown = mistune.create_markdown(renderer=CustomHTMLRenderer(escape=False), plugins=["table", "strikethrough", "task_lists", "footnotes"])

def init_context(context: dict[str, Any], scope: Scope):
    context.update(scope["nercone.dev"])

    context["re_sub"] = lambda s, pattern, repl: re.sub(pattern, repl, s)
    context["this_year"] = datetime.now(ZoneInfo("Asia/Tokyo")).year
    context["this_year_in_heisei"] = datetime.now(ZoneInfo("Asia/Tokyo")).year - 1988

    if file := resolve_file("quotes.txt"):
        daily_seed = str(datetime.now(timezone.utc).date())
        with file.open("r") as f:
            quotes = f.read().strip().split("\n")
        daily_quote = random.Random(daily_seed).choice(quotes)
    else:
        daily_quote = "GReeeeN KA-RA-DA"
    context["daily_quote"] = daily_quote

def render_page(page: str, path: str, request: Request, count: bool = True, render: bool = True, status_code: int = 200, markdown_mode: bool | None = None, context: dict[str, Any] = {}):
    init_context(context, request.scope)

    timings: TimingManager = request.scope["nercone.dev"]["timings"]
    templates: Jinja2Templates = request.scope["nercone.dev"]["templates"]

    if markdown_mode is None:
        markdown_ua = ["curl", "claude-user", "chatgpt-user", "google-extended", "perplexity-user"]
        markdown_mode = path.endswith(".md") or (not any([path.endswith(".html"), "text/html" in request.headers.get("accept", "").lower()]) and any(["text/markdown" in request.headers.get("accept", "").lower(), any([ua in request.headers.get("user-agent", "").lower() for ua in markdown_ua])]))

    if filepath := resolve_file(page):
        with filepath.open("r") as f:
            source = f.read()

        if not source.startswith("---"):
            front = {}
            body = source
        else:
            end = source.find("\n---", 3)
            if end == -1:
                front = {}
                body = source
            else:
                front = yaml.safe_load(source[3:end]) or {}
                body = source[end+4:].lstrip("\n")

        if render:
            timings.start("render", "Render Contents")
            content = templates.env.from_string(body).render(request=request, **context)
            timings.stop("render")

            def render_html(html: str):
                if "base" in front:
                    if front["base"].startswith("/"):
                        source = f"{{% extends \"{front['base']}\" %}}\n"
                    else:
                        source = f"{{% extends \"/base/{front['base']}.html\" %}}\n"
                else:
                    source = "{% extends \"/base/normal.html\" %}\n"

                for key, value in front.items():
                    source += f"{{% block {key} %}}{value}{{% endblock %}}\n"

                source += f"{{% block main %}}\n{html}\n{{% endblock %}}\n"
                return templates.env.from_string(source).render(request=request, **context)

            if page.endswith(".html"):
                if markdown_mode:
                    timings.start("convert", "HTML to Markdown")
                    soup = BeautifulSoup(content, "html.parser")
                    main = str(soup.find("main")) if soup.find("main") else content
                    content = markitdown.convert(io.BytesIO(main.encode("utf-8")), stream_info=StreamInfo(mimetype="text/html", charset="utf-8")).text_content
                    response = PlainTextResponse(content, status_code=status_code, media_type="text/markdown")
                    timings.stop("convert")

                else:
                    timings.start("render", "Render Final HTML")
                    content = render_html(content)
                    timings.stop("render")

                    response = PlainTextResponse(content, status_code=status_code, media_type="text/html")

            elif page.endswith(".md"):
                if markdown_mode:
                    response = PlainTextResponse(content, status_code=status_code, media_type="text/markdown")

                else:
                    timings.start("convert", "Markdown to HTML")
                    main = htmlitdown(content)
                    timings.stop("convert")

                    timings.start("render", "Render Final HTML")
                    content = render_html(main)
                    timings.stop("render")

                    response = PlainTextResponse(content, status_code=status_code, media_type="text/html")

        else:
            if page.endswith(".html"):
                response = PlainTextResponse(source, status_code=status_code, media_type="text/html")
            elif page.endswith(".md"):
                response = PlainTextResponse(source, status_code=status_code, media_type="text/markdown")

        if "compression" in front:
            if front["compression"].lower() == "true":
                request.scope["nercone.dev"]["compression"] = True
            elif front["compression"].lower() == "false":
                request.scope["nercone.dev"]["compression"] = False

        if count:
            request.scope["nercone.dev"]["accesscounter"].increase()

        return response

def default_response(path: str, request: Request, status_code: int = 200, count: bool = True, render: bool = True, context: dict[str, Any] = {}, headers: dict[str, str] = {}):
    markdown_ua = ["curl", "claude-user", "chatgpt-user", "google-extended", "perplexity-user"]
    markdown_mode = path.endswith(".md") or (not any([path.endswith(".html"), "text/html" in request.headers.get("accept", "").lower()]) and any(["text/markdown" in request.headers.get("accept", "").lower(), any([ua in request.headers.get("user-agent", "").lower() for ua in markdown_ua])]))

    timings: TimingManager = request.scope["nercone.dev"]["timings"]

    try:
        if url := resolve_redirects(path, timings=timings):
            response = RedirectResponse(url, status_code=status_code if 300 <= status_code < 400 else 307)

        elif page := resolve_page(path, markdown_mode=markdown_mode, timings=timings):
            response = render_page(page, path, request=request, count=count, render=render, status_code=status_code, markdown_mode=markdown_mode, context=context)

        elif file := resolve_file(path):
            response = FileResponse(file, status_code=status_code)

        else:
            response = render_error_page(request, 404, message="リクエストしたページは現在ご利用になれません。削除/移動されたか、URLが間違っている可能性があります。", joke_message="そんなページ知らないっ！")

    except PermissionError:
        response = render_error_page(request, 403, message="何をしてるんです？脆弱性報告のためならいいのですが、データ盗んで悪用するためなら今すぐにやめてくださいね？", joke_message="ディレクトリトラバーサルね、知ってる。公開してないところ覗きたいの？えっt")

    for key, value in headers.items():
        response.headers[key.lower().strip()] = value

    request.scope["nercone.dev"]["options"].apply(response)
    return response

error_messages = {
    400: {"normal": "リクエストの構文が正しくないか、パラメータが不正です。", "joke": "日本語でおk"},
    401: {"normal": "このリソースにアクセスするには認証が必要です。", "joke": "見たいのならログインすることね"},
    402: {"normal": "このリソースへのアクセスには支払いが必要です。", "joke": "夢が欲しけりゃ金払え！"},
    403: {"normal": "このリソースへのアクセス権がありません。", "joke": "あんたなんかに見せるもんですか！"},
    404: {"normal": "リクエストしたページまたはリソースが見つかりません。", "joke": "そんなページ知らないっ！"},
    405: {"normal": "このリソースではそのHTTPメソッドは許可されていません。", "joke": "そのMethodはNot Allowedだよ"},
    406: {"normal": "リクエストのAcceptヘッダーと一致するレスポンスを生成できません。", "joke": "すまんがその条件ではお渡しできない。"},
    407: {"normal": "このリソースにアクセスするにはプロキシの認証が必要です。", "joke": "うちのプロキシ使うんだったらまずログインしな。"},
    408: {"normal": "リクエストが時間内に完了しませんでした。", "joke": "もう用がないならさっさと帰りなさい。"},
    409: {"normal": "現在のリソースの状態とリクエストが競合しています。", "joke": "ちょっと待ったそんな話聞いてないぞ"},
    410: {"normal": "リクエストしたリソースは恒久的に削除されました。", "joke": "もう無いで。"},
    411: {"normal": "リクエストにはContent-Lengthヘッダーが必要です。", "joke": "サイズを教えろ。話はそれからだ。"},
    412: {"normal": "リクエストの前提条件がサーバーの状態と一致しません。", "joke": "なにその条件美味しいの"},
    413: {"normal": "リクエストのボディがサーバーの許容サイズを超えています。", "joke": "そ、そそ、そんなの入りきらないよっ！"},
    414: {"normal": "リクエストURIがサーバーの処理できる長さを超えています。", "joke": "もちつけ"},
    415: {"normal": "リクエストのメディア形式はサポートされていません。", "joke": "そんな形式知らない！"},
    416: {"normal": "リクエストしたレンジはリソースのサイズ内に存在しません。", "joke": "ちっさぁ:heart:"},
    417: {"normal": "リクエストのExpectヘッダーの要件をサーバーが満たせません。", "joke": "期待させて悪かったわね！"},
    418: {"normal": "このサーバーはティーポットです。コーヒーを淹れることはできません。", "joke": "ティーポット「私はコーヒーを注ぐためのものではありません！やだっ！」"},
    421: {"normal": "リクエストが意図しないサーバーに到達しました。", "joke": "またあいつ案内先間違えてるよ...どうしよ..."},
    426: {"normal": "このリクエストを処理するにはプロトコルのアップグレードが必要です。", "joke": "それに答えるには、まずWebSocketに移動したい。"}
}

def render_error_page(request: Request, status_code: int = 500, status_name: str | None = None, message: str | None = None, joke_message: str | None = None) -> Response:
    if 500 <= status_code < 600:
        request.scope["nercone.dev"]["csp"].append("script-src", "'unsafe-inline'")
        request.scope["nercone.dev"]["csp"].append("style-src", "fonts.googleapis.com", "'unsafe-inline'")
        request.scope["nercone.dev"]["csp"].append("font-src", "fonts.gstatic.com")
        return render_page("error/server.html", "error/server", request=request, status_code=status_code, count=False, render=False)
    else:
        if status_name is None:
            try:
                if status_code == 600:
                    status_name = "Not Normal"
                else:
                    status_name = HTTPStatus(status_code).phrase
            except ValueError:
                status_name = "Unknown"

        return render_page("error/client.md", "error/client", request=request, status_code=status_code, count=False, context={
            "status_code": status_code,
            "status_name": status_name,
            "message": message or error_messages.get(status_code, {}).get("normal", "不明なエラーが発生しました。"),
            "joke_message": joke_message or error_messages.get(status_code, {}).get("joke", "あんのーん")
        })

thumbnail_font_dir = Directories.public.joinpath("assets", "fonts")
thumbnail_font_files = [
    str(thumbnail_font_dir / "NerconeSansJP-Regular.ttf"),
    str(thumbnail_font_dir / "NerconeSansJP-Italic.ttf"),
    str(thumbnail_font_dir / "NerconeSansJP-Bold.ttf"),
    str(thumbnail_font_dir / "NerconeSansJP-BoldItalic.ttf"),
    str(thumbnail_font_dir / "NerconeMonoJP-Regular.ttf"),
    str(thumbnail_font_dir / "NerconeMonoJP-Italic.ttf"),
    str(thumbnail_font_dir / "NerconeMonoJP-Bold.ttf"),
    str(thumbnail_font_dir / "NerconeMonoJP-BoldItalic.ttf")
]

def render_thumbnail_svg(path: str = "/", title: str = "Untitled Page", description: str = "No description.", template: str = "normal") -> str:
    if file := resolve_file(f"/assets/images/thumbnail/template/{template}.svg"):
        parts = [p for p in path.strip("/").split("/") if p]
        svg = file.read_text(encoding="utf-8")
        svg = svg.replace("__PATH__", escape("nercone.dev/" + "/".join(parts) if parts else "nercone.dev"))
        svg = svg.replace("__TITLE__", escape(title))
        svg = svg.replace("__DESCRIPTION__", escape(description))
        return svg
    else:
        raise FileNotFoundError()

def render_thumbnail_png(path: str = "/", title: str = "Untitled Page", description: str = "No description.", template: str = "normal") -> bytes:
    svg = render_thumbnail_svg(path=path, title=title, description=description, template=template)
    png = resvg_py.svg_to_bytes(svg, font_files=thumbnail_font_files, width=1280, height=640)
    return png
