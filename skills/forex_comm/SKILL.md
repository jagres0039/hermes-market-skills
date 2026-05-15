---
name: market-forex-comm
version: 0.1.0
description: |
  On-demand analysis for major forex pairs (EURUSD, USDJPY, GBPUSD, ...) and
  commodities (gold, silver, oil WTI/Brent, natural gas, copper). Includes live
  spot/futures price, technical indicators, chart PNG, today's high-impact
  economic events (ForexFactory), and a narrative summary in Bahasa Indonesia.
triggers:
  - forex
  - fx
  - eurusd
  - gbpusd
  - usdjpy
  - audusd
  - usdchf
  - usdcad
  - nzdusd
  - gold
  - emas
  - xau
  - silver
  - perak
  - xag
  - oil
  - minyak
  - wti
  - brent
  - gas
  - natgas
  - copper
  - tembaga
  - komoditas
language: python
entrypoint: python3 -m skills.forex_comm.analyze
---

# Forex + Commodities skill

## Commands

| Command | Example | What it returns |
| --- | --- | --- |
| `price <sym>` | `price EURUSD` / `price GOLD` | spot quote (TwelveData → yfinance fallback) |
| `ta <sym> [--tf 1d]` | `ta XAUUSD --tf 4h` | RSI, MACD, BB, EMA, ATR, pivot |
| `analyze <sym> [--tf]` | `analyze USDJPY --tf 1d` | full report + chart + calendar + narrative |
| `calendar [--impact]` | `calendar --impact high` | today's ForexFactory events |
| `compare <a> <b>` | `compare GOLD SILVER` | side-by-side TA |
| `watchlist add/rm/list` | `watchlist add EURUSD` | manage watchlist (default: 7 majors + 6 commodities) |

## Symbols

**Forex** — 6-letter pair without slash (`EURUSD`, `USDJPY`, `GBPUSD`). Slash optional (`EUR/USD`).

**Commodities** (aliases auto-resolved to futures ticker):

| Alias | yfinance ticker | What |
| --- | --- | --- |
| `GOLD`, `XAU`, `XAUUSD` | `GC=F` | Gold futures |
| `SILVER`, `XAG`, `XAGUSD` | `SI=F` | Silver futures |
| `OIL`, `WTI` | `CL=F` | Crude oil WTI |
| `BRENT` | `BZ=F` | Crude oil Brent |
| `GAS`, `NATGAS` | `NG=F` | Natural gas |
| `COPPER` | `HG=F` | Copper |
| `PLATINUM` | `PL=F` | Platinum |
| `PALLADIUM` | `PA=F` | Palladium |

Default watchlist: 7 major forex pairs + 6 commodities (gold, silver, oil, brent, natgas, copper).

## Data sources

- **TwelveData** — primary for forex spot + OHLCV. Free tier 800 calls/day, 8/min. Set `TWELVEDATA_API_KEY`.
- **yfinance** — primary for commodities, fallback for forex when TwelveData unavailable. Anonymous.
- **ForexFactory** — economic calendar scrape (high/medium/low impact events). Anonymous.

## Hermes autonomy

Read-only. No order placement. Safe to run without confirmation.

## Caveats

- TwelveData free tier rate-limits aggressively (8 calls/min). The skill caches responses for 60s.
- For forex, when TwelveData key is missing, yfinance fallback uses `<PAIR>=X` which has 15-min delay.
- 4h timeframe is resampled from 1h on the yfinance path.
- ForexFactory occasionally changes its HTML; selectors may need updates if calendar scrape fails.
