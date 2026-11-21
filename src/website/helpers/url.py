from typing import Optional, Tuple, List, Dict
from urllib.parse import parse_qs

class URL:
    def __init__(self, scheme: str, host: str, port: Optional[int], path: str, query: str, fragment: str) -> None:
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
