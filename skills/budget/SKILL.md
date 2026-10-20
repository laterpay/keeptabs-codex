---
name: tokentabs-budget
description: Inspect or change TokenTabs token budget and prompt cost settings. Use when the user asks to view or modify a session token cap, hard-stop behavior, cost threshold, or warning/block mode.
---

# TokenTabs budget

Settings are stored in `~/.codex/tokentabs/budget.json`. Existing settings in `~/.codex/keeptabs/budget.json` are read and copied to the new location on first initialization. The helper is `scripts/tokentabs.py` under the plugin root. Resolve that root from this skill's installed path (`<plugin root>/skills/budget/SKILL.md`) and invoke the helper by its absolute path. Do not rely on `PLUGIN_ROOT`; Codex sets that variable for hook commands, not ordinary shell commands launched by a skill. If the settings file does not exist, initialize the defaults with:

    python3 <absolute-plugin-root>/scripts/tokentabs.py init

Show the file before edits. Only change settings the user explicitly asks to change. If a setting is missing from the personal file, use its value from the plugin's `budget.json`; default cost thresholds are 10 ChatGPT Standard-rate credits and $1.00 API list-price equivalent. Supported fields are `session_limit_tokens` (positive integer or null), `confirm_prompt_above_chatgpt_credits` (positive number or null), `confirm_prompt_above_api_usd` (positive number or null), `prompt_cost_action` (`"warn"` or `"block"`, default `"block"`), `daily_limit_tokens` (reserved; currently informational only), `warn_at_percent` (1–100), and `hard_stop` (boolean). Set either cost threshold to null to disable that check. When one or more thresholds are reached, `prompt_cost_action: "warn"` displays a warning and allows the prompt to proceed. `prompt_cost_action: "block"` rejects the submission before the model runs and does not save or replay it; the user must manually resend the complete prompt with `TOKEN TABS CONTINUE:` at the beginning. That confirms only that submission; later prompts are checked again. The hook checks estimated session-to-date cost before each prompt, not the future request. Explain that ChatGPT estimates are Standard-rate credits and API estimates are list-price equivalents, not actual charges. Hard stop checks the transcript's last recorded usage before prompts and tools, so it cannot stop an in-flight model request.
