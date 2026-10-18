---
name: keeptabs-budget
description: Inspect or change keeptabs-codex token budget settings. Use when the user asks to view or modify a session token cap or hard-stop behavior.
---

# keeptabs budget

Settings are stored in `~/.codex/keeptabs/budget.json`. The helper is `scripts/keeptabs.py` under the plugin root. Resolve that root from this skill's installed path (`<plugin root>/skills/budget/SKILL.md`) and invoke the helper by its absolute path. Do not rely on `PLUGIN_ROOT`; Codex sets that variable for hook commands, not ordinary shell commands launched by a skill. If the settings file does not exist, initialize the defaults with:

    python3 <absolute-plugin-root>/scripts/keeptabs.py init

Show the file before edits. Only change settings the user explicitly asks to change. If a setting is missing from the personal file, use its value from the plugin's `budget.json`; the default confirmation thresholds are 10 ChatGPT Standard-rate credits and $1.00 API list-price equivalent. Supported fields are `session_limit_tokens` (positive integer or null), `confirm_prompt_above_chatgpt_credits` (positive number or null), `confirm_prompt_above_api_usd` (positive number or null), `daily_limit_tokens` (reserved; currently informational only), `warn_at_percent` (1–100), and `hard_stop` (boolean). Set either cost confirmation threshold to null to disable that check. The hook checks estimated session-to-date cost before each prompt, not the future request. If a threshold is reached, the hook rejects the submission before the model runs and does not save or replay it. The user must manually resend the complete prompt with `KEEP TABS CONTINUE:` at the beginning. That confirms only that submission; later prompts are checked again. Explain that ChatGPT estimates are Standard-rate credits and API estimates are list-price equivalents, not actual charges. Hard stop checks the transcript's last recorded usage before prompts and tools, so it cannot stop an in-flight model request.
