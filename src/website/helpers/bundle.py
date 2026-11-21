import re
import posixpath
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple

class Bundler:
    def __init__(self, entry: Path, output: Path, root: Path) -> None:
        self.entry = entry
        self.output = output
        self.root = root.resolve()
        self.cache: Optional[Tuple[Dict[Path, Tuple[int, int]], str]] = None

    @staticmethod
    def stat(path: Path) -> Tuple[int, int]:
        result = path.stat()
        return (result.st_mtime_ns, result.st_size)

    def build(self) -> str:
        if self.cache is not None:
            dependencies, content = self.cache
            try:
                if all(Bundler.stat(path) == stamp for path, stamp in dependencies.items()):
                    return content
            except OSError:
                pass

        dependencies = {}
        content = self.render(dependencies)
        self.cache = (dependencies, content)
        return content

    def render(self, dependencies: Dict[Path, Tuple[int, int]]) -> str:
        raise NotImplementedError()

    def locate(self, specifier: str, importer: Path) -> Path:
        if not specifier.startswith(("./", "../")):
            raise ValueError(f"Only relative imports can be bundled: {specifier!r} in {importer}")

        path = importer.parent.joinpath(specifier).resolve()
        if not path.is_relative_to(self.root):
            raise PermissionError(f"Import outside of the bundle root: {specifier!r} in {importer}")
        if not path.is_file():
            raise FileNotFoundError(f"Imported file not found: {specifier!r} in {importer}")
        return path

    def read(self, path: Path, dependencies: Dict[Path, Tuple[int, int]]) -> str:
        dependencies[path] = Bundler.stat(path)
        return path.read_text(encoding="utf-8").removeprefix("﻿")

    def label(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

class CSSBundler(Bundler):
    scheme = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
    identifier = re.compile(r"[A-Za-z0-9_-]")

    def render(self, dependencies: Dict[Path, Tuple[int, int]]) -> str:
        return self.render_file(self.entry.resolve(), [], dependencies)

    def render_file(self, path: Path, chain: List[Path], dependencies: Dict[Path, Tuple[int, int]]) -> str:
        text = self.read(path, dependencies)
        chain = chain + [path]
        parts: List[str] = [f"/* {self.label(path)} */\n"]

        position = 0
        while True:
            position = CSSBundler.skip_blank(text, position)
            end = CSSBundler.find_statement_end(text, position)

            if text.startswith("@charset ", position):
                if end is None:
                    raise ValueError(f"Unterminated @charset in {path}")
                encoding = text[position + len("@charset "):end].strip().strip("\"'").lower()
                if encoding != "utf-8":
                    raise ValueError(f"Only UTF-8 stylesheets can be bundled: {path}")
                position = end + 1

            elif text[position:position + len("@import")].lower() == "@import" and not CSSBundler.identifier.match(text[position + len("@import"):position + len("@import") + 1]):
                if end is None:
                    raise ValueError(f"Unterminated @import in {path}")
                parts.append(self.render_import(text[position + len("@import"):end], path, chain, dependencies))
                position = end + 1

            elif text[position:position + len("@layer")].lower() == "@layer" and end is not None:
                parts.append(text[position:end + 1] + "\n")
                position = end + 1

            else:
                break

        parts.append(self.rebase(text[position:], path))
        return "".join(parts).rstrip() + "\n"

    def render_import(self, prelude: str, importer: Path, chain: List[Path], dependencies: Dict[Path, Tuple[int, int]]) -> str:
        specifier, conditions = CSSBundler.parse_import(prelude.strip(), importer)
        path = self.locate(specifier, importer)
        if path in chain:
            return ""

        content = self.render_file(path, chain, dependencies)

        layer, supports, media = conditions
        if layer is not None:
            content = f"@layer {layer} {{\n{content}}}\n" if layer else f"@layer {{\n{content}}}\n"
        if supports is not None:
            content = f"@supports ({supports}) {{\n{content}}}\n"
        if media:
            content = f"@media {media} {{\n{content}}}\n"
        return content

    @staticmethod
    def parse_import(prelude: str, importer: Path) -> Tuple[str, Tuple[Optional[str], Optional[str], str]]:
        if prelude[:1] in ("\"", "'"):
            end = CSSBundler.skip_string(prelude, 0)
            specifier = prelude[1:end - 1]
        elif prelude[:4].lower() == "url(":
            end = CSSBundler.find_close(prelude, 3)
            specifier = prelude[4:end].strip().strip("\"'")
            end += 1
        else:
            raise ValueError(f"Malformed @import in {importer}: {prelude!r}")

        if "\\" in specifier:
            raise ValueError(f"Escaped @import URLs cannot be bundled: {specifier!r} in {importer}")

        rest = prelude[end:].strip()

        layer: Optional[str] = None
        if rest[:6].lower() == "layer(":
            close = CSSBundler.find_close(rest, 5)
            layer = rest[6:close].strip()
            rest = rest[close + 1:].strip()
        elif rest[:5].lower() == "layer" and not CSSBundler.identifier.match(rest[5:6]):
            layer = ""
            rest = rest[5:].strip()

        supports: Optional[str] = None
        if rest[:9].lower() == "supports(":
            close = CSSBundler.find_close(rest, 8)
            supports = rest[9:close].strip()
            rest = rest[close + 1:].strip()

        return specifier, (layer, supports, rest)

    def rebase(self, text: str, path: Path) -> str:
        base = posixpath.relpath(path.parent.as_posix(), self.output.resolve().parent.as_posix())
        if base == ".":
            return text

        parts: List[str] = []
        position = 0
        index = 0
        while index < len(text):
            character = text[index]
            if text.startswith("/*", index):
                index = CSSBundler.skip_comment(text, index)
            elif character in ("\"", "'"):
                index = CSSBundler.skip_string(text, index)
            elif text[index:index + 4].lower() == "url(" and (index == 0 or not CSSBundler.identifier.match(text[index - 1])):
                close = CSSBundler.find_close(text, index + 3)
                url = text[index + 4:close].strip()
                if url[:1] in ("\"", "'"):
                    url = url[1:-1]
                if CSSBundler.relative(url):
                    if "\\" in url or "\"" in url:
                        raise ValueError(f"Escaped url() values cannot be bundled: {url!r} in {path}")
                    target = re.split(r"[?#]", url, maxsplit=1)[0]
                    parts.append(text[position:index])
                    parts.append(f"url(\"{posixpath.normpath(posixpath.join(base, target))}{url[len(target):]}\")")
                    position = close + 1
                index = close + 1
            else:
                index += 1

        parts.append(text[position:])
        return "".join(parts)

    @staticmethod
    def relative(url: str) -> bool:
        return bool(url) and not url.startswith(("/", "#")) and not CSSBundler.scheme.match(url)

    @staticmethod
    def skip_blank(text: str, index: int) -> int:
        while index < len(text):
            if text[index].isspace():
                index += 1
            elif text.startswith("/*", index):
                index = CSSBundler.skip_comment(text, index)
            else:
                break
        return index

    @staticmethod
    def skip_comment(text: str, index: int) -> int:
        end = text.find("*/", index + 2)
        return len(text) if end == -1 else end + 2

    @staticmethod
    def skip_string(text: str, index: int) -> int:
        quote = text[index]
        index += 1
        while index < len(text):
            if text[index] == "\\":
                index += 2
            elif text[index] == quote or text[index] == "\n":
                return index + 1
            else:
                index += 1
        return index

    @staticmethod
    def find_close(text: str, index: int) -> int:
        depth = 0
        while index < len(text):
            character = text[index]
            if text.startswith("/*", index):
                index = CSSBundler.skip_comment(text, index)
                continue
            if character in ("\"", "'"):
                index = CSSBundler.skip_string(text, index)
                continue
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    return index
            index += 1
        raise ValueError(f"Unbalanced parentheses: {text[:64]!r}")

    @staticmethod
    def find_statement_end(text: str, index: int) -> Optional[int]:
        depth = 0
        while index < len(text):
            character = text[index]
            if text.startswith("/*", index):
                index = CSSBundler.skip_comment(text, index)
                continue
            if character in ("\"", "'"):
                index = CSSBundler.skip_string(text, index)
                continue
            if character in "([":
                depth += 1
            elif character in ")]":
                depth -= 1
            elif character == "{" and depth == 0:
                return None
            elif character == ";" and depth == 0:
                return index
            index += 1
        return None

class JSBundler(Bundler):
    side_effect_import = re.compile(r"""import\s*(["'])((?:(?!\1)[^\\\n])*)\1\s*;?""")
    keyword_end = re.compile(r"[A-Za-z0-9_$]")

    def render(self, dependencies: Dict[Path, Tuple[int, int]]) -> str:
        parts: List[str] = []
        visited: Set[Path] = set()
        self.render_module(self.entry.resolve(), visited, parts, dependencies)
        return "".join(parts)

    def render_module(self, path: Path, visited: Set[Path], parts: List[str], dependencies: Dict[Path, Tuple[int, int]]) -> None:
        visited.add(path)
        text = self.read(path, dependencies)

        position = 0
        while True:
            position = JSBundler.skip_blank(text, position)
            if not text.startswith("import", position) or JSBundler.keyword_end.match(text[position + len("import"):position + len("import") + 1]):
                break

            next_character = text[JSBundler.skip_blank(text, position + len("import")):][:1]
            if next_character in ("(", "."):
                break

            match = JSBundler.side_effect_import.match(text, position)
            if match is None:
                raise ValueError(f"Only side-effect imports can be bundled: {text[position:text.find(chr(10), position)]!r} in {path}")

            dependency = self.locate(match.group(2), path)
            if dependency not in visited:
                self.render_module(dependency, visited, parts, dependencies)
            position = match.end()

        body = text[position:].strip()
        if body:
            parts.append(f"// {self.label(path)}\n(function () {{\n\"use strict\";\n{body}\n}})();\n")

    @staticmethod
    def skip_blank(text: str, index: int) -> int:
        while index < len(text):
            if text[index].isspace():
                index += 1
            elif text.startswith("//", index):
                end = text.find("\n", index)
                index = len(text) if end == -1 else end + 1
            elif text.startswith("/*", index):
                end = text.find("*/", index + 2)
                index = len(text) if end == -1 else end + 2
            else:
                break
        return index
