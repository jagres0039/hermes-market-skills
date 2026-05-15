"""Technical analysis helpers.

Thin wrappers around ``pandas-ta`` that return a single :class:`TASnapshot`
object per call, so callers don't have to remember individual function signatures
or worry about NaN handling.

All functions accept a DataFrame with at least the columns
``open, high, low, close, volume`` indexed by timestamp (UTC, ascending).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np
import pandas as pd

try:
    import pandas_ta as pta  # type: ignore
except ImportError:  # pragma: no cover
    pta = None


OHLCV_COLS = ("open", "high", "low", "close", "volume")


def _require_pta() -> None:
    if pta is None:
        raise RuntimeError(
            "pandas-ta is not installed. Run `pip install -r requirements.txt`."
        )


def _validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in OHLCV_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


@dataclass
class TASnapshot:
    """A single-point snapshot of all computed indicators at the latest bar."""

    timeframe: str
    last_close: float
    last_bar_time: str

    # momentum
    rsi_14: float | None = None
    rsi_state: str | None = None  # oversold / neutral / overbought
    stoch_k: float | None = None
    stoch_d: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    macd_state: str | None = None  # bullish-cross / bearish-cross / above-zero / below-zero

    # trend
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    trend_state: str | None = None  # uptrend / downtrend / sideways

    # volatility
    bb_upper: float | None = None
    bb_mid: float | None = None
    bb_lower: float | None = None
    bb_pct: float | None = None  # 0 = at lower, 1 = at upper
    atr_14: float | None = None

    # support / resistance heuristics
    pivot: float | None = None
    r1: float | None = None
    r2: float | None = None
    s1: float | None = None
    s2: float | None = None

    # volume
    volume_ma_20: float | None = None
    volume_z: float | None = None  # z-score vs last 20 bars

    # raw series (compact) — last 60 bars for chart rendering
    series_close: list[float] = field(default_factory=list)
    series_time: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _classify_rsi(v: float) -> str:
    if v < 30:
        return "oversold"
    if v > 70:
        return "overbought"
    if v < 40:
        return "weak"
    if v > 60:
        return "strong"
    return "neutral"


def _classify_trend(close: float, ema50: float | None, ema200: float | None) -> str:
    if ema50 is None or ema200 is None or np.isnan(ema50) or np.isnan(ema200):
        return "unknown"
    if close > ema50 > ema200:
        return "uptrend-strong"
    if close > ema50 and ema50 < ema200:
        return "uptrend-weak"
    if close < ema50 < ema200:
        return "downtrend-strong"
    if close < ema50 and ema50 > ema200:
        return "downtrend-weak"
    return "sideways"


def _classify_macd(macd: float | None, sig: float | None, hist: float | None,
                   prev_hist: float | None) -> str:
    if macd is None or sig is None or hist is None:
        return "unknown"
    states: list[str] = []
    if prev_hist is not None:
        if prev_hist < 0 < hist:
            states.append("bullish-cross")
        elif prev_hist > 0 > hist:
            states.append("bearish-cross")
    states.append("above-zero" if macd > 0 else "below-zero")
    return "+".join(states)


def _f(v: Any) -> float | None:
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except Exception:
        return None


def _col_by_prefix(df: pd.DataFrame | None, prefix: str) -> str | None:
    """Find a column whose name starts with ``prefix``. Returns the first match."""
    if df is None:
        return None
    for c in df.columns:
        if c.startswith(prefix):
            return c
    return None


def snapshot(df: pd.DataFrame, *, timeframe: str = "1d", series_n: int = 60) -> TASnapshot:
    """Compute a full TA snapshot at the latest bar."""
    _require_pta()
    df = _validate(df)
    if len(df) < 30:
        # too short — return bare minimum
        return TASnapshot(
            timeframe=timeframe,
            last_close=_f(df["close"].iloc[-1]) or 0.0,
            last_bar_time=df.index[-1].isoformat(),
            series_close=[_f(v) or 0.0 for v in df["close"].tail(series_n).tolist()],
            series_time=[t.isoformat() for t in df.index[-series_n:].tolist()],
        )

    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]

    # momentum
    rsi = pta.rsi(close, length=14)
    stoch = pta.stoch(high, low, close, k=14, d=3, smooth_k=3)
    macd_df = pta.macd(close, fast=12, slow=26, signal=9)

    # trend
    ema20 = pta.ema(close, length=20)
    ema50 = pta.ema(close, length=50)
    ema200 = pta.ema(close, length=200)
    sma20 = pta.sma(close, length=20)
    sma50 = pta.sma(close, length=50)
    sma200 = pta.sma(close, length=200)

    # volatility
    bb = pta.bbands(close, length=20, std=2)
    atr = pta.atr(high, low, close, length=14)

    # classic pivot points from last completed bar
    p_high, p_low, p_close = high.iloc[-2], low.iloc[-2], close.iloc[-2]
    pivot = (p_high + p_low + p_close) / 3
    r1 = 2 * pivot - p_low
    s1 = 2 * pivot - p_high
    r2 = pivot + (p_high - p_low)
    s2 = pivot - (p_high - p_low)

    # volume
    vol_ma = pta.sma(vol, length=20)
    vol_std = vol.rolling(20).std()
    last_vol = vol.iloc[-1]
    last_vol_ma = vol_ma.iloc[-1] if vol_ma is not None else np.nan
    last_vol_std = vol_std.iloc[-1] if vol_std is not None else np.nan
    vol_z = (
        (last_vol - last_vol_ma) / last_vol_std
        if pd.notna(last_vol_ma) and pd.notna(last_vol_std) and last_vol_std != 0
        else None
    )

    last_close = float(close.iloc[-1])
    rsi_v = _f(rsi.iloc[-1]) if rsi is not None else None
    # MACD/BB column names vary between pandas-ta versions (e.g. BBU_20_2.0 vs BBU_20_2.0_2.0).
    macd_col = _col_by_prefix(macd_df, "MACD_")
    macds_col = _col_by_prefix(macd_df, "MACDs_")
    macdh_col = _col_by_prefix(macd_df, "MACDh_")
    bbu_col = _col_by_prefix(bb, "BBU_")
    bbm_col = _col_by_prefix(bb, "BBM_")
    bbl_col = _col_by_prefix(bb, "BBL_")
    stoch_k_col = _col_by_prefix(stoch, "STOCHk_")
    stoch_d_col = _col_by_prefix(stoch, "STOCHd_")

    macd_v = _f(macd_df[macd_col].iloc[-1]) if macd_col else None
    sig_v = _f(macd_df[macds_col].iloc[-1]) if macds_col else None
    hist_v = _f(macd_df[macdh_col].iloc[-1]) if macdh_col else None
    prev_hist_v = (
        _f(macd_df[macdh_col].iloc[-2]) if macdh_col and len(macd_df) > 1 else None
    )
    bb_u = _f(bb[bbu_col].iloc[-1]) if bbu_col else None
    bb_m = _f(bb[bbm_col].iloc[-1]) if bbm_col else None
    bb_l = _f(bb[bbl_col].iloc[-1]) if bbl_col else None
    bb_pct = None
    if bb_u and bb_l and bb_u != bb_l:
        bb_pct = (last_close - bb_l) / (bb_u - bb_l)

    snap = TASnapshot(
        timeframe=timeframe,
        last_close=last_close,
        last_bar_time=df.index[-1].isoformat(),
        rsi_14=rsi_v,
        rsi_state=_classify_rsi(rsi_v) if rsi_v is not None else None,
        stoch_k=_f(stoch[stoch_k_col].iloc[-1]) if stoch_k_col else None,
        stoch_d=_f(stoch[stoch_d_col].iloc[-1]) if stoch_d_col else None,
        macd=macd_v,
        macd_signal=sig_v,
        macd_hist=hist_v,
        macd_state=_classify_macd(macd_v, sig_v, hist_v, prev_hist_v),
        ema_20=_f(ema20.iloc[-1]) if ema20 is not None else None,
        ema_50=_f(ema50.iloc[-1]) if ema50 is not None else None,
        ema_200=_f(ema200.iloc[-1]) if ema200 is not None else None,
        sma_20=_f(sma20.iloc[-1]) if sma20 is not None else None,
        sma_50=_f(sma50.iloc[-1]) if sma50 is not None else None,
        sma_200=_f(sma200.iloc[-1]) if sma200 is not None else None,
        trend_state=_classify_trend(
            last_close,
            _f(ema50.iloc[-1]) if ema50 is not None else None,
            _f(ema200.iloc[-1]) if ema200 is not None else None,
        ),
        bb_upper=bb_u,
        bb_mid=bb_m,
        bb_lower=bb_l,
        bb_pct=bb_pct,
        atr_14=_f(atr.iloc[-1]) if atr is not None else None,
        pivot=_f(pivot),
        r1=_f(r1),
        r2=_f(r2),
        s1=_f(s1),
        s2=_f(s2),
        volume_ma_20=_f(last_vol_ma),
        volume_z=_f(vol_z) if vol_z is not None else None,
        series_close=[_f(v) or 0.0 for v in close.tail(series_n).tolist()],
        series_time=[t.isoformat() for t in df.index[-series_n:].tolist()],
    )
    return snap


def fibonacci_levels(high: float, low: float) -> dict[str, float]:
    """Return classic Fibonacci retracement levels between a swing high & low."""
    diff = high - low
    return {
        "0.0": low,
        "0.236": low + diff * 0.236,
        "0.382": low + diff * 0.382,
        "0.5": low + diff * 0.5,
        "0.618": low + diff * 0.618,
        "0.786": low + diff * 0.786,
        "1.0": high,
    }
