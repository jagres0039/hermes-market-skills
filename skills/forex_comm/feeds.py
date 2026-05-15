"""Data feeds for the forex + commodities skill.

Adapters:

* TwelveData — primary forex OHLCV + spot (requires free API key, 800/day).
* yfinance — commodity futures (`GC=F`, `CL=F`, ...), fallback for forex (`EURUSD=X`).
* ForexFactory scrape — economic calendar (high-impact events).
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .._shared.http_cache import cached_get

try:
    import yfinance as yf  # type: ignore
except ImportError:  # pragma: no cover
    yf = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover
    BeautifulSoup = None


TWELVEDATA_BASE = "https://api.twelvedata.com"
TWELVEDATA_KEY = os.environ.get("TWELVEDATA_API_KEY", "")


# ---------- symbol routing ----------

_COMMODITY_YF = {
    "GOLD": "GC=F", "XAU": "GC=F", "XAUUSD": "GC=F",
    "SILVER": "SI=F", "XAG": "SI=F", "XAGUSD": "SI=F",
    "OIL": "CL=F", "WTI": "CL=F",
    "BRENT": "BZ=F",
    "GAS": "NG=F", "NATGAS": "NG=F",
    "COPPER": "HG=F",
    "PLATINUM": "PL=F", "PALLADIUM": "PA=F",
}

_FOREX_RE = re.compile(r"^([A-Z]{3})/?([A-Z]{3})$")


def asset_kind(symbol: str) -> str:
    s = symbol.upper().replace("/", "")
    if s in _COMMODITY_YF:
        return "commodity"
    if _FOREX_RE.match(s):
        return "forex"
    return "unknown"


def to_yf_ticker(symbol: str) -> str:
    """Resolve a user-facing symbol to a yfinance ticker.

    - ``GOLD`` / ``XAU`` / ``XAUUSD`` -> ``GC=F``
    - ``OIL`` -> ``CL=F``
    - forex ``EURUSD`` / ``EUR/USD`` -> ``EURUSD=X``
    - anything else passes through.
    """
    s = symbol.upper().replace("/", "")
    if s in _COMMODITY_YF:
        return _COMMODITY_YF[s]
    m = _FOREX_RE.match(s)
    if m:
        return f"{m.group(1)}{m.group(2)}=X"
    return s


def to_twelvedata_symbol(symbol: str) -> str:
    """Resolve a user-facing symbol to a TwelveData symbol.

    - ``EURUSD`` -> ``EUR/USD``
    - ``XAUUSD`` / ``GOLD`` -> ``XAU/USD``
    """
    s = symbol.upper().replace("/", "")
    if s in ("GOLD", "XAU", "XAUUSD"):
        return "XAU/USD"
    if s in ("SILVER", "XAG", "XAGUSD"):
        return "XAG/USD"
    m = _FOREX_RE.match(s)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return symbol


# ---------- TwelveData ----------

_TF_TD = {
    "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "4h": "4h",
    "1d": "1day", "1w": "1week",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def td_quote(symbol: str) -> dict[str, Any]:
    """TwelveData ``/quote`` endpoint (forex / commodity spot)."""
    if not TWELVEDATA_KEY:
        return {"ok": False, "error": "TWELVEDATA_API_KEY not set"}
    s = to_twelvedata_symbol(symbol)
    params = {"symbol": s, "apikey": TWELVEDATA_KEY}
    r = cached_get(f"{TWELVEDATA_BASE}/quote", params=params, ttl=15)
    if r.status_code != 200:
        return {"ok": False, "error": f"twelvedata HTTP {r.status_code}", "body": r.text[:200]}
    j = r.json()
    if j.get("code") and j.get("code") != 200:
        return {"ok": False, "error": j.get("message"), "code": j.get("code")}
    return {
        "ok": True,
        "symbol": s,
        "name": j.get("name"),
        "last": float(j["close"]) if j.get("close") else None,
        "open": float(j["open"]) if j.get("open") else None,
        "high": float(j["high"]) if j.get("high") else None,
        "low": float(j["low"]) if j.get("low") else None,
        "previous_close": float(j["previous_close"]) if j.get("previous_close") else None,
        "change": float(j["change"]) if j.get("change") else None,
        "change_pct": float(j["percent_change"]) if j.get("percent_change") else None,
        "currency_base": j.get("currency_base"),
        "currency_quote": j.get("currency_quote"),
        "exchange": j.get("exchange"),
        "timestamp": j.get("timestamp"),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def td_time_series(symbol: str, *, timeframe: str = "1d", outputsize: int = 300) -> pd.DataFrame:
    """TwelveData ``/time_series`` -> OHLCV DataFrame."""
    if not TWELVEDATA_KEY:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    s = to_twelvedata_symbol(symbol)
    interval = _TF_TD.get(timeframe, "1day")
    params = {"symbol": s, "interval": interval, "outputsize": outputsize,
              "apikey": TWELVEDATA_KEY, "format": "JSON"}
    r = cached_get(f"{TWELVEDATA_BASE}/time_series", params=params, ttl=60)
    if r.status_code != 200:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    j = r.json()
    if j.get("status") == "error" or not j.get("values"):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    rows = j["values"]
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["datetime"], utc=True)
    df = df.drop(columns=["datetime"]).rename(columns={
        "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume",
    })
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(float).fillna(0.0)
    else:
        df["volume"] = 0.0
    df = df.sort_index()
    return df[["open", "high", "low", "close", "volume"]]


# ---------- yfinance fallback / commodities ----------

_TF_YF = {
    "5m": ("5m", "5d"),
    "15m": ("15m", "5d"),
    "30m": ("30m", "60d"),
    "1h": ("60m", "730d"),
    "4h": ("60m", "730d"),
    "1d": ("1d", "2y"),
    "1w": ("1wk", "10y"),
}


def _require_yf() -> None:
    if yf is None:
        raise RuntimeError(
            "yfinance is not installed. Run `pip install -r requirements.txt`."
        )


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def yf_ohlcv(symbol: str, *, timeframe: str = "1d") -> pd.DataFrame:
    _require_yf()
    t = to_yf_ticker(symbol)
    interval, period = _TF_YF.get(timeframe, ("1d", "2y"))
    df = yf.download(t, interval=interval, period=period, auto_adjust=False,
                     progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                            "Close": "close", "Volume": "volume"})
    df.index = pd.to_datetime(df.index, utc=True)
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].astype(float)
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
    return df


def _fi(obj: Any, *names: str) -> Any:
    """Read a value from yfinance FastInfo trying snake_case attrs then camelCase keys."""
    for n in names:
        try:
            v = getattr(obj, n, None)
            if v is not None:
                return v
        except Exception:
            pass
    for n in names:
        try:
            v = obj.get(n) if hasattr(obj, "get") else None
            if v is not None:
                return v
        except Exception:
            pass
    return None


def yf_quote(symbol: str) -> dict[str, Any]:
    _require_yf()
    t = to_yf_ticker(symbol)
    tk = yf.Ticker(t)
    fast = tk.fast_info
    last = _fi(fast, "last_price", "lastPrice", "regular_market_price", "regularMarketPrice")
    prev = _fi(fast, "previous_close", "previousClose", "regularMarketPreviousClose")
    # Fallback: pull last bar from a recent OHLCV history if fast_info empty.
    if last is None or prev is None:
        try:
            hist = yf.download(t, period="5d", interval="1d", auto_adjust=False,
                               progress=False, threads=False)
            if hist is not None and not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = [c[0] for c in hist.columns]
                if last is None:
                    last = float(hist["Close"].iloc[-1])
                if prev is None and len(hist) > 1:
                    prev = float(hist["Close"].iloc[-2])
        except Exception:
            pass
    change_pct = None
    if last is not None and prev:
        change_pct = (float(last) - float(prev)) / float(prev) * 100
    return {
        "ok": True,
        "symbol": t,
        "last": float(last) if last is not None else None,
        "previous_close": float(prev) if prev else None,
        "change_pct": change_pct,
        "day_low": _fi(fast, "day_low", "dayLow"),
        "day_high": _fi(fast, "day_high", "dayHigh"),
        "year_low": _fi(fast, "year_low", "yearLow", "fiftyTwoWeekLow"),
        "year_high": _fi(fast, "year_high", "yearHigh", "fiftyTwoWeekHigh"),
        "currency": _fi(fast, "currency"),
    }


# ---------- combined router ----------

def quote(symbol: str) -> dict[str, Any]:
    """Get the best available quote: TwelveData if forex+key present, else yfinance."""
    kind = asset_kind(symbol)
    if kind == "forex" and TWELVEDATA_KEY:
        q = td_quote(symbol)
        if q.get("ok"):
            q["kind"] = "forex"
            return q
    # commodity, or forex without td key
    q = yf_quote(symbol)
    q["kind"] = kind
    return q


def ohlcv(symbol: str, *, timeframe: str = "1d") -> pd.DataFrame:
    """OHLCV with same routing as :func:`quote`."""
    kind = asset_kind(symbol)
    if kind == "forex" and TWELVEDATA_KEY:
        df = td_time_series(symbol, timeframe=timeframe)
        if not df.empty:
            return df
    return yf_ohlcv(symbol, timeframe=timeframe)


# ---------- ForexFactory economic calendar ----------

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def calendar_today(min_impact: str = "high") -> dict[str, Any]:
    """Scrape today's ForexFactory calendar for high-impact events.

    ``min_impact`` is one of ``low``, ``medium``, ``high``. Higher impact only.
    """
    if BeautifulSoup is None:
        return {"ok": False, "error": "beautifulsoup4 not installed"}
    headers = {"User-Agent": "Mozilla/5.0 (Hermes Market Skills)"}
    r = cached_get("https://www.forexfactory.com/calendar?day=today",
                   headers=headers, ttl=600)
    if r.status_code != 200:
        return {"ok": False, "error": f"forexfactory HTTP {r.status_code}"}
    soup = BeautifulSoup(r.content, "lxml")
    rows = soup.select("tr.calendar__row")
    impact_rank = {"low": 0, "medium": 1, "high": 2, "holiday": -1}
    threshold = impact_rank.get(min_impact, 2)
    out: list[dict[str, Any]] = []
    for tr in rows:
        impact_el = tr.select_one(".calendar__impact span")
        impact = ""
        if impact_el and impact_el.has_attr("title"):
            impact = impact_el["title"].lower().split()[0]
        if impact_rank.get(impact, -1) < threshold:
            continue
        currency = (tr.select_one(".calendar__currency") or {}).get_text(strip=True) if tr.select_one(".calendar__currency") else ""
        event = (tr.select_one(".calendar__event") or {}).get_text(strip=True) if tr.select_one(".calendar__event") else ""
        time_ = (tr.select_one(".calendar__time") or {}).get_text(strip=True) if tr.select_one(".calendar__time") else ""
        actual = (tr.select_one(".calendar__actual") or {}).get_text(strip=True) if tr.select_one(".calendar__actual") else ""
        forecast = (tr.select_one(".calendar__forecast") or {}).get_text(strip=True) if tr.select_one(".calendar__forecast") else ""
        previous = (tr.select_one(".calendar__previous") or {}).get_text(strip=True) if tr.select_one(".calendar__previous") else ""
        out.append({"time": time_, "currency": currency, "impact": impact, "event": event,
                    "actual": actual, "forecast": forecast, "previous": previous})
    return {"ok": True, "date": datetime.utcnow().date().isoformat(),
            "min_impact": min_impact, "count": len(out), "items": out}


# Defaults
DEFAULT_FOREX_WATCHLIST = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD"]
DEFAULT_COMMODITY_WATCHLIST = ["GOLD", "SILVER", "OIL", "BRENT", "NATGAS", "COPPER"]
