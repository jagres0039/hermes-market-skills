"""Pure-function unit tests for symbol routing.

No network, no API keys. Safe to run anywhere.
"""

from skills.crypto.feeds import to_coingecko_id, to_ccxt_pair
from skills.forex_comm.feeds import asset_kind, to_yf_ticker, to_twelvedata_symbol
from skills.saham_idn.feeds import normalize_ticker


def test_crypto_known_tickers():
    assert to_coingecko_id("BTC") == "bitcoin"
    assert to_coingecko_id("ETH") == "ethereum"
    assert to_coingecko_id("SOL") == "solana"


def test_crypto_unknown_passes_through():
    # unknown ticker -> lowercased (CoinGecko also accepts IDs)
    assert to_coingecko_id("XYZQQQ") == "xyzqqq"


def test_ccxt_pair():
    assert to_ccxt_pair("BTC") == "BTC/USDT"
    assert to_ccxt_pair("ETH", quote="USD") == "ETH/USD"
    assert to_ccxt_pair("BTC/USDT") == "BTC/USDT"


def test_saham_idn_normalize():
    assert normalize_ticker("BBRI") == "BBRI.JK"
    assert normalize_ticker("bbca") == "BBCA.JK"
    assert normalize_ticker("BBRI.JK") == "BBRI.JK"
    assert normalize_ticker("^JKSE") == "^JKSE"


def test_forex_asset_kind():
    assert asset_kind("EURUSD") == "forex"
    assert asset_kind("EUR/USD") == "forex"
    assert asset_kind("GOLD") == "commodity"
    assert asset_kind("XAU") == "commodity"
    assert asset_kind("OIL") == "commodity"
    assert asset_kind("zzz") == "unknown"


def test_forex_to_yf():
    assert to_yf_ticker("GOLD") == "GC=F"
    assert to_yf_ticker("XAU") == "GC=F"
    assert to_yf_ticker("XAUUSD") == "GC=F"
    assert to_yf_ticker("OIL") == "CL=F"
    assert to_yf_ticker("EURUSD") == "EURUSD=X"
    assert to_yf_ticker("EUR/USD") == "EURUSD=X"


def test_forex_to_twelvedata():
    assert to_twelvedata_symbol("EURUSD") == "EUR/USD"
    assert to_twelvedata_symbol("EUR/USD") == "EUR/USD"
    assert to_twelvedata_symbol("GOLD") == "XAU/USD"
    assert to_twelvedata_symbol("XAU") == "XAU/USD"
    assert to_twelvedata_symbol("SILVER") == "XAG/USD"
