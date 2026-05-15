---
name: market-saham-idn
version: 0.1.0
description: |
  On-demand analysis for Indonesian-listed stocks (IDX / BEI). Covers price,
  fundamentals (PER, EPS, dividend yield, sector), technical indicators, chart
  PNG, market news from local RSS, IHSG composite snapshot, and a narrative
  summary in Bahasa Indonesia.
triggers:
  - saham
  - ihsg
  - idx
  - bei
  - bursa
  - lq45
  - bbri
  - bbca
  - bmri
  - bbni
  - tlkm
  - asii
  - unvr
  - indf
  - icbp
  - tpia
  - ".jk"
language: python
entrypoint: python3 -m skills.saham_idn.analyze
---

# Saham IDN skill

## Commands

| Command | Example | What it returns |
| --- | --- | --- |
| `price <ticker>` | `price BBRI` | last, prev close, range, mcap, PER, EPS, dividend |
| `ihsg` | `ihsg` | snapshot of the IHSG composite (`^JKSE`) |
| `ta <ticker> [--tf 1d]` | `ta BBCA --tf 4h` | RSI, MACD, BB, EMA, ATR, pivot |
| `analyze <ticker> [--tf]` | `analyze TLKM --tf 1d` | full report + chart + news + IHSG + narrative |
| `news [keyword]` | `news bank` | RSS news matching keyword |
| `compare <a> <b>` | `compare BBRI BBCA` | side-by-side fundamentals + TA |
| `watchlist add/rm/list` | `watchlist add ASII` | manage watchlist (default: LQ45 core) |

## Tickers

Use the 4-letter IDX code (`BBRI`, `BBCA`, `TLKM`). The skill auto-appends `.JK` for yfinance. Composite index: `^JKSE`.

Default curated watchlist: `BBRI BBCA BMRI BBNI TLKM TPIA ASII UNVR INDF ICBP`.

## Data sources

- **yfinance** — `<ticker>.JK` OHLCV + Ticker.info fundamentals. Anonymous, free, no auth.
- **RSS** — Bisnis.com, Kontan, IDN Financials. No auth.

## Hermes autonomy

Read-only. No order placement, no broker integration. Safe to run without confirmation.

## Caveats

- yfinance fundamentals for IDX tickers can be sparse; missing fields are returned as `null`.
- IDX intraday data has a 15-min delay on the free Yahoo feed.
- Some 6-letter IDX codes (mis. `ARTO.JK`) also work.
- 4h timeframe is resampled from 1h (yfinance doesn't expose 4h natively).
