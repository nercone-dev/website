import functools
from typing import Optional, Callable, Tuple, Dict

import gzip
import zlib
import zstandard
import brotlicffi

@functools.lru_cache(maxsize=128)
def compress_gzip(body: bytes) -> bytes:
    return gzip.compress(body, compresslevel=6, mtime=0)

@functools.lru_cache(maxsize=128)
def compress_deflate(body: bytes) -> bytes:
    return zlib.compress(body, level=6)

@functools.lru_cache(maxsize=128)
def compress_zstd(body: bytes) -> bytes:
    return zstandard.ZstdCompressor(level=3).compress(body)

@functools.lru_cache(maxsize=128)
def compress_brotli(body: bytes) -> bytes:
    return brotlicffi.compress(body, quality=4)

class Compressor:
    encodings: Dict[str, Callable[[bytes], bytes]] = {
        "zstd": compress_zstd,
        "br": compress_brotli,
        "gzip": compress_gzip,
        "deflate": compress_deflate,
    }

    essences: Tuple[str, ...] = ("text/", "application/javascript", "application/json", "application/manifest+json", "application/xml", "image/svg+xml", "font/ttf", "font/otf")

    min_size: int = 256

    @classmethod
    def essence(cls, content_type: str) -> str:
        return content_type.split(";")[0].strip().lower()

    @classmethod
    def compressible(cls, content_type: str, size: int) -> bool:
        return size >= cls.min_size and cls.essence(content_type).startswith(cls.essences)

    @classmethod
    def parse_accept_encoding(cls, value: str) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for item in value.split(","):
            coding, *parameters = [part.strip() for part in item.split(";")]
            if not coding:
                continue

            weight = 1.0
            for parameter in parameters:
                name, _, raw = parameter.partition("=")
                if name.strip().lower() == "q":
                    try:
                        weight = min(max(float(raw.strip()), 0.0), 1.0)
                    except ValueError:
                        weight = 0.0

            weights[coding.lower()] = weight
        return weights

    @classmethod
    def negotiate(cls, accept_encoding: Optional[str]) -> Optional[str]:
        if not accept_encoding:
            return None

        weights = cls.parse_accept_encoding(accept_encoding)
        wildcard = weights.get("*", 0.0)

        best: Optional[str] = None
        best_weight = 0.0
        for encoding in cls.encodings:
            weight = weights.get(encoding, wildcard)
            if weight > best_weight:
                best, best_weight = encoding, weight
        return best

    @classmethod
    def compress(cls, body: bytes, encoding: str) -> bytes:
        if encoding not in cls.encodings:
            raise ValueError(f"Unsupported content-coding: {encoding}")
        return cls.encodings[encoding](body)
