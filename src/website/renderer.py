import io
import re
import json
import yaml
import jinja2
import random
import resvg_py
from bs4 import BeautifulSoup
from http import HTTPStatus
from html import escape as html_escape
from typing import Optional, Any, Literal, Dict, Tuple
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import Response, PlainTextResponse, HTMLResponse, FileResponse, RedirectResponse

import mistune
from markitdown import MarkItDown, StreamInfo

from .helpers import Counter, ServerTiming
from .resolver import resolve_static, resolve_template, resolve_page, resolve_redirects
from .constants import Startup, Directories, Files

templates = jinja2.Environment(loader=jinja2.FileSystemLoader(Directories.templates), autoescape=False)

class CustomHTMLRenderer(mistune.HTMLRenderer):
    alert_re = re.compile(r'^\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\n(.*?))?</p>\s*', re.IGNORECASE | re.DOTALL)

    def block_code(self, code: str, **attrs: Any) -> str:
        return f'<pre>{mistune.escape(code)}</pre>\n'

    def block_quote(self, text: str) -> str:
        m = self.alert_re.match(text)
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

def init_context(context: Dict[str, Any], request: Request) -> None:
    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]
    context.update(request.scope)

    context["startid"] = Startup.id
    context["version"] = Startup.version

    context["url"]            = request.scope["nercone"]["request"]["url"]
    context["access_id"]      = request.scope["nercone"]["request"]["id"]
    context["access_counter"] = Counter(Files.access_counter)

    context["re_sub"] = lambda s, pattern, repl: re.sub(pattern, repl, s)

    context["this_year"]           = datetime.now(ZoneInfo("Asia/Tokyo")).year
    context["this_year_in_heisei"] = datetime.now(ZoneInfo("Asia/Tokyo")).year - 1988

    def daily_quote() -> str:
        if file := resolve_static("quotes.txt", timings=timings):
            quotes = file.read_text().strip().split("\n")

            daily_seed = str(datetime.now(timezone.utc).date())
            return random.Random(daily_seed).choice(quotes)
        else:
            return "GReeeeN KA-RA-DA"
    context["daily_quote"] = daily_quote

def render_mode(request: Request) -> Literal["html", "markdown"]:
    if any([request.scope["nercone"]["request"]["url"].path.endswith(".md"), "text/markdown" in (request.headers.get("accept", "")).lower(), (request.headers.get("user-agent", "")).lower().startswith("curl")]):
        return "markdown"
    else:
        return "html"

async def render_page(page: str, request: Request, render: bool = True, status_code: int = 200, context: Optional[Dict[str, Any]] = None, mode: Optional[Literal["html", "markdown"]] = None) -> Response:
    if context is None:
        context = {}

    init_context(context, request)
    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]

    if mode is None:
        mode = render_mode(request)

    if not page.endswith((".html", ".md")):
        raise ValueError(f"Unsupported page type: {page}")

    filepath = resolve_template(page, timings=timings)
    if filepath is None:
        raise FileNotFoundError(f"Page not found: {page}")

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
        content = templates.from_string(body).render(request=request, **context)
        timings.stop("render")

        def render_html(html: str) -> str:
            if "base" in front:
                if front["base"].startswith("/"):
                    source = f"{{% extends \"{front['base']}\" %}}\n"
                else:
                    source = f"{{% extends \"/base/{front['base']}.html\" %}}\n"
            else:
                source = "{% extends \"/base/default.html\" %}\n"

            for key, value in front.items():
                source += f"{{% block {key} %}}{value}{{% endblock %}}\n"

            source += f"{{% block main %}}\n{html}\n{{% endblock %}}\n"
            return templates.from_string(source).render(request=request, **context)

        if page.endswith(".html"):
            if mode == "html":
                timings.start("render", "Render Final HTML")
                content = render_html(content)
                timings.stop("render")

                response = HTMLResponse(content, status_code=status_code)

            elif mode == "markdown":
                timings.start("convert", "HTML to Markdown")
                soup = BeautifulSoup(content, "html.parser")
                main = str(soup.find("main")) if soup.find("main") else content
                content = markitdown.convert(io.BytesIO(main.encode("utf-8")), stream_info=StreamInfo(mimetype="text/html", charset="utf-8")).text_content
                timings.stop("convert")

                response = PlainTextResponse(content, status_code=status_code, media_type="text/markdown; charset=utf-8")

        elif page.endswith(".md"):
            if mode == "html":
                timings.start("convert", "Markdown to HTML")
                main = str(htmlitdown(content))
                timings.stop("convert")

                timings.start("render", "Render Final HTML")
                content = render_html(main)
                timings.stop("render")

                response = HTMLResponse(content, status_code=status_code)

            elif mode == "markdown":
                response = PlainTextResponse(content, status_code=status_code, media_type="text/markdown; charset=utf-8")

    else:
        if page.endswith(".html"):
            response = HTMLResponse(source, status_code=status_code)
        elif page.endswith(".md"):
            response = PlainTextResponse(source, status_code=status_code, media_type="text/markdown; charset=utf-8")

    if "compression" in front:
        if front["compression"].lower() == "true":
            request.scope["nercone"]["response"]["compression"] = True
        elif front["compression"].lower() == "false":
            request.scope["nercone"]["response"]["compression"] = False

    return response

async def default_response(path: str, request: Request, status_code: int = 200, render: bool = True, context: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, mode: Optional[Literal["html", "markdown"]] = None) -> Response:
    if headers is None:
        headers = {}

    if mode is None:
        mode = render_mode(request)

    timings = request.scope["nercone"]["response"]["headers"]["server-timing"]

    try:
        if url := resolve_redirects(path, timings=timings):
            response = RedirectResponse(url)
            response.status_code = status_code if 300 <= status_code < 400 else 307

        elif page := resolve_page(path, mode=mode, timings=timings):
            response = await render_page(page, request=request, render=render, status_code=status_code, context=context, mode=mode)

        elif file := resolve_static(path, timings=timings):
            response = FileResponse(file)
            response.status_code = status_code

        else:
            response = await render_error_page(request, 404, message="リクエストしたページは現在ご利用になれません。削除/移動されたか、URLが間違っている可能性があります。", joke_message="そんなページ知らないっ！")

    except PermissionError:
        response = await render_error_page(request, 403, message="何をしてるんです？脆弱性報告のためならいいのですが、データ盗んで悪用するためなら今すぐにやめてくださいね？", joke_message="ディレクトリトラバーサルね、知ってる。公開してないところ覗きたいの？えっt")

    for key, value in headers.items():
        response.headers.append(key.lower().strip(), value)

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

async def render_error_page(request: Request, status_code: int = 500, status_name: Optional[str] = None, message: Optional[str] = None, joke_message: Optional[str] = None) -> Response:
    if 500 <= status_code < 600:
        request.scope["nercone"]["response"]["headers"]["content-security-policy"].append("script-src", "'unsafe-inline'")
        request.scope["nercone"]["response"]["headers"]["content-security-policy"].append("style-src", "fonts.googleapis.com", "'unsafe-inline'")
        request.scope["nercone"]["response"]["headers"]["content-security-policy"].append("font-src", "fonts.gstatic.com")
        return await render_page("error/server.html", request=request, status_code=status_code, render=False)
    else:
        if status_name is None:
            try:
                if status_code == 600:
                    status_name = "Not Normal"
                else:
                    status_name = HTTPStatus(status_code).phrase
            except ValueError:
                status_name = "Unknown"

        return await render_page("error/client.md", request=request, status_code=status_code, context={
            "status_code": status_code,
            "status_name": status_name,
            "message": message or error_messages.get(status_code, {}).get("normal", "不明なエラーが発生しました。"),
            "joke_message": joke_message or error_messages.get(status_code, {}).get("joke", "あんのーん")
        })

def render_thumbnail_svg(path: str = "/", title: str = "Untitled Page", description: str = "No description.", *, template: str = "normal", timings: Optional[ServerTiming] = None) -> str:
    file = resolve_static(f"/assets/images/templates/thumbnail/{template}.svg", timings=timings)
    if file is None:
        raise FileNotFoundError()

    if timings:
        timings.start("render", "Render Thumbnail SVG")

    parts = [p for p in path.strip("/").split("/") if p]
    svg = file.read_text(encoding="utf-8")
    svg = svg.replace("__PATH__", html_escape("nercone.dev/" + "/".join(parts) if parts else "nercone.dev"))
    svg = svg.replace("__TITLE__", html_escape(title))
    svg = svg.replace("__DESCRIPTION__", html_escape(description))

    if timings:
        timings.stop("render")

    return svg

def render_thumbnail_png(path: str = "/", title: str = "Untitled Page", description: str = "No description.", *, width: int = 1280, height: int = 640, template: str = "normal", timings: Optional[ServerTiming] = None) -> bytes:
    svg = render_thumbnail_svg(path, title, description, template=template, timings=timings)

    if timings:
        timings.start("render", "Render Thumbnail PNG")

    png = resvg_py.svg_to_bytes(svg, font_files=[str(file.resolve()) for file in Files.Fonts.ttf], width=width, height=height)

    if timings:
        timings.stop("render")

    return png
