import json
import functools
from typing import Optional

from fastapi import Response

import minify_html as rhtmin
import rjsmin
import rcssmin
from scour import scour

scour_options = scour.generateDefaultOptions()
scour_options.newlines = False
scour_options.shorten_ids = True
scour_options.strip_comments = True

@functools.lru_cache(maxsize=128)
def minify_html(body: str) -> str:
    return rhtmin.minify(body, minify_js=True, minify_css=True, keep_comments=True, keep_html_and_head_opening_tags=True)

@functools.lru_cache(maxsize=128)
def minify_css(body: str) -> str:
    return str(rcssmin.cssmin(body))

@functools.lru_cache(maxsize=128)
def minify_js(body: str) -> str:
    return str(rjsmin.jsmin(body))

@functools.lru_cache(maxsize=64)
def minify_svg(body: str) -> str:
    return scour.scourString(body, scour_options)

class Minifier:
    max_filesize = 32768

    essences = ("text/html", "text/css", "text/javascript", "application/javascript", "image/svg", "application/json")

    @classmethod
    def essence(cls, content_type: str) -> str:
        return content_type.split(";")[0].strip().lower()

    @classmethod
    def minify(cls, body: bytes, content_type: str) -> bytes:
        essence = cls.essence(content_type)
        content = body.decode("utf-8", errors="replace")

        if essence.startswith("text/html"):
            return minify_html(content).encode("utf-8")

        elif essence.startswith("text/css"):
            return minify_css(content).encode("utf-8")

        elif essence.startswith(("text/javascript", "application/javascript")):
            return minify_js(content).encode("utf-8")

        elif essence.startswith("image/svg"):
            return minify_svg(content).encode("utf-8")

        elif essence.startswith("application/json"):
            return json.dumps(json.loads(content)).encode("utf-8")

        return body

    @classmethod
    def body(cls, response: Response) -> Optional[bytes]:
        body = getattr(response, "body", None)
        if not isinstance(body, (bytes, bytearray, memoryview)):
            return None

        if len(body) > cls.max_filesize:
            return None

        return bytes(body)

    @classmethod
    def apply(cls, response: Response) -> None:
        content_type = response.headers.get("content-type", "")
        if not cls.essence(content_type).startswith(cls.essences):
            return

        try:
            if (body := cls.body(response)) is None:
                return

            minified = cls.minify(body, content_type)

        except Exception:
            return

        if minified != body:
            response.body = minified
