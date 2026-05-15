"""Tiny on-disk HTTP cache.

Most free-tier market data APIs are rate-limited; caching identical GET requests
for a few seconds makes ``analyze`` + ``price`` + ``ta`` calls on the same symbol
share results. Uses :mod:`diskcache` (LRU, sqlite-backed).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import requests

try:
    import diskcache  # type: ignore
except ImportError:  # pragma: no cover
    diskcache = None  # cache becomes a no-op


CACHE_DIR = Path(os.environ.get("HERMES_CACHE_DIR", "/tmp/hermes-cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_TTL = int(os.environ.get("HERMES_CACHE_TTL", "60"))  # seconds

_cache = diskcache.Cache(str(CACHE_DIR), size_limit=200 * 1024 * 1024) if diskcache else None


def _key(method: str, url: str, params: Mapping[str, Any] | None,
         headers: Mapping[str, str] | None) -> str:
    raw = json.dumps(
        {"m": method.upper(), "u": url, "p": params or {}, "h": dict(headers or {})},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def cached_get(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    ttl: int = DEFAULT_TTL,
    timeout: float = 15.0,
) -> requests.Response:
    """``requests.get`` with on-disk caching keyed by URL + params + headers."""
    k = _key("GET", url, params, headers)
    if _cache is not None:
        hit = _cache.get(k)
        if hit is not None:
            r = requests.Response()
            r._content, r.status_code, r.encoding = hit[0], hit[1], "utf-8"
            return r
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if _cache is not None and resp.status_code == 200:
        _cache.set(k, (resp.content, resp.status_code), expire=ttl)
    return resp


def invalidate(prefix: str = "") -> int:
    """Drop all entries whose URL starts with ``prefix`` (debug helper). Returns count."""
    if _cache is None:
        return 0
    n = 0
    for k in list(_cache.iterkeys()):
        n += 1
        _cache.delete(k)
    return n
