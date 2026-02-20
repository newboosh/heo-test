#!/usr/bin/env python3
"""
Sentinel Task Context Hook - Capture orchestrator intent before subagent spawns.

Fires on PreToolUse for Task tool calls. Reads last_assistant_message to
extract what the orchestrator acknowledged as intentional before spawning
a subagent. Writes this context to .sentinel/agent-context.json so that
sentinel-detect.py can suppress or downgrade findings made by the subagent
that were already acknowledged by the orchestrator.

Example flow:
  Orchestrator: "I'm keeping the debug prints while we diagnose issue #42"
  → spawns git-orchestrator (Task)
  → this hook fires, captures the intent, writes agent-context.json
  → git-orchestrator edits files
  → sentinel-detect.py fires, reads context, suppresses debug_print findings

Hook Event: PreToolUse
Trigger:     Task tool
Mode:        Non-blocking (never prevents the Task from running)
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from safeguards import guard_hook_execution, log_diagnostic
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return True
    def log_diagnostic(msg, **_): pass

try:
    from reasoning import classify_reasoning, extract_acknowledged_items, write_agent_context
    REASONING_AVAILABLE = True
except ImportError:
    REASONING_AVAILABLE = False


def main() -> None:
    try:
        if not guard_hook_execution():
            print(json.dumps({}))
            sys.exit(0)

        if not REASONING_AVAILABLE:
            log_diagnostic("reasoning module not available, skipping task context capture")
            print(json.dumps({}))
            sys.exit(0)

        hook_input = json.loads(sys.stdin.read())

        # Only act on Task tool
        if hook_input.get("tool_name") != "Task":
            print(json.dumps({}))
            sys.exit(0)

        last_msg = hook_input.get("last_assistant_message", "")
        if not last_msg:
            print(json.dumps({}))
            sys.exit(0)

        classification = classify_reasoning(last_msg)

        # Only write context if there's something meaningful to capture
        if not classification["has_context"]:
            print(json.dumps({}))
            sys.exit(0)

        acknowledged = extract_acknowledged_items(last_msg)
        cwd = hook_input.get("cwd", os.getcwd())

        write_agent_context(classification, acknowledged, last_msg, cwd=cwd)

        if acknowledged:
            log_diagnostic(
                f"[sentinel-task-context] Captured {len(acknowledged)} acknowledged item(s) "
                f"from orchestrator before Task spawn"
            )
        else:
            log_diagnostic(
                f"[sentinel-task-context] Captured reasoning context "
                f"(intentional={classification['intentional']}, cleanup={classification['cleanup']})"
            )

        print(json.dumps({}))
        sys.exit(0)

    except Exception as e:
        log_diagnostic(f"sentinel-task-context hook error: {e}", error=str(e))
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
