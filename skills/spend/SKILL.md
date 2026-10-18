---
name: keeptabs-spend
description: Show observed token usage for this Codex session and explain the configured token budget. Use when asked about keeptabs, Codex usage, tokens spent, or the current budget.
---

# keeptabs spend

Run the plugin's usage report and summarize observed input, cached input, output, reasoning output, total tokens, and the configured limit:

    python3 "${PLUGIN_ROOT}/scripts/keeptabs.py" status

The report is derived from Codex's local session transcript. It is best effort because that format is not a stable interface. Do not convert tokens into USD or claim billing cost; Codex plan usage and API billing are different and this plugin has no billing feed.
