"""Narrative analysis via Hermes' local 9router LLM.

Used by the three skill `analyze` commands to turn raw indicators into a short,
opinionated Bahasa Indonesia summary in Gresman's voice.

If the LLM is unreachable, this module silently falls back to a deterministic
template-based summary so the skill never fails just because the model is down.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests


BASE_URL = os.environ.get("NINEROUTER_BASE_URL", "http://localhost:20128/v1")
API_KEY = os.environ.get("NINEROUTER_API_KEY", "")
MODEL = os.environ.get("HERMES_MODEL", "jagrescombo")

SYSTEM_PROMPT = (
    "Lo Gresman, AI agent partner-nya Abang. Lo ngomong Bahasa Indonesia register gua/lu, "
    "langsung, gak pake basa-basi. Lo expert di market analysis tapi gak sok tau — "
    "kalo data ambigu, bilang ambigu.\n\n"
    "Format reply lo:\n"
    "1. Satu kalimat verdict (mis. 'short term bullish' / 'bearish setup' / 'mixed signal').\n"
    "2. 3-5 bullet point reasoning, masing-masing satu baris pendek.\n"
    "3. Satu kalimat 'kalo gua sih...' opini lo (pake disclaimer 'NFA' = not financial advice).\n"
    "4. Maks 150 kata total.\n"
    "Jangan pake markdown header. Pakai dash buat bullet."
)


def _fallback(data: dict[str, Any]) -> str:
    """Deterministic non-LLM fallback summary."""
    sym = data.get("symbol", "?")
    tf = data.get("timeframe", "?")
    ta = data.get("ta", {}) or {}
    price = data.get("price", {}) or {}
    last = ta.get("last_close") or price.get("last")
    change = price.get("change_24h_pct")
    rsi = ta.get("rsi_14")
    trend = ta.get("trend_state") or "unknown"
    macd_state = ta.get("macd_state") or "unknown"
    bb_pct = ta.get("bb_pct")

    parts = [f"{sym} ({tf}): trend={trend}, MACD={macd_state}."]
    if last is not None:
        parts.append(f"- Harga terakhir: {last}.")
    if change is not None:
        parts.append(f"- Perubahan 24 jam: {change:+.2f}%.")
    if rsi is not None:
        zone = ta.get("rsi_state") or "?"
        parts.append(f"- RSI(14): {rsi:.1f} ({zone}).")
    if bb_pct is not None:
        parts.append(f"- BB %B: {bb_pct:.2f} (0=lower band, 1=upper band).")
    parts.append("- Catatan: ringkasan auto-generated tanpa LLM (fallback mode).")
    parts.append("Kalo gua sih, baca chart-nya sendiri biar yakin. NFA.")
    return "\n".join(parts)


def summarize(payload: dict[str, Any], *, timeout: float = 30.0) -> str:
    """Return a short narrative summary of `payload` (free-form structured dict).

    Falls back to deterministic template if the LLM endpoint is unreachable.
    """
    user_msg = (
        "Analisa data market berikut, kasih verdict + 3-5 bullet + opini lo + NFA. "
        "Maks 150 kata. Data JSON:\n```json\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
        + "\n```"
    )
    try:
        resp = requests.post(
            BASE_URL.rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.4,
                "max_tokens": 400,
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            return _fallback(payload) + f"\n(LLM HTTP {resp.status_code})"
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text or _fallback(payload)
    except Exception as e:  # pragma: no cover
        return _fallback(payload) + f"\n(LLM error: {type(e).__name__})"
