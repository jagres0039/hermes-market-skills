"""Output / watchlist helpers."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

WATCHLIST_DIR = Path(os.environ.get("HERMES_WATCHLIST_DIR", str(Path.home() / ".hermes" / "watchlists")))


def emit(payload: dict[str, Any]) -> None:
    """Print payload as a single JSON line to stdout."""
    json.dump(payload, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def emit_error(msg: str, **extra: Any) -> None:
    emit({"ok": False, "error": msg, **extra})


def watchlist_path(skill: str) -> Path:
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    return WATCHLIST_DIR / f"{skill}.json"


def watchlist_load(skill: str) -> list[str]:
    p = watchlist_path(skill)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def watchlist_save(skill: str, items: list[str]) -> None:
    p = watchlist_path(skill)
    p.write_text(json.dumps(sorted(set(items)), indent=2))


def watchlist_add(skill: str, symbol: str) -> list[str]:
    items = watchlist_load(skill)
    if symbol.upper() not in (s.upper() for s in items):
        items.append(symbol.upper())
    watchlist_save(skill, items)
    return watchlist_load(skill)


def watchlist_remove(skill: str, symbol: str) -> list[str]:
    items = watchlist_load(skill)
    items = [s for s in items if s.upper() != symbol.upper()]
    watchlist_save(skill, items)
    return items
