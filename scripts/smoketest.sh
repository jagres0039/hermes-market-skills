#!/usr/bin/env bash
# Run a `price` query on a known-good symbol for each skill. Verifies wiring,
# Python deps, and free-tier API connectivity in one go.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "== crypto: BTC =="
python3 -m skills.crypto.analyze price BTC || true
echo

echo "== saham_idn: BBRI =="
python3 -m skills.saham_idn.analyze price BBRI || true
echo

echo "== forex_comm: GOLD =="
python3 -m skills.forex_comm.analyze price GOLD || true
echo

echo "Done."
