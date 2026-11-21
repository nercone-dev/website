import time
from typing import Optional, Union, List, Dict, Tuple

class CommaHeader:
    def __init__(self, value: Union[str, List[str]]) -> None:
        self.raw = CommaHeader.parse(value).raw if isinstance(value, str) else list(value)

    @classmethod
    def parse(cls, value: str) -> "CommaHeader":
        return cls([item.strip() for item in value.split(",") if item.strip()])

    def append(self, value: str) -> None:
        if value not in self.raw:
            self.raw.append(value)

    def remove(self, value: str) -> None:
        self.raw.remove(value)

    def build(self) -> str:
        return ", ".join(self.raw)

    def __contains__(self, value: str) -> bool:
        return value in self.raw

    def __str__(self) -> str:
        return self.build()

class CacheControl:
    def __init__(self) -> None:
        self.initial = True
        self.directives: Dict[str, Union[int, bool]] = {}

    def set(self, key: str, value: Union[int, bool] = True, override: bool = True) -> None:
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def remove(self, key: str) -> None:
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

class ContentSecurityPolicy:
    def __init__(self) -> None:
        self.initial = True
        self.directives: Dict[str, Union[bool, str, List[str]]] = {
            "default-src":     ["'none'"],
            "img-src":         ["assets.nercone.dev", "t3tra.dev", "drsb.f5.si"],
            "font-src":        ["assets.nercone.dev"],
            "style-src":       ["assets.nercone.dev"],
            "script-src":      ["assets.nercone.dev"],
            "manifest-src":    ["nercone.dev"],
            "connect-src":     ["'self'"],
            "frame-src":       ["'self'"],
            "frame-ancestors": ["'self'"],
            "base-uri":        ["'self'"],
            "form-action":     ["'self'"],
            "upgrade-insecure-requests": True,
            "report-to": "csp-endpoint"
        }

    def set(self, key: str, value: Union[bool, str, List[str]], override: bool = True) -> None:
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def append(self, key: str, *values: str) -> None:
        self.initial = False
        current = self.directives.get(key)
        if isinstance(current, list):
            current.extend(value for value in values if value not in current)
        elif isinstance(current, str) and current:
            self.directives[key] = [current, *(value for value in values if value != current)]
        else:
            self.directives[key] = list(values)

    def remove(self, key: str) -> None:
        self.initial = False
        self.directives.pop(key, None)

    @property
    def header(self) -> str:
        parts = []
        for key, value in self.directives.items():
            if isinstance(value, bool):
                if value:
                    parts.append(key)
            elif isinstance(value, str):
                if value:
                    parts.append(f"{key} {value}")
            else:
                parts.append(" ".join([key, *value]))
        return "; ".join(parts).strip()

class PermissionsPolicy:
    def __init__(self) -> None:
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

    def set(self, key: str, value: List[str], override: bool = True) -> None:
        if override or key not in self.directives:
            self.initial = False
            self.directives[key] = value

    def append(self, key: str, *values: str) -> None:
        self.initial = False
        if key not in self.directives:
            self.directives[key] = list(values)
        else:
            self.directives[key] += list(values)

    def remove(self, key: str) -> None:
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

class ServerTiming:
    def __init__(self) -> None:
        self.timings: Dict[str, Tuple[float, Optional[float], Optional[str]]] = {}

    def start(self, key: str, description: Optional[str] = None) -> float:
        if key in self.timings:
            n = 1
            while f"{key}-{n}" in self.timings:
                n += 1
            key = f"{key}-{n}"
        now = time.perf_counter()
        self.timings[key] = (now, None, description)
        return now

    def stop(self, key: str, description: Optional[str] = None) -> float:
        candidates = [k for k in self.timings if (k == key or (k.startswith(f"{key}-") and k[len(key) + 1:].isdigit())) and self.timings[k][1] is None]
        if not candidates:
            raise KeyError(f"No running timing: {key}")
        key = max(candidates, key=lambda k: self.timings[k][0])
        now = time.perf_counter()
        self.timings[key] = (self.timings[key][0], now, description or self.timings[key][2])
        return now

    @property
    def header(self) -> str:
        headers = []
        for key, (start, stop, description) in sorted(self.timings.items(), key=lambda item: item[1][0]):
            if stop is None:
                continue
            entry = key
            if description is not None:
                entry += ";desc=\"" + description.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
            entry += f";dur={round((stop - start) * 1000, 3)}"
            headers.append(entry)
        return ", ".join(headers)
