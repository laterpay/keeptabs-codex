# keeptabs-codex

An initial Codex port of Supertab's keeptabs usage and budget workflow. It reads local Codex session transcript `token_usage_record` events, reports observed token counts, warns at a configured threshold, and can deny later prompts and local tool calls after a session cap is reached.

## Important differences from the Claude plugin

- Codex does not expose Claude's in-process per-request telemetry or the pane API. This port has no live pane or guaranteed complete call ledger.
- The hook's `transcript_path` format is documented as unstable. Usage is best effort and may need updates as Codex evolves.
- This release reports tokens only. It does not estimate USD cost, because Codex usage may be subscription based and this is not an API billing feed.
- A hard stop only sees token usage already written to the transcript. It cannot interrupt an in-flight model request; it can block subsequent prompts and supported local tool calls. Hosted tools do not run local hooks.
- `daily_limit_tokens` is reserved in configuration but is not enforced yet.
- The provisional default session limit is 10,000,000 tokens, with a warning at 80% and hard stops disabled. This is a rough starting point informed by one published long-running Codex experiment, not a calibrated typical-session threshold. To gather observations, run the `keeptabs-spend` skill after a session and record its observed token total alongside a short session type (for example, coding, research, or short Q&A). Use the distribution—especially the median and 80th/90th percentile—to revisit the threshold. These are observed token counts, not cost estimates.

## Use the plugin

### Check token usage

Invoke the spend skill in a Codex conversation:

```text
$keeptabs-codex:keeptabs-spend
```

It reports observed input, cached input, output, reasoning output, total tokens, and the configured session limit for the latest available local transcript. Run it near the end of a conversation if you are recording session totals for threshold calibration.

### View or change the budget

Invoke the budget skill and state what you want to inspect or change:

```text
$keeptabs-codex:keeptabs-budget
```

For example, ask: “Set the session limit to 15 million tokens and keep hard stops off.” Settings live in `$CODEX_HOME/keeptabs/budget.json`, or `~/.codex/keeptabs/budget.json` when `CODEX_HOME` is not set. Supported fields are `session_limit_tokens` (positive integer or `null` for off), `warn_at_percent` (1–100), `hard_stop` (boolean), and `daily_limit_tokens` (reserved; not enforced).

The provisional defaults are a 10,000,000-token session limit, a warning at 80% (8,000,000 tokens), and hard stops off. When enabled, the prompt hook displays a warning after the threshold is reached. If you enable hard stops, the hooks can block later prompts and supported local tool calls after the limit is reached; they cannot interrupt an in-flight request, and hosted tools are not covered.

### Automatic hooks

After the plugin is installed and its hooks are enabled and trusted in Codex, Keeptabs checks the current transcript on prompt submission and before supported local tool calls. No manual command is needed for the configured warning or hard-stop behavior.

## Install for local development

Add the repository as a plugin using Codex's plugin controls. Review and trust its bundled hooks before expecting them to run. To initialize a personal config from the repository defaults while developing locally, run:

```sh
python3 scripts/keeptabs.py init
```

Then edit `$CODEX_HOME/keeptabs/budget.json` (or `~/.codex/keeptabs/budget.json`).

Hook scripts use only Python's standard library and write user settings under `$CODEX_HOME/keeptabs` (or `~/.codex/keeptabs`).
