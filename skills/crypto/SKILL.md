---
name: market-crypto
version: 0.1.0
description: |
  On-demand cryptocurrency analysis (BTC, ETH, top alts). Provides live price,
  technical indicators (RSI/MACD/BB/EMA/Ichimoku/Fib), chart PNG, news with
  sentiment, Fear & Greed index, and a narrative summary in Bahasa Indonesia.
triggers:
  - crypto
  - bitcoin
  - btc
  - ethereum
  - eth
  - solana
  - sol
  - coin
  - token
  - altcoin
  - defi
  - "fear and greed"
  - "fng"
language: python
entrypoint: python3 -m skills.crypto.analyze
---

# Crypto skill

## Commands

| Command | Example | What it returns |
| --- | --- | --- |
| `price <symbol>` | `price BTC` | live USD/IDR, mcap, 24h vol, 24h change |
| `ta <symbol> [--tf 1d]` | `ta ETH --tf 4h` | RSI, MACD, BB, EMA20/50/200, ATR, pivot |
| `analyze <symbol> [--tf]` | `analyze SOL --tf 1d` | full report + chart PNG + news + F&G + narrative |
| `news [symbol]` | `news BTC` | latest CryptoPanic posts |
| `compare <a> <b>` | `compare BTC ETH` | side-by-side TA snapshot |
| `watchlist add/rm/list [sym]` | `watchlist add BTC` | manage persistent watchlist |

Output is JSON to stdout. Charts are saved to `$HERMES_CHART_OUT` (default `/tmp/hermes-charts/`) and the absolute path is included in the JSON as `chart_path`.

## Symbols

Use the bare ticker (`BTC`, `ETH`, `SOL`, `DOGE`). The skill maps it to:
- CoinGecko ID (`bitcoin`, `ethereum`, `solana`, …) for price + market data.
- CCXT pair `<SYM>/USDT` for OHLCV via Binance public REST.

Custom mappings can be added in `feeds.py:_COINGECKO_IDS`. For coins not in the map, the lowercased ticker is tried as a CoinGecko ID directly.

## Data sources

- **CoinGecko** — `/simple/price`, `/coins/{id}`. Free Demo tier or anonymous. Set `COINGECKO_API_KEY` to lift the rate limit.
- **Binance via CCXT** — `fetch_ohlcv` on spot pairs. No auth, no key.
- **DeFiLlama** — `/tvl/{protocol}`, chain TVL. No auth.
- **CryptoPanic** — `/posts/`. Requires `CRYPTOPANIC_API_KEY` (free 200/day).
- **alternative.me** — Fear & Greed `/fng/?limit=1`. No auth.

## Hermes autonomy

Read-only by design. No trade execution, no signing, no on-chain calls. Safe to run without confirmation. The agent should still apply rate-limit prudence (max ~10 analyze calls/min).

## Caveats

- Stablecoins (USDT, USDC) work for price queries but TA is meaningless.
- Memecoins outside the curated ID map need either the explicit CoinGecko slug or the CCXT pair name (`PEPE/USDT`).
- TwelveData and Glassnode are NOT used — keeping the crypto skill 100% free tier.
