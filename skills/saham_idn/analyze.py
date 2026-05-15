"""Saham Indonesia (IDX) skill CLI.

Subcommands: price, ta, analyze, news, compare, watchlist, ihsg.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from . import feeds
from .._shared import chart as chart_mod
from .._shared import ta as ta_mod
from .._shared import llm_summary
from .._shared.output import (
    emit, emit_error,
    watchlist_add, watchlist_load, watchlist_remove,
)


SKILL = "saham_idn"


def cmd_price(args: argparse.Namespace) -> None:
    emit(feeds.quote(args.symbol))


def cmd_ihsg(args: argparse.Namespace) -> None:
    emit(feeds.ihsg())


def cmd_ta(args: argparse.Namespace) -> None:
    df = feeds.ohlcv(args.symbol, timeframe=args.tf)
    if df.empty:
        return emit_error("no OHLCV data", symbol=args.symbol, tf=args.tf)
    snap = ta_mod.snapshot(df, timeframe=args.tf)
    emit({"ok": True, "skill": SKILL, "symbol": feeds.normalize_ticker(args.symbol),
          "timeframe": args.tf, "ta": snap.to_dict()})


def cmd_analyze(args: argparse.Namespace) -> None:
    sym = feeds.normalize_ticker(args.symbol)
    q = feeds.quote(args.symbol)
    df = feeds.ohlcv(args.symbol, timeframe=args.tf)
    if df.empty:
        return emit_error("no OHLCV data", symbol=sym, tf=args.tf)
    snap = ta_mod.snapshot(df, timeframe=args.tf)
    chart_path: str | None = None
    if args.chart:
        try:
            chart_path = chart_mod.candlestick(
                df, title=f"{sym} {args.tf}",
                overlays=("EMA20", "EMA50", "EMA200"),
                show_bb=True, show_volume=True, last_n=120,
            )
        except Exception:
            chart_path = None
    news_out = feeds.news(args.symbol.replace(".JK", "").upper(), limit=5) if args.news else None
    ihsg_snap = feeds.ihsg() if args.ihsg else None

    payload: dict[str, Any] = {
        "ok": True, "skill": SKILL, "symbol": sym, "timeframe": args.tf,
        "fundamentals": {k: q.get(k) for k in (
            "name", "sector", "industry", "last", "previous_close", "change_pct",
            "year_low", "year_high", "market_cap", "pe_ratio", "forward_pe",
            "eps_trailing", "eps_forward", "dividend_yield", "book_value",
        )},
        "ihsg": ihsg_snap,
        "ta": snap.to_dict(),
        "news": news_out,
        "chart_path": chart_path,
    }
    if args.narrative:
        payload["narrative"] = llm_summary.summarize(payload)
    emit(payload)


def cmd_news(args: argparse.Namespace) -> None:
    emit(feeds.news(args.symbol, limit=args.limit))


def cmd_compare(args: argparse.Namespace) -> None:
    out: dict[str, Any] = {"ok": True, "skill": SKILL, "tf": args.tf, "items": {}}
    for sym in (args.a, args.b):
        q = feeds.quote(sym)
        df = feeds.ohlcv(sym, timeframe=args.tf)
        norm = feeds.normalize_ticker(sym)
        if df.empty:
            out["items"][norm] = {"ok": False, "error": "no data"}
            continue
        snap = ta_mod.snapshot(df, timeframe=args.tf)
        out["items"][norm] = {
            "last": q.get("last"),
            "change_pct": q.get("change_pct"),
            "pe_ratio": q.get("pe_ratio"),
            "dividend_yield": q.get("dividend_yield"),
            "rsi_14": snap.rsi_14,
            "trend_state": snap.trend_state,
        }
    emit(out)


def cmd_watchlist(args: argparse.Namespace) -> None:
    if args.action == "list":
        emit({"ok": True, "skill": SKILL, "items": watchlist_load(SKILL) or feeds.DEFAULT_WATCHLIST})
    elif args.action == "add":
        emit({"ok": True, "skill": SKILL, "items": watchlist_add(SKILL, args.symbol)})
    elif args.action == "rm":
        emit({"ok": True, "skill": SKILL, "items": watchlist_remove(SKILL, args.symbol)})
    else:
        emit_error(f"unknown watchlist action: {args.action}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skills.saham_idn.analyze",
                                description="Indonesian stock (IDX) market analysis")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("price"); sp.add_argument("symbol"); sp.set_defaults(fn=cmd_price)
    si = sub.add_parser("ihsg"); si.set_defaults(fn=cmd_ihsg)

    st = sub.add_parser("ta"); st.add_argument("symbol")
    st.add_argument("--tf", default="1d"); st.set_defaults(fn=cmd_ta)

    sa = sub.add_parser("analyze"); sa.add_argument("symbol")
    sa.add_argument("--tf", default="1d")
    sa.add_argument("--no-chart", dest="chart", action="store_false", default=True)
    sa.add_argument("--no-news", dest="news", action="store_false", default=True)
    sa.add_argument("--no-ihsg", dest="ihsg", action="store_false", default=True)
    sa.add_argument("--no-narrative", dest="narrative", action="store_false", default=True)
    sa.set_defaults(fn=cmd_analyze)

    sn = sub.add_parser("news"); sn.add_argument("symbol", nargs="?", default="")
    sn.add_argument("--limit", type=int, default=10); sn.set_defaults(fn=cmd_news)

    sc = sub.add_parser("compare"); sc.add_argument("a"); sc.add_argument("b")
    sc.add_argument("--tf", default="1d"); sc.set_defaults(fn=cmd_compare)

    sw = sub.add_parser("watchlist"); sw.add_argument("action", choices=["list", "add", "rm"])
    sw.add_argument("symbol", nargs="?", default=""); sw.set_defaults(fn=cmd_watchlist)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.fn(args)
        return 0
    except Exception as e:
        emit_error(f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
