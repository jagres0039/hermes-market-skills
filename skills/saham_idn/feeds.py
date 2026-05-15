"""Data feeds for the Indonesian-stock skill.

Adapters:

* yfinance — OHLCV + fundamentals for `<ticker>.JK` (e.g. `BBRI.JK`).
* IDX (idx.co.id) — composite (IHSG `^JKSE`) and very limited scrape fallback.
* RSS — news headlines from Bisnis Indonesia + Kontan.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import yfinance as yf  # type: ignore
except ImportError:  # pragma: no cover
    yf = None

try:
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover
    feedparser = None


def _require_yf() -> None:
    if yf is None:
        raise RuntimeError(
            "yfinance is not installed. Run `pip install -r requirements.txt`."
        )


def normalize_ticker(symbol: str) -> str:
    """Map a bare ticker like ``BBRI`` to the yfinance form ``BBRI.JK``.

    Already-suffixed inputs (``BBRI.JK``, ``^JKSE``) pass through.
    """
    s = symbol.upper().strip()
    if s.startswith("^") or s.endswith(".JK"):
        return s
    return f"{s}.JK"


_TF_MAP = {
    "5m": ("5m", "5d"),
    "15m": ("15m", "5d"),
    "30m": ("30m", "60d"),
    "1h": ("60m", "730d"),
    "4h": ("60m", "730d"),  # yfinance has no 4h; caller can resample
    "1d": ("1d", "2y"),
    "1w": ("1wk", "10y"),
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def ohlcv(symbol: str, *, timeframe: str = "1d") -> pd.DataFrame:
    """Return OHLCV DataFrame for ``symbol`` via yfinance."""
    _require_yf()
    t = normalize_ticker(symbol)
    interval, period = _TF_MAP.get(timeframe, ("1d", "2y"))
    df = yf.download(
        t, interval=interval, period=period, auto_adjust=False, progress=False, threads=False,
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    # yfinance returns MultiIndex columns when single ticker too in newer versions; flatten
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
    })
    df.index = pd.to_datetime(df.index, utc=True)
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].astype(float)
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
    return df


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def quote(symbol: str) -> dict[str, Any]:
    """Return a snapshot (last price, day range, mcap, PER, dividend yield)."""
    _require_yf()
    t = normalize_ticker(symbol)
    tk = yf.Ticker(t)
    fast = tk.fast_info or {}
    info: dict[str, Any] = {}
    try:
        info = tk.info or {}
    except Exception:
        info = {}

    last = fast.get("last_price") or info.get("regularMarketPrice")
    prev = fast.get("previous_close") or info.get("regularMarketPreviousClose")
    change_pct = None
    if last is not None and prev:
        change_pct = (float(last) - float(prev)) / float(prev) * 100

    return {
        "ok": True,
        "symbol": t,
        "name": info.get("shortName") or info.get("longName"),
        "currency": fast.get("currency") or info.get("currency") or "IDR",
        "last": float(last) if last is not None else None,
        "previous_close": float(prev) if prev else None,
        "change_pct": change_pct,
        "day_low": fast.get("day_low"),
        "day_high": fast.get("day_high"),
        "year_low": info.get("fiftyTwoWeekLow"),
        "year_high": info.get("fiftyTwoWeekHigh"),
        "market_cap": info.get("marketCap"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps_trailing": info.get("trailingEps"),
        "eps_forward": info.get("forwardEps"),
        "dividend_yield": info.get("dividendYield"),
        "book_value": info.get("bookValue"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": info.get("exchange"),
    }


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def ihsg() -> dict[str, Any]:
    """IHSG (Indonesia Composite) snapshot via ``^JKSE``."""
    return quote("^JKSE")


# ---------- News RSS ----------

_NEWS_FEEDS = [
    "https://www.bisnis.com/rss/market",
    "https://investasi.kontan.co.id/rss",
    "https://www.idnfinancials.com/feed",
]


def news(query: str = "", limit: int = 10) -> dict[str, Any]:
    """Aggregate market news from public RSS, optionally filtered by keyword."""
    if feedparser is None:
        return {"ok": False, "error": "feedparser not installed"}
    items: list[dict[str, Any]] = []
    q = query.lower().strip()
    for url in _NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:30]:
            title = (e.get("title") or "").strip()
            if q and q not in title.lower():
                continue
            items.append({
                "title": title,
                "url": e.get("link"),
                "published": e.get("published") or e.get("updated"),
                "source": feed.feed.get("title"),
            })
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    return {"ok": True, "count": min(len(items), limit), "items": items[:limit]}


# Curated default watchlist — top 10 most-liquid IDX stocks (LQ45 core)
DEFAULT_WATCHLIST = [
    "BBRI", "BBCA", "BMRI", "BBNI",  # bank
    "TLKM", "TPIA",                  # telco/petchem
    "ASII",                          # automotive
    "UNVR", "INDF", "ICBP",          # consumer
]
