# Forex + Commodities skill

Major forex pairs and commodity futures analyzer for [Hermes](https://github.com/aiandi/hermes). See top-level [README.md](../../README.md) for project context.

## Usage

```bash
python3 -m skills.forex_comm.analyze price EURUSD
python3 -m skills.forex_comm.analyze price GOLD
python3 -m skills.forex_comm.analyze ta XAUUSD --tf 4h
python3 -m skills.forex_comm.analyze analyze USDJPY --tf 1d
python3 -m skills.forex_comm.analyze calendar --impact high
python3 -m skills.forex_comm.analyze compare GOLD SILVER
python3 -m skills.forex_comm.analyze watchlist list
```

## Configuration

| Env var | Required | Purpose |
| --- | --- | --- |
| `TWELVEDATA_API_KEY` | recommended | forex OHLCV (free 800/day). Without it, yfinance fallback (`EURUSD=X`) is used with 15-min delay |
| `NINEROUTER_BASE_URL`, `NINEROUTER_API_KEY`, `HERMES_MODEL` | for narrative | 9router LLM |

Commodity tickers (`GOLD`, `OIL`, ...) always work without any key — yfinance commodity futures are anonymous.
