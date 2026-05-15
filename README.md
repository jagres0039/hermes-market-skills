# hermes-market-skills

Market-analysis skills for the [Hermes](https://github.com/aiandi/hermes) AI agent. Three independent skills covering the asset classes the agent (Gresman) is asked about most often:

| Skill | Scope | Trigger keywords (Bahasa / English) |
| --- | --- | --- |
| `skills/crypto` | Cryptocurrencies (BTC, ETH, altcoins, on-chain metrics) | `crypto`, `btc`, `eth`, `coin`, `token`, `defi`, ticker like `SOL`, `DOGE` |
| `skills/saham_idn` | Indonesian stock market (IDX / BEI) | `saham`, `ihsg`, `bbri`, `bbca`, `tlkm`, `asii`, ticker with `.JK` |
| `skills/forex_comm` | Forex pairs + commodities (gold, oil, silver, copper) | `forex`, `eurusd`, `usdjpy`, `gold`, `xau`, `oil`, `silver`, `komoditas` |

Each skill is **self-contained**: own data feed, own analysis logic, own CLI. The skills share TA / charting / LLM-summary helpers from `skills/_shared/`.

## Status

| Skill | Status |
| --- | --- |
| `_shared` (TA, chart, llm) | scaffolding |
| `crypto` | scaffolding |
| `saham_idn` | scaffolding |
| `forex_comm` | scaffolding |

## Quick start

```bash
# 1. clone
git clone https://github.com/jagres0039/hermes-market-skills.git
cd hermes-market-skills

# 2. install python deps (uses uv if available, falls back to pip)
python3 -m pip install --user -r requirements.txt

# 3. set free-tier API keys in env (all skills work without them, with reduced coverage)
export COINGECKO_API_KEY=""          # optional — boost rate limit
export TWELVEDATA_API_KEY=""         # optional — forex OHLCV (free 800/day)
export CRYPTOPANIC_API_KEY=""        # optional — crypto news feed

# 4. try each skill
python3 -m skills.crypto.analyze        price BTC
python3 -m skills.saham_idn.analyze     price BBRI
python3 -m skills.forex_comm.analyze    price XAUUSD
```

## CLI pattern (shared by all three skills)

```
python3 -m skills.<asset>.analyze <command> <symbol> [flags]

  price <symbol>             current price, 24h change, volume
  ta    <symbol> [--tf TF]   indicators (RSI, MACD, BB, EMA, Ichimoku, Fib)
  analyze <symbol> [--tf TF] full report (price + TA + news + opinion + chart PNG)
  news  <symbol|topic>       latest news + sentiment scoring
  compare <a> <b>            head-to-head comparison
  watchlist [add|rm|list] s  manage per-skill watchlist (JSON file)
```

`<TF>` is `5m`, `15m`, `1h`, `4h`, `1d` (default), `1w`.

Output is always JSON to stdout. Charts are saved to `OUT_DIR` (default `/tmp/hermes-charts/`) and the path is included in the JSON. Hermes uses the JSON to compose the natural-language reply (Bahasa Indonesia, default tone: educational + opinionated).

## Data sources (all free tier by default)

**Crypto** — CoinGecko (price + market cap), Binance public REST via CCXT (OHLCV), DeFiLlama (TVL), CryptoPanic (news).

**Saham IDN** — Yahoo Finance via `yfinance` with `.JK` suffix (OHLCV + fundamentals), IDX official scrape (composite stats), RSS from Bisnis Indonesia / Kontan (news).

**Forex + Commodities** — TwelveData (forex OHLCV), Yahoo futures tickers (`GC=F` gold, `SI=F` silver, `CL=F` oil WTI, `BZ=F` brent, `NG=F` natgas, `HG=F` copper), ForexFactory scrape (economic calendar).

See each skill's `README.md` for the full source list and rate-limit notes.

## Repository layout

```
hermes-market-skills/
├── README.md
├── LICENSE                       # MIT
├── SECURITY.md                   # no-secret-in-repo policy
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── skills/
│   ├── _shared/                  # shared library (NOT a skill, internal use only)
│   │   ├── __init__.py
│   │   ├── ta.py                 # technical analysis indicators
│   │   ├── chart.py              # matplotlib chart helper
│   │   ├── llm_summary.py        # wrapper around 9router LLM for narrative analysis
│   │   ├── http_cache.py         # tiny on-disk HTTP cache to be polite to free APIs
│   │   └── output.py             # JSON output formatting + watchlist storage
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── analyze.py            # CLI entrypoint
│   │   ├── feeds.py              # CoinGecko + CCXT + DeFiLlama + CryptoPanic adapters
│   │   ├── SKILL.md              # Hermes-facing skill manifest
│   │   └── README.md
│   ├── saham_idn/
│   │   ├── __init__.py
│   │   ├── analyze.py
│   │   ├── feeds.py              # yfinance + IDX scrape + RSS
│   │   ├── SKILL.md
│   │   └── README.md
│   └── forex_comm/
│       ├── __init__.py
│       ├── analyze.py
│       ├── feeds.py              # TwelveData + Yahoo commodities + ForexFactory
│       ├── SKILL.md
│       └── README.md
├── scripts/
│   ├── install-to-hermes.sh      # symlinks skills/ into ~/.hermes/skills/research/market/
│   └── smoketest.sh              # runs `price` on a known-good symbol for each skill
└── tests/
    └── ...
```

## Hermes integration

Each skill ships a `SKILL.md` that Hermes parses to discover its commands, trigger keywords, and required env vars. To wire all three skills into a running Hermes installation:

```bash
bash scripts/install-to-hermes.sh
```

The installer creates a symlink at `~/.hermes/skills/research/market/` pointing to this repo's `skills/` directory, so updates from `git pull` are picked up immediately.

## License

MIT — see [LICENSE](LICENSE). No warranty. Nothing in this repository constitutes financial advice. Trade at your own risk.
