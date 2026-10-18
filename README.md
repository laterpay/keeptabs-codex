# keeptabs-codex

An initial Codex port of Supertab's keeptabs usage and budget workflow. It reads local Codex session transcript `token_usage_record` events, reports observed token counts, warns at a configured threshold, and can deny later prompts and local tool calls after a session cap is reached.

## Important differences from the Claude plugin

- Codex does not expose Claude's in-process per-request telemetry or the pane API. This port has no live pane or guaranteed complete call ledger.
- The hook's `transcript_path` format is documented as unstable. Usage is best effort and may need updates as Codex evolves.
- This release reports tokens only. It does not estimate USD cost, because Codex usage may be subscription based and this is not an API billing feed.
- A hard stop only sees token usage already written to the transcript. It cannot interrupt an in-flight model request; it can block subsequent prompts and supported local tool calls. Hosted tools do not run local hooks.
- `daily_limit_tokens` is reserved in configuration but is not enforced yet.

## Install for local development

Enable this folder as a Codex plugin using the app's plugin controls. Review and trust its bundled hooks before expecting them to run. Initialize a personal config with `python3 scripts/keeptabs.py init`; then edit `~/.codex/keeptabs/budget.json`. Skills provide `keeptabs-spend` and `keeptabs-budget` workflows.

Hook scripts use only Python's standard library and write user settings under `$CODEX_HOME/keeptabs` (or `~/.codex/keeptabs`).
