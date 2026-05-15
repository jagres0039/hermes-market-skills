"""Chart rendering helper.

Renders a candlestick chart with optional overlay (EMAs, Bollinger Bands) and a
volume sub-panel. Output is PNG suitable for posting to Telegram.

Designed to be cheap: matplotlib + mplfinance, no GUI backend.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")  # no GUI

import pandas as pd  # noqa: E402

try:
    import mplfinance as mpf  # type: ignore
except ImportError:  # pragma: no cover
    mpf = None


DEFAULT_OUT_DIR = Path(os.environ.get("HERMES_CHART_OUT", "/tmp/hermes-charts"))


def _ensure_out_dir() -> Path:
    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUT_DIR


def candlestick(
    df: pd.DataFrame,
    *,
    title: str,
    out_path: str | None = None,
    overlays: Iterable[str] = ("EMA20", "EMA50"),
    show_bb: bool = True,
    show_volume: bool = True,
    last_n: int = 120,
) -> str:
    """Render a candlestick PNG and return the absolute path.

    ``df`` must have columns open/high/low/close/volume indexed by DatetimeIndex.
    """
    if mpf is None:
        raise RuntimeError(
            "mplfinance is not installed. Run `pip install -r requirements.txt`."
        )

    df = df.tail(last_n).copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "Date"

    rename = {c: c.capitalize() for c in ("open", "high", "low", "close", "volume")}
    df = df.rename(columns=rename)

    addplots: list = []
    if "EMA20" in overlays and len(df) >= 20:
        addplots.append(mpf.make_addplot(df["Close"].ewm(span=20).mean(), color="#3D85C6", width=0.9))
    if "EMA50" in overlays and len(df) >= 50:
        addplots.append(mpf.make_addplot(df["Close"].ewm(span=50).mean(), color="#FFA500", width=0.9))
    if "EMA200" in overlays and len(df) >= 200:
        addplots.append(mpf.make_addplot(df["Close"].ewm(span=200).mean(), color="#FF0000", width=0.9))

    if show_bb and len(df) >= 20:
        mid = df["Close"].rolling(20).mean()
        std = df["Close"].rolling(20).std()
        addplots.append(mpf.make_addplot(mid + 2 * std, color="#888", width=0.5, linestyle="--"))
        addplots.append(mpf.make_addplot(mid - 2 * std, color="#888", width=0.5, linestyle="--"))

    out_dir = _ensure_out_dir()
    if out_path is None:
        safe = "".join(c if c.isalnum() else "_" for c in title.lower())[:60]
        out_path = str(out_dir / f"{safe}_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%S')}.png")

    mpf.plot(
        df,
        type="candle",
        style="charles",
        title=title,
        ylabel="Price",
        volume=show_volume,
        addplot=addplots if addplots else None,
        figratio=(16, 9),
        figscale=1.0,
        tight_layout=True,
        savefig=dict(fname=out_path, dpi=120, bbox_inches="tight"),
    )
    return out_path
