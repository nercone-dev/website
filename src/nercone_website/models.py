import time
import json
import rjsmin
import rcssmin
import hashlib
import ipaddress
import minify_html
from scour import scour
from pathlib import Path
from urllib.parse import parse_qs
from email.utils import formatdate, parsedate_to_datetime
from typing import Optional, Union, List, Dict, Tuple

from aki import Request, Message, Method, Cookie, SetCookie
from soyokaze import SameSite

from .constants import reserved_cookie_keys

class URL:
    def __init__(self, scheme: str, host: str, port: Optional[int], path: str, query: str, fragment: str):
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment

    @classmethod
    def parse_authority(cls, authority: str) -> Tuple[str, Optional[int]]:
        if not authority:
            return "", None

        if authority.startswith("["):
            end = authority.find("]")
            if end == -1:
                return authority, None

            host = authority[1:end]
            remainder = authority[end + 1:]

            if remainder.startswith(":") and remainder[1:].isdecimal():
                return host, int(remainder[1:])

            return host, None

        host, separator, port = authority.rpartition(":")
        if separator and port.isdecimal():
            return host, int(port)

        return authority, None

    @classmethod
    def split_target(cls, target: str) -> Tuple[str, str, str]:
        remainder, _, fragment = target.partition("#")
        path, _, query = remainder.partition("?")
        return path, query, fragment

    @classmethod
    def from_target(cls, target: str, scheme: str = "http", authority: str = "") -> "URL":
        if target == "*":
            host, port = cls.parse_authority(authority)
            return cls(scheme, host, port, "*", "", "")

        if "://" in target:
            head, _, remainder = target.partition("://")

            end = len(remainder)
            for separator in ("/", "?", "#"):
                index = remainder.find(separator)
                if index != -1:
                    end = min(end, index)

            host, port = cls.parse_authority(remainder[:end])
            path, query, fragment = cls.split_target(remainder[end:])

            return cls(head, host, port, path or "/", query, fragment)

        if target.startswith("/"):
            path, query, fragment = cls.split_target(target)
            host, port = cls.parse_authority(authority)
            return cls(scheme, host, port, path, query, fragment)

        host, port = cls.parse_authority(target)
        return cls(scheme, host, port, "", "", "")

    @property
    def params(self) -> Dict[str, List[str]]:
        return parse_qs(self.query, keep_blank_values=True)

    @property
    def netloc(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host

        if self.port is not None:
            return f"{host}:{self.port}"

        return host

    def __str__(self) -> str:
        if self.path == "*":
            return "*"

        result = f"{self.scheme}://{self.netloc}{self.path}" if self.host else self.path

        if self.query:
            result += f"?{self.query}"

        if self.fragment:
            result += f"#{self.fragment}"

        return result

class CommaHeader:
    def __init__(self, value: Union[str, List[str]]):
        self.raw = CommaHeader.parse(value).raw if isinstance(value, str) else list(value)

    @classmethod
    def parse(cls, value: str) -> "CommaHeader":
        return cls([item.strip() for item in value.split(",") if item.strip()])

    def append(self, value: str):
        if value not in self.raw:
            self.raw.append(value)

    def remove(self, value: str):
        self.raw.remove(value)

    def build(self) -> str:
        return ", ".join(self.raw)

    def __contains__(self, value: str) -> bool:
        return value in self.raw

    def __str__(self) -> str:
        return self.build()

class Minifier:
    max_offload_filesize = 32768

    essences = ("text/html", "text/css", "text/javascript", "application/javascript", "image/svg", "application/json")

    @classmethod
    def essence(cls, content_type: str) -> str:
        return content_type.split(";")[0].strip().lower()

    @classmethod
    def minify(cls, body: bytes, content_type: str) -> bytes:
        essence = cls.essence(content_type)
        content = body.decode("utf-8", errors="replace")

        if essence.startswith("text/html"):
            return minify_html.minify(content, minify_js=True, minify_css=True, keep_comments=True, keep_html_and_head_opening_tags=True).encode("utf-8")

        elif essence.startswith("text/css"):
            return rcssmin.cssmin(content).encode("utf-8")

        elif essence.startswith(("text/javascript", "application/javascript")):
            return rjsmin.jsmin(content).encode("utf-8")

        elif essence.startswith("image/svg"):
            options = scour.generateDefaultOptions()
            options.newlines = False
            options.shorten_ids = True
            options.strip_comments = True

            return scour.scourString(content, options).encode("utf-8")

        elif essence.startswith("application/json"):
            return json.dumps(json.loads(content)).encode("utf-8")

        return body

    @classmethod
    def body(cls, message: Message) -> Optional[bytes]:
        if (body := message.body_inline()) is not None:
            return body

        if (path := message.body_path()) is None:
            return None

        file = Path(path)
        if not 0 < file.stat().st_size <= cls.max_offload_filesize:
            return None

        return file.read_bytes()

    @classmethod
    def apply(cls, message: Message):
        content_type = message.header("content-type") or ""
        if not cls.essence(content_type).startswith(cls.essences):
            return

        try:
            if (body := cls.body(message)) is None:
                return

            minified = cls.minify(body, content_type)

        except Exception:
            return

        if minified != body:
            message.set_body(minified)

class Conditional:
    methods = (Method.GET, Method.HEAD)

    digest_size = 16

    @classmethod
    def opaque(cls, etag: str) -> str:
        return etag.strip().removeprefix("W/").strip()

    @classmethod
    def matches(cls, condition: str, etag: str) -> bool:
        if condition.strip() == "*":
            return True

        return any(cls.opaque(candidate) == cls.opaque(etag) for candidate in CommaHeader(condition).raw)

    @classmethod
    def timestamp(cls, condition: str) -> Optional[float]:
        try:
            return parsedate_to_datetime(condition).timestamp()
        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def validators(cls, message: Message) -> Tuple[Optional[str], Optional[float]]:
        if (body := message.body_inline()) is not None:
            return f'"{hashlib.blake2b(body, digest_size=cls.digest_size).hexdigest()}"', None

        if (path := message.body_path()) is not None:
            try:
                status = Path(path).stat()
            except OSError:
                return None, None

            return f'"{status.st_mtime_ns:x}-{status.st_size:x}"', status.st_mtime

        return None, None

    @classmethod
    def fresh(cls, request: Request, etag: str, modified: Optional[float]) -> bool:
        if (condition := request.header("if-none-match")) is not None:
            return cls.matches(condition, etag)

        if (condition := request.header("if-modified-since")) is not None and modified is not None:
            since = cls.timestamp(condition)
            return since is not None and int(modified) <= int(since)

        return False

    @classmethod
    def apply(cls, request: Request, response: Message) -> bool:
        if response.status_code != 200 or request.method not in cls.methods:
            return False

        etag, modified = cls.validators(response)
        if etag is None:
            return False

        response.insert_header("ETag", f"W/{etag}")

        if modified is not None:
            response.insert_header("Last-Modified", formatdate(modified, usegmt=True))

        if not cls.fresh(request, etag, modified):
            return False

        response.status_code = 304
        response.clear_body()
        response.remove_header("content-length")

        return True

class PPManager:
    def __init__(self):
        self.initial = True
        self.directives: Dict[str, List[str]] = {
            "camera": [],
            "microphone": [],
            "geolocation": [],
            "payment": [],
            "usb": [],
            "accelerometer": [],
            "gyroscope": [],
            "magnetometer": [],
            "display-capture": []
        }

    def set(self, key: str, value: List[str], override: bool = True):
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def append(self, key: str, *values: str):
        self.initial = False
        if key not in self.directives:
            self.directives[key] = list(values)
        else:
            self.directives[key] += list(values)

    def remove(self, key: str):
        self.initial = False
        self.directives.pop(key, None)

    @property
    def header(self) -> str:
        parts = []
        for key, value in self.directives.items():
            if value == ["*"]:
                parts.append(f"{key}=*")
            elif value:
                parts.append(f"{key}=({' '.join(value)})")
            else:
                parts.append(f"{key}=()")
        return ", ".join(parts)

class CSPManager:
    def __init__(self):
        self.initial = True
        self.directives: Dict[str, Union[List[str], bool]] = {
            "default-src": ["'none'"],
            "script-src": ["assets.nercone.dev"],
            "style-src": ["assets.nercone.dev"],
            "font-src": ["assets.nercone.dev"],
            "img-src": ["assets.nercone.dev", "t3tra.dev", "drsb.f5.si"],
            "manifest-src": ["nercone.dev"],
            "connect-src": ["'self'"],
            "frame-src": ["snowflake.torproject.org", "embed-snowflake.torproject.org"],
            "frame-ancestors": ["'self'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "upgrade-insecure-requests": True,
            "report-to": "csp-endpoint"
        }

    def set(self, key: str, value: Union[List[str], bool], override: bool = True):
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def append(self, key: str, *values: str):
        self.initial = False
        if key not in self.directives:
            self.directives[key] = list(values)
        else:
            self.directives[key] += list(values)

    def remove(self, key: str):
        self.initial = False
        self.directives.pop(key, None)

    @property
    def header(self) -> str:
        parts = []
        for key, value in self.directives.items():
            if isinstance(value, bool) and value:
                parts.append(key)
            elif isinstance(value, str) and value:
                parts.append(f"{key} {value}")
            else:
                parts.append(f"{key} {' '.join(value)}")
        return "; ".join(parts).strip()

class CCManager:
    def __init__(self):
        self.initial = True
        self.directives: Dict[str, Union[int, bool]] = {}

    def set(self, key: str, value: Union[int, bool] = True, override: bool = True):
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def remove(self, key: str):
        self.initial = False
        self.directives.pop(key, None)

    @property
    def header(self) -> str:
        parts = []
        for key, value in self.directives.items():
            if value is True:
                parts.append(key)
            elif isinstance(value, int):
                parts.append(f"{key}={value}")
        return ", ".join(parts)

class TimingManager:
    def __init__(self):
        self.timings: Dict[str, List[float, Optional[float], Optional[str]]] = {}

    def start(self, key: str, description: Optional[str] = None) -> float:
        if key in self.timings:
            n = 1
            while f"{key}-{n}" in self.timings:
                n += 1
            key = f"{key}-{n}"
        now = time.perf_counter()
        self.timings[key] = [now, None, description]
        return now

    def stop(self, key: str, description: Optional[str] = None) -> float:
        candidates = [k for k in self.timings if k == key or (k.startswith(f"{key}-") and k[len(key) + 1:].isdigit())]
        assert candidates
        key = max(candidates, key=lambda k: self.timings[k][0])
        now = time.perf_counter()
        self.timings[key] = [self.timings[key][0], now, description or self.timings[key][2]]
        return now

    @property
    def header(self) -> str:
        headers = []
        sorted_timings = sorted(((key, value) for key, value in self.timings.items() if value[1] is not None), key=lambda item: item[1][1])
        for key, value in sorted_timings:
            duration = round((value[1] - value[0]) * 1000, 3)
            headers.append(f"{key}{f';desc=\"{value[2]}\"' if value[2] is not None else ''};dur={duration}")
        return ", ".join(headers)

class NetworkManager:
    trusted_networks = [ipaddress.ip_network(network) for network in [
        "127.0.0.0/8",
        "169.254.0.0/16",

        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",

        "100.64.0.0/10",

        "::1/128",
        "fc00::/7",
        "fe80::/10"
    ]]

    def __init__(self, client: Optional[str]):
        self.host, self.port = NetworkManager.parse_client(client)
        self.address = NetworkManager.parse_address(self.host)
        self.trusted = any(self.address in network for network in self.trusted_networks) if self.address else False

    @classmethod
    def parse_client(cls, client: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
        if not client:
            return None, None

        host, port = URL.parse_authority(client)
        return host or None, port

    @classmethod
    def parse_address(cls, host: Optional[str]) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        try:
            address = ipaddress.ip_address(host) if host else None
        except ValueError:
            return None

        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            return address.ipv4_mapped

        return address

class OptionManager:
    options = {
        "dev.nercone.options.appearance.theme": "system"
    }

    def __init__(self, request: Request):
        self.request = request
        self.params = request.scope["url"].params
        self.cookies = dict(Cookie.parse(header).pairs()) if (header := request.header("cookie")) else {}

    def __contains__(self, key: str):
        return key in self.params or key in self.cookies

    def __len__(self):
        return len(set(self.cookies) | set(self.params))

    @classmethod
    def cookie(cls, key: str, value: str, *, secure: bool = False) -> SetCookie:
        cookie = SetCookie(key, value)
        cookie.path = "/"
        cookie.secure = secure
        cookie.samesite = SameSite.LAX
        return cookie

    def get(self, key: str, default: Optional[str] = None):
        once_values = self.params.get(key + ".once")
        once = once_values[0] if once_values else None
        query_values = self.params.get(key)
        query = query_values[0] if query_values else None
        cookie = self.cookies.get(key, None)
        return once or query or cookie or default or self.options.get(key)

    def set(self, response: Message, key: str, value: str):
        response.set_cookie(OptionManager.cookie(key, value))

    def apply(self, response: Message):
        for key in self.params:
            if key.lower() in reserved_cookie_keys:
                continue
            if key in self.options and not key.endswith(".once") and self.cookies.get(key) != self.params.get(key)[0]:
                if (self.params.get(key)[0] or self.cookies.get(key)) != self.options.get(key):
                    response.set_cookie(OptionManager.cookie(key, self.params[key][0], secure=True))
                else:
                    response.delete_cookie(OptionManager.cookie(key, "", secure=True))
