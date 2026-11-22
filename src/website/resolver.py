import json
from typing import Optional, Union, Literal, List
from pathlib import Path

from .helpers import ServerTiming
from .constants import Directories

def ensure_public_path(path: Union[str, Path]) -> Optional[Path]:
    if not Path(path).resolve().is_relative_to(Directories.public):
        raise PermissionError()
    if not Path(path).exists():
        return None
    return Path(path)

def resolve_file(path: str, *, timings: Optional[ServerTiming] = None) -> Optional[Path]:
    if timings:
        timings.start("resolve-file", f"File {path or '/'}")

    try:
        if full_path := ensure_public_path(Directories.public.joinpath(path.lstrip("/"))):
            if full_path.is_file():
                return full_path
        return None
    finally:
        if timings:
            timings.stop("resolve-file")

def resolve_static(path: str, *, timings: Optional[ServerTiming] = None) -> Optional[Path]:
    return resolve_file("static/" + path.lstrip("/"), timings=timings)

def resolve_template(path: str, *, timings: Optional[ServerTiming] = None) -> Optional[Path]:
    return resolve_file("templates/" + path.lstrip("/"), timings=timings)

def page_candidates(path: str, mode: Literal["html", "markdown"] = "html") -> List[str]:
    if path in ["", "/"]:
        stems = ["index", "README"]
    else:
        name = path.removesuffix(".html") if path.endswith(".html") else path.removesuffix(".md")
        name = name.strip("/")
        stems = [name, f"{name}/index", f"{name}/README"]

    html = [f"{stem}.html" for stem in stems]
    markdown = [f"{stem}.md" for stem in stems]
    return html + markdown if mode == "html" else markdown + html

def resolve_page(path: str, *, mode: Literal["html", "markdown"] = "html", timings: Optional[ServerTiming] = None) -> Optional[str]:
    if timings:
        timings.start("resolve-page", f"Page {path or '/'}")

    try:
        for candidate in page_candidates(path, mode):
            if file := resolve_template(candidate, timings=timings):
                return file.relative_to(Directories.templates).as_posix()
        return None
    finally:
        if timings:
            timings.stop("resolve-page")

def resolve_redirects(path: str, *, max_retry: int = 10, timings: Optional[ServerTiming] = None) -> Optional[str]:
    if timings:
        timings.start("resolve-redirect", f"Redirect {path or '/'}")

    try:
        file = resolve_static("redirects.json", timings=timings)
        if file is None:
            return None

        redirects = json.loads(file.read_text())
        current = path.strip("/")
        visited = set()

        for _ in range(max_retry):
            if current in visited or current not in redirects:
                return None
            visited.add(current)

            entry = redirects[current]
            if entry["type"] == "redirect":
                return entry["content"]
            elif entry["type"] == "alias":
                current = entry["content"]

        return None
    finally:
        if timings:
            timings.stop("resolve-redirect")
