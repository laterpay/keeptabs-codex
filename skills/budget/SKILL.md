---
name: keeptabs-budget
description: Inspect or change keeptabs-codex token budget settings. Use when the user asks to view or modify a session token cap or hard-stop behavior.
---

# keeptabs budget

Settings are stored in `~/.codex/keeptabs/budget.json`. The helper is `scripts/keeptabs.py` under the plugin root. Resolve that root from this skill's installed path (`<plugin root>/skills/budget/SKILL.md`) and invoke the helper by its absolute path. Do not rely on `PLUGIN_ROOT`; Codex sets that variable for hook commands, not ordinary shell commands launched by a skill. If the settings file does not exist, initialize the defaults with:

    python3 <absolute-plugin-root>/scripts/keeptabs.py init

Show the file before edits. Only change settings the user explicitly asks to change. Supported fields are `session_limit_tokens` (positive integer or null), `daily_limit_tokens` (reserved; currently informational only), `warn_at_percent` (1–100), and `hard_stop` (boolean). Explain that hard stop checks the transcript's last recorded usage before prompts and tools, so it cannot stop an in-flight model request.
