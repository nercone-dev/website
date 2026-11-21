import functools

import xxhash

@functools.lru_cache(maxsize=512)
def compute_xxhash3(body: bytes) -> str:
    return '"' + xxhash.xxh3_128(body).hexdigest() + '"'
