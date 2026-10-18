---
name: keeptabs-spend
description: Show observed token usage for this Codex session and explain the configured token budget. Use when asked about keeptabs, Codex usage, tokens spent, or the current budget.
---

# keeptabs spend

Run the plugin's usage report and summarize observed input, cached input, output, reasoning output, total tokens, the configured limit, and any available ChatGPT credit/API USD rate estimates. Include the pricing coverage and explain that these are estimates, not actual charges. The helper is `scripts/keeptabs.py` under the plugin root. Resolve that root from this skill's installed path (`<plugin root>/skills/spend/SKILL.md`) and invoke the helper by its absolute path. Do not rely on `PLUGIN_ROOT`; Codex sets that variable for hook commands, not ordinary shell commands launched by a skill.

    python3 <absolute-plugin-root>/scripts/keeptabs.py status

The report is derived from Codex's local session transcript. It is best effort because that format is not a stable interface. Never describe ChatGPT credits as dollars or claim an estimate is the actual amount billed. ChatGPT plan usage and API billing use different rates; explain which estimate is shown and its coverage.
