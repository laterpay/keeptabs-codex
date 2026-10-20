# TokenTabs Codex

A Codex token usage and budget plugin. It reads local Codex session transcript `token_usage_record` events, reports observed token counts, warns at a configured threshold, and can deny later prompts and local tool calls after a session cap is reached.

## Codex-specific behavior

- Codex hooks do not provide the in-process per-request telemetry or pane API available in the Claude Code version. TokenTabs therefore has no live pane or guaranteed complete call ledger.
- Codex documents the hook's `transcript_path` format as unstable. Usage is best effort and may need updates as Codex evolves.
- Cost estimates are best-effort rate equivalents, not a bill. ChatGPT use is shown as Standard-rate credits; API use is shown as Standard list-price USD, with a short-to-long context range when published rates differ. ChatGPT credits are not converted to dollars because plan allowances and credit prices vary.
- A hard stop only sees token usage already written to the transcript. It cannot interrupt an in-flight model request; it can block subsequent prompts and supported local tool calls. Hosted tools do not run local hooks.
- `daily_limit_tokens` is reserved in configuration but is not enforced yet.
- The provisional default session limit is 10,000,000 tokens, with a warning at 80% and hard stops disabled. This is a rough starting point informed by one published long-running Codex experiment, not a calibrated typical-session threshold. To gather observations, run the `tokentabs-spend` skill after a session and record its observed token total alongside a short session type (for example, coding, research, or short Q&A). Use the distribution—especially the median and 80th/90th percentile—to revisit the threshold. These are observed token counts, not cost estimates.

## Use the plugin

### Check token usage

Invoke the spend skill in a Codex conversation:

```text
$tokentabs-codex:tokentabs-spend
```

It reports observed input, cached input, output, reasoning output, total tokens, the configured session limit, and model-based rate estimates where the transcript model and published rates are recognized. Run it near the end of a conversation if you are recording session totals for threshold calibration.

Cost estimates are shown separately as ChatGPT Standard-rate credits and API Standard list-price USD. The API estimate spans published short- and long-context rates; the transcript does not identify API billing mode, exact context class, or speed mode. Unknown models are excluded and the priced-token coverage is shown. Rates are stored in `scripts/pricing.json` with a verification date and source links. Estimates may differ from actual subscription consumption or API charges.

### View or change the budget

Invoke the budget skill and state what you want to inspect or change:

```text
$tokentabs-codex:tokentabs-budget
```

For example, ask: “Set the session limit to 15 million tokens, keep hard stops off, and warn instead of blocking when cost thresholds are reached.” Settings live in `$CODEX_HOME/tokentabs/budget.json`, or `~/.codex/tokentabs/budget.json` when `CODEX_HOME` is not set. If the new TokenTabs settings file does not exist, TokenTabs copies settings from the previous `$CODEX_HOME/keeptabs/budget.json` location (or `~/.codex/keeptabs/budget.json`) on first initialization. The original file is left in place. Supported fields are `session_limit_tokens` (positive integer or `null` for off), `warn_at_percent` (1–100), `hard_stop` (boolean), `confirm_prompt_above_chatgpt_credits` and `confirm_prompt_above_api_usd` (positive number or `null` to disable each check), `prompt_cost_action` (`"warn"` or `"block"`), and `daily_limit_tokens` (reserved; not enforced).

The provisional defaults are a 10,000,000-token session limit, a warning at 80% (8,000,000 tokens), and hard stops off. When enabled, the prompt hook displays a warning after the threshold is reached. If you enable hard stops, the hooks can block later prompts and supported local tool calls after the limit is reached; they cannot interrupt an in-flight request, and hosted tools are not covered.

### Prompt cost preflight

Before each prompt, the hook reads usage already recorded in the current session transcript and displays session-to-date cost estimates. It compares those estimates with the configured thresholds. By default, the thresholds are 10 ChatGPT Standard-rate credits and $1.00 API list-price equivalent, and reaching either threshold triggers the configured action. The API check uses the upper end of the short-to-long context estimate. Set a threshold to `null` in the personal budget file to turn off that check.

Choose what happens when a threshold is reached with `prompt_cost_action` in your personal `budget.json`:

```json
{
  "prompt_cost_action": "warn"
}
```

`"warn"` displays the threshold warning and allows the prompt to proceed. `"block"` (the default) rejects the prompt before it runs; Codex does not retain it, so you must resend the full prompt with `TOKEN TABS CONTINUE:` at the beginning. This setting controls only cost threshold behavior; token hard stops are controlled separately by `hard_stop`.

The check happens before the submitted prompt runs. It only sees usage already written to the transcript, so if a prompt itself pushes the session over a threshold, that prompt can run; the configured warning or block action takes effect on the next prompt. Estimates are rate equivalents, not a forecast of the new prompt's full cost or a bill.

<img width="1554" height="640" alt="TokenTabs prompt cost warning example" src="https://github.com/user-attachments/assets/68c17bbc-a90d-473f-bbc6-a56446a10bc1" />

When a prompt is blocked, Codex rejects that submission before sending it to the model. TokenTabs does not save or replay it. To continue, manually resend the complete prompt with `TOKEN TABS CONTINUE:` at the very beginning, for example:

```text
TOKEN TABS CONTINUE: Please summarize the changes.
```

That prefix confirms this one submission. The hook lets it through and adds context asking Codex to treat the text after the prefix as the request and not repeat the marker. It does not disable the gate or reset session usage, so any later prompt that is still above a threshold will need the prefix too. This is a manual resubmission flow, not a confirmation dialog that remembers or automatically replays your blocked prompt.

### Automatic hooks

TokenTabs uses Codex lifecycle hooks; they run automatically after setup, so you do not need to invoke a skill for each prompt or tool call. The hooks do the following:

- `SessionStart` creates `$CODEX_HOME/tokentabs/budget.json` from the plugin defaults if the file does not already exist. It never overwrites an existing personal config.
- `UserPromptSubmit` reports session-to-date usage and cost estimates, applies configured cost confirmation thresholds, and enforces a hard token stop if enabled.
- `PreToolUse` enforces a configured hard token stop before supported local tool calls.

**You must review and trust the hooks before Codex will run them.** Enabling or installing the plugin alone does not grant hook trust. In Codex CLI, enter `/hooks` to inspect the TokenTabs hooks, review their commands, and trust the current definitions. If Codex says hooks need review at startup, follow that message and open `/hooks`. In the Codex desktop app, use its hook review prompt or hook controls when shown; if the controls are not available in your current surface, run `/hooks` in Codex CLI.

Codex stores trust for each hook definition. If a hook changes after a plugin update, Codex marks the updated definition for review and skips it until you trust it again. The plugin must also remain enabled. Once trusted, the hooks run on their matching events without further per-run approval. These lifecycle hooks are supported for plugins installed manually in Codex desktop and require their scripts to be available in that execution environment.

Config initialization happens when a Codex session starts with the plugin enabled and the `SessionStart` hook trusted; it does not run at installation time. To confirm TokenTabs is active, submit a prompt and look for the TokenTabs usage/cost system message, or run the spend skill to inspect the current session. If no TokenTabs message appears, check that the plugin is enabled and review/trust its hooks with `/hooks`.

## Install for local development

Add the repository as a plugin using Codex's plugin controls, enable it, then review and trust its bundled hooks with `/hooks` before expecting automatic behavior. Codex may request review again if the hook definitions change. To initialize a personal config from the repository defaults while developing locally, run:

```sh
python3 scripts/tokentabs.py init
```

Then edit `$CODEX_HOME/tokentabs/budget.json` (or `~/.codex/tokentabs/budget.json`).

Hook scripts use only Python's standard library and write user settings under `$CODEX_HOME/tokentabs` (or `~/.codex/tokentabs`).
