#!/usr/bin/env python3
"""Codex transcript-backed token usage and hook guard. Transcript format is best effort."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "keeptabs"
CFG = DATA / "budget.json"
DEFAULT_CFG = ROOT / "budget.json"
PRICING_FILE = Path(__file__).with_name("pricing.json")
CONFIRM_PREFIX = "KEEP TABS CONTINUE:"


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def config():
    try:
        cfg = json.loads(DEFAULT_CFG.read_text())
    except Exception:
        cfg = {"session_limit_tokens": None, "daily_limit_tokens": None, "warn_at_percent": 80,
               "hard_stop": False, "confirm_prompt_above_chatgpt_credits": 10,
               "confirm_prompt_above_api_usd": 1.0}
    try:
        user_cfg = json.loads(CFG.read_text())
    except Exception:
        user_cfg = {}
    if isinstance(user_cfg, dict):
        cfg.update(user_cfg)
    return cfg


def records(path):
    """Read Codex token_usage_record events; this private transcript format may change."""
    out = []
    models_by_turn = {}
    if not path:
        return out
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    p = event.get("payload") or {}
                    if event.get("type") == "turn_context":
                        turn_id = p.get("turn_id")
                        model = p.get("model")
                        if turn_id and model:
                            models_by_turn[turn_id] = str(model)
                        continue
                    if event.get("type") != "token_usage_record":
                        continue
                    # Codex writes a per-response usage record plus cumulative usage
                    # for the enclosing turn. Use the latter to avoid undercounting
                    # turns that contain more than one model response.
                    u = p.get("turn_token_usage") or p.get("usage") or {}
                    out.append({"ts": event.get("timestamp"), "turn_id": p.get("turn_id"),
                                "model": None, "input": int(u.get("input_tokens") or 0),
                                "cached_input": int(u.get("cached_input_tokens") or 0),
                                "cache_write_input": int(u.get("cache_write_input_tokens") or 0),
                                "output": int(u.get("output_tokens") or 0),
                                "reasoning_output": int(u.get("reasoning_output_tokens") or 0),
                                "total": int(u.get("total_tokens") or 0)})
                except (ValueError, TypeError):
                    continue
    except OSError:
        pass
    for row in out:
        row["model"] = models_by_turn.get(row["turn_id"])
    # Event records can represent cumulative thread usage. Prefer the latest record per turn.
    by_turn = {}
    for row in out:
        by_turn[row["turn_id"] or str(len(by_turn))] = row
    return list(by_turn.values())


def usage(path):
    rows = records(path)
    return {"turns": len(rows), "input_tokens": sum(x["input"] for x in rows),
            "cached_input_tokens": sum(x["cached_input"] for x in rows),
            "cache_write_input_tokens": sum(x["cache_write_input"] for x in rows),
            "output_tokens": sum(x["output"] for x in rows),
            "reasoning_output_tokens": sum(x["reasoning_output"] for x in rows),
            "total_tokens": sum(x["total"] for x in rows), "records": rows}


def latest_transcript():
    sessions = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
    try:
        return max(sessions.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime)
    except (ValueError, OSError):
        return None


def emit(obj):
    print(json.dumps(obj))


def load_pricing():
    try:
        return json.loads(PRICING_FILE.read_text())
    except (OSError, ValueError):
        return {"verified_date": None, "models": {}}


def estimate_costs(rows):
    """Return list-price estimates only for turns whose models have published rates."""
    pricing = load_pricing()
    models = pricing.get("models", {})
    totals = {
        "chatgpt_credits": {"value": 0.0, "priced_tokens": 0, "turns": 0},
        "api_usd": {"short": 0.0, "long": 0.0, "priced_tokens": 0, "turns": 0},
    }
    all_tokens = sum(row.get("total") or 0 for row in rows)
    for row in rows:
        model = models.get(row.get("model"))
        if not model:
            continue
        input_tokens = max(0, row.get("input") or 0)
        cached = min(input_tokens, max(0, row.get("cached_input") or 0))
        cache_write = min(input_tokens - cached, max(0, row.get("cache_write_input") or 0))
        uncached = input_tokens - cached - cache_write
        output = max(0, row.get("output") or 0)
        turn_tokens = row.get("total") or 0

        credit_rates = model.get("chatgpt_credits_per_million")
        if credit_rates:
            totals["chatgpt_credits"]["value"] += (
                (uncached + cache_write) * credit_rates["input"]
                + cached * credit_rates["cached_input"]
                + output * credit_rates["output"]
            ) / 1_000_000
            totals["chatgpt_credits"]["priced_tokens"] += turn_tokens
            totals["chatgpt_credits"]["turns"] += 1

        api_rates = model.get("api_usd_per_million")
        if api_rates and "short" in api_rates and "long" in api_rates:
            for context_class in ("short", "long"):
                rates = api_rates[context_class]
                totals["api_usd"][context_class] += (
                    uncached * rates["input"]
                    + cached * rates["cached_input"]
                    + cache_write * rates["cache_write_input"]
                    + output * rates["output"]
                ) / 1_000_000
            totals["api_usd"]["priced_tokens"] += turn_tokens
            totals["api_usd"]["turns"] += 1

    for estimate in totals.values():
        estimate["coverage_percent"] = (
            round(100 * estimate["priced_tokens"] / all_tokens, 1) if all_tokens else 0.0
        )
    totals["pricing_verified_date"] = pricing.get("verified_date")
    return totals


def prompt_preflight(report, cfg, prompt):
    estimates = estimate_costs(report["records"])
    messages = ["Keeptabs preflight (session usage before this prompt):"]
    credits = estimates["chatgpt_credits"]
    api = estimates["api_usd"]
    if credits["turns"]:
        messages.append(
            f"ChatGPT Standard-rate equivalent: {credits['value']:.2f} credits "
            f"({credits['coverage_percent']:.0f}% of observed tokens priced)."
        )
    else:
        messages.append("ChatGPT credit equivalent unavailable for the recorded model(s).")
    if api["turns"]:
        messages.append(
            f"API Standard list-price equivalent: ${api['short']:.4f}–${api['long']:.4f} USD "
            f"({api['coverage_percent']:.0f}% of observed tokens priced)."
        )
    else:
        messages.append("API USD equivalent unavailable for the recorded model(s).")
    messages.append("This is session-to-date, not a forecast of this prompt's full request or output.")

    prompt = prompt if isinstance(prompt, str) else ""
    confirmed = prompt.lstrip().startswith(CONFIRM_PREFIX)
    exceeded = []
    credit_limit = cfg.get("confirm_prompt_above_chatgpt_credits")
    if isinstance(credit_limit, (int, float)) and not isinstance(credit_limit, bool) and credit_limit > 0:
        if credits["turns"] and credits["value"] >= credit_limit:
            exceeded.append(f"ChatGPT estimate {credits['value']:.2f} credits reached {credit_limit:g} credits")
    api_limit = cfg.get("confirm_prompt_above_api_usd")
    if isinstance(api_limit, (int, float)) and not isinstance(api_limit, bool) and api_limit > 0:
        if api["turns"] and api["long"] >= api_limit:
            exceeded.append(f"API estimate upper bound ${api['long']:.4f} reached ${api_limit:.4f}")

    if exceeded and not confirmed:
        reason = "; ".join(exceeded)
        return {"decision": "block", "reason": (
            f"keeptabs: {reason}. To proceed, resend the full prompt prefixed with "
            f"'{CONFIRM_PREFIX}' (the blocked prompt is not replayed automatically)."
        )}
    if exceeded and confirmed:
        messages.append(f"Explicit confirmation accepted for this prompt ({CONFIRM_PREFIX}).")
        return {
            "systemMessage": " ".join(messages),
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"The user explicitly confirmed estimated session usage by prefixing this prompt with "
                    f"{CONFIRM_PREFIX}. Treat the text after that prefix as the user's request and do not echo the prefix."
                ),
            },
        }
    return {"systemMessage": " ".join(messages)}


def ensure_config():
    DATA.mkdir(parents=True, exist_ok=True)
    if not CFG.exists():
        CFG.write_text(DEFAULT_CFG.read_text())


def run(mode):
    if mode == "init-quiet":
        ensure_config()
        return
    event = read_input()
    path = event.get("transcript_path") or latest_transcript()
    report = usage(path)
    cfg = config()
    cap = cfg.get("session_limit_tokens")
    warn = cfg.get("warn_at_percent", 80)
    total = report["total_tokens"]
    over = isinstance(cap, int) and cap > 0 and total >= cap
    if mode == "hook-tool":
        if over and cfg.get("hard_stop"):
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                  "permissionDecisionReason": f"keeptabs: observed session usage {total:,} tokens reached the {cap:,}-token limit. Change ~/.codex/keeptabs/budget.json to adjust it."}})
        return
    if mode == "hook-prompt":
        if over and cfg.get("hard_stop"):
            emit({"continue": False, "stopReason": f"keeptabs: observed usage reached the {cap:,}-token session limit."})
        else:
            preflight = prompt_preflight(report, cfg, event.get("prompt"))
            if "systemMessage" in preflight and isinstance(cap, int) and cap > 0 and total >= cap * warn / 100:
                preflight["systemMessage"] = (
                    f"keeptabs budget warning: observed session usage is {total:,} tokens ({total/cap:.0%} of {cap:,}). "
                    + preflight["systemMessage"]
                )
            emit(preflight)
        return
    if mode == "json":
        report["cost_estimates"] = estimate_costs(report["records"])
        report["confirm_prompt_above_chatgpt_credits"] = cfg.get("confirm_prompt_above_chatgpt_credits")
        report["confirm_prompt_above_api_usd"] = cfg.get("confirm_prompt_above_api_usd")
        report["session_limit_tokens"] = cap
        report["hard_stop"] = bool(cfg.get("hard_stop"))
        emit(report)
        return
    if mode == "init":
        ensure_config()
        print(f"Initialized {CFG}")
        return
    print(f"keeptabs-codex · observed tokens: {total:,} across {report['turns']} turns")
    print(f"  input {report['input_tokens']:,} (cached {report['cached_input_tokens']:,}; cache write {report['cache_write_input_tokens']:,})")
    print(f"  output {report['output_tokens']:,} (reasoning {report['reasoning_output_tokens']:,})")
    print(f"  budget: {cap:,}" if isinstance(cap, int) else "  budget: off")
    estimates = estimate_costs(report["records"])
    credits = estimates["chatgpt_credits"]
    if credits["turns"]:
        print(f"  ChatGPT Standard-rate equivalent: {credits['value']:.2f} credits ({credits['coverage_percent']:.0f}% of tokens priced; not an invoice amount)")
    else:
        print("  ChatGPT credit estimate: unavailable (model pricing not recognized)")
    api = estimates["api_usd"]
    if api["turns"]:
        print(f"  API list-price equivalent: ${api['short']:.4f}–${api['long']:.4f} USD ({api['coverage_percent']:.0f}% of tokens priced; short-to-long context range)")
    else:
        print("  API USD estimate: unavailable (model pricing not recognized)")
    if estimates.get("pricing_verified_date"):
        print(f"  rates verified: {estimates['pricing_verified_date']}")
    credit_gate = cfg.get("confirm_prompt_above_chatgpt_credits")
    api_gate = cfg.get("confirm_prompt_above_api_usd")
    credit_gate_text = f"{credit_gate:g} credits" if isinstance(credit_gate, (int, float)) and credit_gate > 0 else "off"
    api_gate_text = f"${api_gate:g}" if isinstance(api_gate, (int, float)) and api_gate > 0 else "off"
    print(f"  prompt confirmation: ChatGPT {credit_gate_text}; API {api_gate_text}")
    print("  transcript: unavailable" if not path else f"  source: {path}")
    print("  note: estimates use published standard rates and transcript usage; actual plan consumption or billing may differ.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "status")
