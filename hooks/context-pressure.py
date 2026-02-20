#!/usr/bin/env python3
"""
Context Pressure Monitoring Hook - PostToolUse

Fires on every tool call to track context window pressure. Increments
counters, computes weighted pressure scores, detects re-reads and
tool streaks, and emits advisory messages when thresholds are hit.

Always exits 0 (non-blocking). Target: <50ms per invocation.

Hook Event: PostToolUse
Trigger: All tool calls (matcher: "*")
Mode: Advisory (non-blocking, emits hookSpecificOutput.message)

Related:
  - hooks/lib/context_state.py - State/config management
  - agents/context-monitor.md - Persistent monitor agent
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from safeguards import guard_hook_execution, log_diagnostic
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return True
    def log_diagnostic(msg, **_): pass

try:
    from context_state import (
        ensure_context_dir,
        load_state,
        save_state,
        load_config,
        save_config,
        DEFAULT_STATE,
    )
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False


def generate_session_id() -> str:
    """Generate a session ID from current date and hour."""
    now = datetime.now()
    return now.strftime("%Y%m%d-%H")


def is_session_stale(state: dict, current_session_id: str) -> bool:
    """Check if the session has changed (new hour = new session)."""
    return state.get("session_id", "") != current_session_id


def reset_state_for_new_session(state: dict, session_id: str) -> dict:
    """Reset state for a new session, preserving version."""
    import copy
    fresh = copy.deepcopy(DEFAULT_STATE)
    fresh["session_id"] = session_id
    return fresh


def handle_acknowledge_checkpoint(state: dict, config: dict) -> bool:
    """Handle the acknowledge_checkpoint flag set by the agent.

    Resets pressure_since_checkpoint, clears re_reads, and marks
    last_checkpoint_at_call. Clears the flag in config.

    Returns:
        True if the flag was processed (config needs saving), False otherwise.
    """
    if config.get("acknowledge_checkpoint", False):
        flags = state.setdefault("flags", {})
        state["pressure_since_checkpoint"] = 0
        state["last_checkpoint_at_call"] = state.get("total_calls", 0)
        state["re_reads"] = []
        flags["checkpoint_requested"] = False
        flags["re_read_warning_sent"] = False
        state["flags"] = flags
        config["acknowledge_checkpoint"] = False
        return True
    return False


def increment_counters(state: dict, config: dict, tool_name: str) -> None:
    """Increment total_calls, tool_counts, and pressure score."""
    state["total_calls"] = state.get("total_calls", 0) + 1

    tool_counts = state.get("tool_counts", {})
    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
    state["tool_counts"] = tool_counts

    weights = config.get("weights", {})
    weight = weights.get(tool_name, 0)
    state["pressure_score"] = state.get("pressure_score", 0) + weight
    state["pressure_since_checkpoint"] = (
        state.get("pressure_since_checkpoint", 0) + weight
    )


def update_streak(state: dict, tool_name: str) -> None:
    """Update streak tracking. Reset warning flag when streak breaks."""
    streak = state.get("streak", {"tool": "", "count": 0})

    if streak.get("tool") == tool_name:
        streak["count"] = streak.get("count", 0) + 1
    else:
        # Streak broken - reset warning flag so next streak can warn
        state.setdefault("flags", {})["streak_warning_sent"] = False
        streak = {"tool": tool_name, "count": 1}

    state["streak"] = streak


def check_re_read(
    state: dict, config: dict, tool_name: str, hook_input: dict
) -> None:
    """Check for re-reads of previously read files."""
    if tool_name != "Read":
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    files_read = state.get("files_read", {})
    total_calls = state.get("total_calls", 0)
    re_read_gap = config.get("re_read_gap", 5)

    if file_path in files_read:
        last_read_at = files_read[file_path]
        gap = total_calls - last_read_at
        if gap >= re_read_gap:
            re_reads = state.get("re_reads", [])
            re_reads.append({
                "file": file_path,
                "gap": gap,
                "call_number": total_calls,
            })
            # Cap to prevent unbounded growth
            if len(re_reads) > 50:
                re_reads = re_reads[-50:]
            state["re_reads"] = re_reads

    # Record this read (update to latest call number)
    files_read[file_path] = total_calls
    state["files_read"] = files_read


def build_messages(state: dict, config: dict) -> list:
    """Build advisory messages if thresholds are exceeded.

    Only emits each message type once until the flag is cleared
    (checkpoint clears all flags, streak break clears streak flag).
    """
    messages = []
    flags = state.get("flags", {})
    msg_templates = config.get("messages", {})

    # Check suppress
    suppress_until = config.get("suppress_until_call", 0)
    if suppress_until and state.get("total_calls", 0) < suppress_until:
        return messages

    # Checkpoint pressure threshold
    threshold = config.get("pressure_threshold", 8)
    pressure = state.get("pressure_since_checkpoint", 0)
    if pressure >= threshold and not flags.get("checkpoint_requested", False):
        template = msg_templates.get(
            "checkpoint",
            "\n[context] Pressure {score}/{threshold}. Checkpoint recommended.\n",
        )
        messages.append(template.format(
            score=pressure, threshold=threshold
        ))
        flags["checkpoint_requested"] = True

    # Re-read detection
    re_reads = state.get("re_reads", [])
    if re_reads and not flags.get("re_read_warning_sent", False):
        latest = re_reads[-1]
        template = msg_templates.get(
            "re_read",
            "\n[context] Re-read: {file} (gap: {gap}).\n",
        )
        messages.append(template.format(
            file=latest["file"], gap=latest["gap"]
        ))
        flags["re_read_warning_sent"] = True

    # Streak detection
    streak = state.get("streak", {"tool": "", "count": 0})
    streak_limit = config.get("streak_limit", 3)
    if (
        streak.get("count", 0) >= streak_limit
        and not flags.get("streak_warning_sent", False)
    ):
        template = msg_templates.get(
            "streak",
            "\n[context] {count}x {tool} streak.\n",
        )
        messages.append(template.format(
            count=streak["count"], tool=streak["tool"]
        ))
        flags["streak_warning_sent"] = True

    state["flags"] = flags
    return messages


def main() -> None:
    """Hook entry point."""
    try:
        # Guard: only run in heo projects
        if not guard_hook_execution():
            print(json.dumps({}))
            sys.exit(0)

        # Check state library
        if not STATE_AVAILABLE:
            log_diagnostic("context_state not available, skipping pressure tracking")
            print(json.dumps({}))
            sys.exit(0)

        # Read hook input from stdin
        try:
            content = sys.stdin.read()
            if not content.strip():
                print(json.dumps({}))
                sys.exit(0)
            hook_input = json.loads(content)
        except (json.JSONDecodeError, IOError):
            print(json.dumps({}))
            sys.exit(0)

        tool_name = hook_input.get("tool_name", "")
        if not tool_name:
            print(json.dumps({}))
            sys.exit(0)

        cwd = hook_input.get("cwd", os.getcwd())

        # Ensure .context/ directory
        context_dir = ensure_context_dir(cwd)

        # Load state and config (defaults on missing/corrupt)
        # Note: no file locking — concurrent PostToolUse calls may lose
        # updates. This is acceptable since counters are advisory-only;
        # a missed increment just means slightly inaccurate pressure.
        state = load_state(context_dir)
        config = load_config(context_dir)

        # Check disabled flag
        if config.get("disabled", False):
            print(json.dumps({}))
            sys.exit(0)

        # Check session staleness
        session_id = generate_session_id()
        if is_session_stale(state, session_id):
            state = reset_state_for_new_session(state, session_id)

        # Handle acknowledge_checkpoint flag (save config if flag was cleared)
        ack_processed = handle_acknowledge_checkpoint(state, config)

        # Increment counters and pressure
        increment_counters(state, config, tool_name)

        # Update streak
        update_streak(state, tool_name)

        # Check for re-reads (Read tool only)
        check_re_read(state, config, tool_name, hook_input)

        # Build messages if thresholds exceeded
        messages = build_messages(state, config)

        # Save state atomically
        save_state(context_dir, state)

        # Save config if acknowledge_checkpoint was processed
        if ack_processed:
            save_config(context_dir, config)

        # Build response
        response = {}
        if messages:
            response = {
                "hookSpecificOutput": {
                    "message": "".join(messages),
                }
            }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # Always fail open - never block tool execution
        log_diagnostic(f"Context pressure hook error: {e}", error=str(e))
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
