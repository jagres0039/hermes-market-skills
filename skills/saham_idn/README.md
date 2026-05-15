# Saham IDN skill

Indonesia stock market (IDX / BEI) analyzer for [Hermes](https://github.com/aiandi/hermes). See top-level [README.md](../../README.md) for project context.

## Usage

```bash
python3 -m skills.saham_idn.analyze price BBRI
python3 -m skills.saham_idn.analyze ihsg
python3 -m skills.saham_idn.analyze ta BBCA --tf 1d
python3 -m skills.saham_idn.analyze analyze TLKM --tf 1d
python3 -m skills.saham_idn.analyze news bank --limit 5
python3 -m skills.saham_idn.analyze compare BBRI BBCA
python3 -m skills.saham_idn.analyze watchlist list
```

## Configuration

No required env vars. All data sources (yfinance, RSS) are anonymous. The narrative summary requires the Hermes LLM env vars described in the top-level README.
