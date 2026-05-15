# Crypto skill

Pluggable into [Hermes](https://github.com/aiandi/hermes) via `SKILL.md` discovery. See top-level [README.md](../../README.md) for project context.

## Usage

```bash
# from the repo root
python3 -m skills.crypto.analyze price BTC
python3 -m skills.crypto.analyze ta ETH --tf 4h
python3 -m skills.crypto.analyze analyze SOL --tf 1d
python3 -m skills.crypto.analyze news BTC --limit 5
python3 -m skills.crypto.analyze compare BTC ETH --tf 1d
python3 -m skills.crypto.analyze watchlist add BTC
```

Output is JSON to stdout, suitable for piping to Hermes' narrative-formatter.

## Configuration

| Env var | Required | Purpose |
| --- | --- | --- |
| `COINGECKO_API_KEY` | no | CoinGecko Demo API key (free, higher rate limit) |
| `CRYPTOPANIC_API_KEY` | for `news` / `analyze --news` | CryptoPanic free key (200/day) |
| `NINEROUTER_BASE_URL`, `NINEROUTER_API_KEY`, `HERMES_MODEL` | for narrative | 9router LLM access |

The skill works without any of these — price, ta, OHLCV, F&G, and DeFiLlama all run anonymously.
