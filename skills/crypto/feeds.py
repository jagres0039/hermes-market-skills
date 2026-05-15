"""Data feeds for the crypto skill.

Adapters:

* CoinGecko (REST, free public — generous rate limit, optional Demo API key for higher).
* Binance public REST via ccxt (no auth — OHLCV history for any spot pair).
* DeFiLlama (REST, no auth — TVL & protocol data).
* CryptoPanic (REST, free — news + sentiment).

All adapters are pure functions; no global state besides env-driven API keys.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .._shared.http_cache import cached_get

try:
    import ccxt  # type: ignore
except ImportError:  # pragma: no cover
    ccxt = None


COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_KEY = os.environ.get("COINGECKO_API_KEY", "")
DEFILLAMA_BASE = "https://api.llama.fi"
CRYPTOPANIC_BASE = "https://cryptopanic.com/api/v1"
CRYPTOPANIC_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "")


# ---------- symbol normalization ----------

_COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2",
    "DOT": "polkadot", "MATIC": "matic-network", "POL": "polygon-ecosystem-token",
    "LINK": "chainlink", "TRX": "tron", "LTC": "litecoin", "BCH": "bitcoin-cash",
    "ATOM": "cosmos", "NEAR": "near", "ARB": "arbitrum", "OP": "optimism",
    "SUI": "sui", "APT": "aptos", "TON": "the-open-network", "SHIB": "shiba-inu",
    "PEPE": "pepe", "WIF": "dogwifcoin", "BONK": "bonk", "FET": "fetch-ai",
    "RNDR": "render-token", "INJ": "injective-protocol", "TIA": "celestia",
    "USDT": "tether", "USDC": "usd-coin",
}


def to_coingecko_id(symbol: str) -> str:
    """Map a ticker like ``BTC`` to a CoinGecko ID. Unknown tickers fall back to
    the lower-cased ticker; CoinGecko also accepts IDs directly.
    """
    s = symbol.upper().replace("USDT", "").replace("USD", "").strip()
    return _COINGECKO_IDS.get(s, s.lower())


def to_ccxt_pair(symbol: str, quote: str = "USDT") -> str:
    """Map a ticker like ``BTC`` to a CCXT pair like ``BTC/USDT``."""
    s = symbol.upper()
    if "/" in s:
        return s
    s = s.replace("USDT", "").replace("USD", "")
    return f"{s}/{quote}"


# ---------- CoinGecko ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def cg_price(symbol: str) -> dict[str, Any]:
    """Return live price + 24h stats for a single coin."""
    cid = to_coingecko_id(symbol)
    params: dict[str, Any] = {
        "ids": cid,
        "vs_currencies": "usd,idr",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
    }
    headers = {"x-cg-demo-api-key": COINGECKO_KEY} if COINGECKO_KEY else {}
    r = cached_get(COINGECKO_BASE + "/simple/price", params=params, headers=headers, ttl=15)
    if r.status_code != 200:
        return {"ok": False, "error": f"coingecko HTTP {r.status_code}", "body": r.text[:200]}
    data = r.json()
    row = data.get(cid)
    if not row:
        return {"ok": False, "error": f"unknown coingecko id: {cid}"}
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "coingecko_id": cid,
        "price_usd": row.get("usd"),
        "price_idr": row.get("idr"),
        "market_cap_usd": row.get("usd_market_cap"),
        "volume_24h_usd": row.get("usd_24h_vol"),
        "change_24h_pct": row.get("usd_24h_change"),
        "last_updated_at": row.get("last_updated_at"),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def cg_market_data(symbol: str) -> dict[str, Any]:
    """Return richer market data (rank, ATH, supply, etc.)."""
    cid = to_coingecko_id(symbol)
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    }
    headers = {"x-cg-demo-api-key": COINGECKO_KEY} if COINGECKO_KEY else {}
    r = cached_get(COINGECKO_BASE + f"/coins/{cid}", params=params, headers=headers, ttl=120)
    if r.status_code != 200:
        return {"ok": False, "error": f"coingecko HTTP {r.status_code}"}
    j = r.json()
    md = j.get("market_data", {}) or {}
    return {
        "ok": True,
        "name": j.get("name"),
        "symbol": (j.get("symbol") or "").upper(),
        "rank": j.get("market_cap_rank"),
        "ath_usd": (md.get("ath") or {}).get("usd"),
        "ath_change_pct": (md.get("ath_change_percentage") or {}).get("usd"),
        "ath_date": (md.get("ath_date") or {}).get("usd"),
        "atl_usd": (md.get("atl") or {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
        "max_supply": md.get("max_supply"),
        "categories": j.get("categories"),
    }


# ---------- CCXT (Binance) ----------

_TF_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h",
    "1d": "1d", "1w": "1w",
}


def _binance() -> Any:
    if ccxt is None:
        raise RuntimeError(
            "ccxt is not installed. Run `pip install -r requirements.txt`."
        )
    return ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})


def ohlcv(symbol: str, timeframe: str = "1d", limit: int = 300) -> pd.DataFrame:
    """Return OHLCV DataFrame for ``symbol`` from Binance spot."""
    tf = _TF_MAP.get(timeframe, "1d")
    pair = to_ccxt_pair(symbol)
    ex = _binance()
    raw = ex.fetch_ohlcv(pair, timeframe=tf, limit=limit)
    if not raw:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop(columns=["ts"]).astype(float)
    return df


# ---------- DeFiLlama ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def defillama_tvl(protocol: str) -> dict[str, Any]:
    """Return current TVL for a protocol slug (e.g. ``uniswap``, ``aave-v3``)."""
    r = cached_get(f"{DEFILLAMA_BASE}/tvl/{protocol}", ttl=300)
    if r.status_code != 200:
        return {"ok": False, "error": f"defillama HTTP {r.status_code}"}
    try:
        return {"ok": True, "protocol": protocol, "tvl_usd": float(r.text)}
    except ValueError:
        return {"ok": False, "error": "non-numeric response", "body": r.text[:200]}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def defillama_chain_tvl(chain: str = "Ethereum") -> dict[str, Any]:
    """Current TVL for an entire chain."""
    r = cached_get(f"{DEFILLAMA_BASE}/v2/historicalChainTvl/{chain}", ttl=300)
    if r.status_code != 200:
        return {"ok": False, "error": f"defillama HTTP {r.status_code}"}
    arr = r.json()
    if not arr:
        return {"ok": False, "error": "empty"}
    return {"ok": True, "chain": chain, "tvl_usd": arr[-1]["tvl"], "ts": arr[-1]["date"]}


# ---------- CryptoPanic ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def cryptopanic_news(query: str = "", limit: int = 10) -> dict[str, Any]:
    """Return recent crypto news, optionally filtered by ticker/keyword."""
    if not CRYPTOPANIC_KEY:
        return {"ok": False, "error": "CRYPTOPANIC_API_KEY not set"}
    params: dict[str, Any] = {"auth_token": CRYPTOPANIC_KEY, "public": "true"}
    if query:
        params["currencies"] = query.upper()
    r = cached_get(f"{CRYPTOPANIC_BASE}/posts/", params=params, ttl=60)
    if r.status_code != 200:
        return {"ok": False, "error": f"cryptopanic HTTP {r.status_code}"}
    j = r.json()
    items: list[dict[str, Any]] = []
    for p in (j.get("results") or [])[:limit]:
        items.append({
            "title": p.get("title"),
            "url": p.get("url"),
            "domain": (p.get("source") or {}).get("domain"),
            "published": p.get("published_at"),
            "votes": p.get("votes"),
            "currencies": [c.get("code") for c in (p.get("currencies") or [])],
        })
    return {"ok": True, "count": len(items), "items": items}


# ---------- Fear & Greed ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fear_greed() -> dict[str, Any]:
    """Alternative.me's Fear & Greed Index (free, no auth)."""
    r = cached_get("https://api.alternative.me/fng/?limit=1", ttl=600)
    if r.status_code != 200:
        return {"ok": False, "error": f"alt.me HTTP {r.status_code}"}
    j = r.json()
    if not j.get("data"):
        return {"ok": False, "error": "empty"}
    d = j["data"][0]
    return {
        "ok": True,
        "value": int(d["value"]),
        "classification": d["value_classification"],
        "timestamp": d["timestamp"],
    }
