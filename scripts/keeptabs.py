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


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def config():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        try:
            return json.loads(DEFAULT_CFG.read_text())
        except Exception:
            return {"session_limit_tokens": None, "daily_limit_tokens": None, "warn_at_percent": 80, "hard_stop": False}


def records(path):
    """Read Codex token_usage_record events; this private transcript format may change."""
    out = []
    if not path:
        return out
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if event.get("type") != "token_usage_record":
                        continue
                    p = event.get("payload") or {}
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


def run(mode):
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
        elif isinstance(cap, int) and cap > 0 and total >= cap * warn / 100:
            emit({"systemMessage": f"keeptabs budget warning: observed session usage is {total:,} tokens ({total/cap:.0%} of {cap:,})."})
        return
    if mode == "json":
        report["session_limit_tokens"] = cap
        report["hard_stop"] = bool(cfg.get("hard_stop"))
        emit(report)
        return
    if mode == "init":
        DATA.mkdir(parents=True, exist_ok=True)
        if not CFG.exists():
            CFG.write_text(DEFAULT_CFG.read_text())
        print(f"Initialized {CFG}")
        return
    print(f"keeptabs-codex · observed tokens: {total:,} across {report['turns']} turns")
    print(f"  input {report['input_tokens']:,} (cached {report['cached_input_tokens']:,}; cache write {report['cache_write_input_tokens']:,})")
    print(f"  output {report['output_tokens']:,} (reasoning {report['reasoning_output_tokens']:,})")
    print(f"  budget: {cap:,}" if isinstance(cap, int) else "  budget: off")
    print("  transcript: unavailable" if not path else f"  source: {path}")
    print("  note: Codex transcript usage is best effort; USD cost is not inferred.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "status")
