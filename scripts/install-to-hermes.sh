#!/usr/bin/env bash
# Wire the skills/ directory into a running Hermes installation by symlinking
# it under ~/.hermes/skills/research/market/. Updates from `git pull` propagate
# instantly, no copy needed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TARGET_DIR="$HERMES_HOME/skills/research/market"

if [[ ! -d "$HERMES_HOME" ]]; then
  echo "Hermes home not found at $HERMES_HOME — set HERMES_HOME env var or install Hermes first" >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET_DIR")"

if [[ -e "$TARGET_DIR" || -L "$TARGET_DIR" ]]; then
  echo "Backing up existing $TARGET_DIR to ${TARGET_DIR}.bak_$(date +%Y%m%d_%H%M%S)"
  mv "$TARGET_DIR" "${TARGET_DIR}.bak_$(date +%Y%m%d_%H%M%S)"
fi

ln -s "$REPO_ROOT/skills" "$TARGET_DIR"
echo "Installed: $TARGET_DIR -> $REPO_ROOT/skills"

# Optional: also wire an env file referenced by Hermes
if [[ ! -e "$HOME/.agent/credentials/market-skills.env" ]]; then
  cp "$REPO_ROOT/.env.example" "$HOME/.agent/credentials/market-skills.env" 2>/dev/null || true
  chmod 600 "$HOME/.agent/credentials/market-skills.env" 2>/dev/null || true
  echo "Created: ~/.agent/credentials/market-skills.env (edit to add free-tier API keys)"
fi

echo
echo "Done. Try:"
echo "  cd $REPO_ROOT && python3 -m skills.crypto.analyze price BTC"
