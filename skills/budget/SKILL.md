---
name: keeptabs-budget
description: Inspect or change keeptabs-codex token budget settings. Use when the user asks to view or modify a session token cap or hard-stop behavior.
---

# keeptabs budget

Settings are stored in `~/.codex/keeptabs/budget.json`. If it does not exist, initialize the defaults with:

    python3 "${PLUGIN_ROOT}/scripts/keeptabs.py" init

Show the file before edits. Only change settings the user explicitly asks to change. Supported fields are `session_limit_tokens` (positive integer or null), `daily_limit_tokens` (reserved; currently informational only), `warn_at_percent` (1–100), and `hard_stop` (boolean). Explain that hard stop checks the transcript's last recorded usage before prompts and tools, so it cannot stop an in-flight model request.
