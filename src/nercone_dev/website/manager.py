import time
import ipaddress
from fastapi import Response
from starlette.requests import Request, HTTPConnection
from ..constants import reserved_cookie_keys

class PPManager:
    def __init__(self):
        self.initial = True
        self.directives: dict[str, list[str]] = {
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

    def set(self, key: str, value: list[str], override: bool = True):
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
        self.directives: dict[str, list[str] | bool] = {
            "default-src": ["'none'"],
            "script-src": ["'self'", "assets.nercone.dev"],
            "style-src": ["'self'", "assets.nercone.dev"],
            "font-src": ["'self'", "assets.nercone.dev"],
            "img-src": ["'self'", "assets.nercone.dev", "t3tra.dev", "drsb.f5.si"],
            "manifest-src": ["'self'"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'self'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "upgrade-insecure-requests": True,
            "report-to": "csp-endpoint"
        }

    def set(self, key: str, value: list[str] | bool, override: bool = True):
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
        self.directives: dict[str, int | bool] = {}

    def set(self, key: str, value: int | bool = True, override: bool = True):
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
        self.timings: dict[str, list[float, float | None, str | None]] = {}

    def start(self, key: str, description: str | None = None) -> float:
        if key in self.timings:
            n = 1
            while f"{key}-{n}" in self.timings:
                n += 1
            key = f"{key}-{n}"
        now = time.perf_counter()
        self.timings[key] = [now, None, description]
        return now

    def stop(self, key: str, description: str | None = None) -> float:
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

    def __init__(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address | None, host: str | None, port: int | None):
        self.address = address
        self.host = host
        self.port = port
        self.trusted = (address is not None and any(address in network for network in self.trusted_networks))

class OptionManager:
    options = {
        "dev.nercone.options.appearance.theme": "dark"
    }

    def __init__(self, request: HTTPConnection | Request):
        self.request = request

    def __contains__(self, key: str):
        return key in self.request.query_params or key in self.request.cookies

    def __len__(self):
        return len(self.request.cookies | self.request.query_params)

    def get(self, key: str, default: str | None = None):
        once = self.request.query_params.get(key + ".once", None)
        query = self.request.query_params.get(key, None)
        cookie = self.request.cookies.get(key, None)
        return once or query or cookie or default or self.options.get(key)

    def set(self, response: Response, key: str, value: str):
        response.set_cookie(key, value, samesite="lax")

    def apply(self, response: Response):
        queries = self.request.query_params
        cookies = self.request.cookies
        for key in queries:
            if key.lower() in reserved_cookie_keys:
                continue
            if key in self.options and not key.endswith(".once") and cookies.get(key) != queries.get(key):
                if (queries.get(key) or cookies.get(key)) != self.options.get(key):
                    response.set_cookie(key, queries[key], secure=True, samesite="lax")
                else:
                    response.delete_cookie(key, secure=True, samesite="lax")
