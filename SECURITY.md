# Security policy

This repository is **public**. It must contain **zero** secrets, credentials, API keys, wallet private keys, tokens, session cookies, or any other sensitive material.

## Rules

1. **No secret values in source.** Every API key / token / password is read from the environment at runtime. Look at the top of each `feeds.py` for the canonical pattern (`os.environ.get("<NAME>", "")`).
2. **No secret values in tests / fixtures / examples.** Use `<replace-me>` placeholders or dummy values like `"REDACTED"`.
3. **`.env` files are git-ignored.** A `.env.example` (no real values) may be committed for documentation; nothing else.
4. **Cookies / session blobs** never go in the repo. They live in `~/.agent/credentials/` on the Hermes host (chmod 600), referenced only by path.
5. **Wallet private keys** are out of scope for this repo entirely. The Hermes agent owns its own wallet credentials elsewhere.

## Disclosure

If you find a secret accidentally committed (e.g. in a historical commit), open an issue immediately. Do **not** include the secret value in the issue body — link to the commit hash + file path only, and the maintainer will rotate the secret and rewrite history.

## Threat model

This repo is **utility code** that produces market analysis JSON / chart PNGs. It does **not** execute trades, transfer funds, or sign on-chain transactions. The blast radius of a compromise is limited to:

- Spoofed analysis output (low: user verifies on their own chart provider).
- Free-tier API quota exhaustion (low: rate-limited per-key; recoverable in ~24h).

If future modules ever need write/trading capability, they belong in a **separate private** repo with a different threat model.
