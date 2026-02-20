#!/usr/bin/env python3
"""
SessionStart hook: Initialize session guard config.

Generates .claude/session-config.json with conflict group resolutions.
Each conflict group gets either a random selection or a context-based
deterministic selection. Skills check this config at invocation time
and self-disable if not selected for this session.
"""

import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_info, log_warning
except ImportError:
    # Minimal fallback
    def graceful_hook(blocking=False, name=None):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[frosty] Hook error: {e}", file=sys.stderr)
                    sys.exit(0)
            return wrapper
        return decorator

    def get_project_dir():
        return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))

    def log_info(msg, **_):
        print(f"[frosty] {msg}", file=sys.stderr)

    def log_warning(msg, **_):
        print(f"[frosty] {msg}", file=sys.stderr)

try:
    from safeguards import is_frosty_project, log_diagnostic
except ImportError:
    def is_frosty_project(p=None):
        return True, "fallback"

    def log_diagnostic(msg, **_):
        pass


# ============================================================================
# CONTEXT DETECTORS
#
# Context detectors return (selected_skill, reason) and always resolve
# definitively — they never fall back to random.
# ============================================================================

CONTEXT_DETECTORS = {}


# ============================================================================
# CONFLICT GROUP REGISTRY
# ============================================================================

# Conflict groups registry.
# Previously contained "session-end-learning" (wrap-up vs continuous-learning).
# That group was removed when wrap-up and continuous-learning were consolidated
# into /tree close AI phases. The infrastructure remains for future groups.
CONFLICT_GROUPS = {}


# ============================================================================
# RESOLUTION LOGIC
# ============================================================================

def generate_session_id(now: datetime) -> str:
    """Generate a session ID: date-time-random."""
    random_suffix = format(random.randint(0, 0xFFFF), "04x")
    return now.strftime("%Y%m%d-%H%M%S") + f"-{random_suffix}"


def resolve_random(skills: list) -> dict:
    """Resolve a conflict group by random selection."""
    rv = random.random()
    segment_size = 1.0 / len(skills)
    selected_index = min(int(rv / segment_size), len(skills) - 1)
    return {
        "selected": skills[selected_index],
        "selection_method": "random",
        "random_value": round(rv, 4),
    }


def resolve_context(skills: list, detector_name: str, project_dir: Path) -> dict:
    """Resolve a conflict group by context detection. Always definitive."""
    detector = CONTEXT_DETECTORS.get(detector_name)
    if not detector:
        # No detector found — select first skill as safe default
        log_warning(f"Context detector '{detector_name}' not found, using first skill as default")
        return {
            "selected": skills[0],
            "selection_method": "context",
            "context_reason": f"detector '{detector_name}' not found, defaulted to first skill",
        }

    selected, reason = detector(project_dir)
    return {
        "selected": selected,
        "selection_method": "context",
        "context_reason": reason,
    }


def resolve_group(group_name: str, group_config: dict, project_dir: Path) -> dict:
    """Resolve a single conflict group to a selection."""
    skills = group_config["skills"]
    method = group_config["selection_method"]

    result = {
        "description": group_config["description"],
        "skills": skills,
    }

    if not skills:
        log_warning(f"Conflict group '{group_name}' has no skills, skipping")
        result["selected"] = None
        result["selection_method"] = "none"
        return result

    if method == "random":
        result.update(resolve_random(skills))
    elif method == "context":
        detector_name = group_config.get("context_detector", "")
        result.update(resolve_context(skills, detector_name, project_dir))
    else:
        log_warning(f"Unknown selection method '{method}' for '{group_name}', defaulting to first skill")
        result["selected"] = skills[0]
        result["selection_method"] = "default"

    return result


# ============================================================================
# MAIN
# ============================================================================

@graceful_hook(blocking=False, name="session-guard-init")
def main():
    project_dir = get_project_dir()

    # SAFEGUARD: Skip if not a frosty-compatible project
    is_frosty, reason = is_frosty_project(project_dir)
    if not is_frosty:
        log_diagnostic(f"Skipping session guard: {reason}")
        sys.exit(0)

    log_diagnostic("session-guard-init started")

    # Generate config
    now = datetime.now(timezone.utc)
    config = {
        "version": 1,
        "session_id": generate_session_id(now),
        "generated_at": now.isoformat(),
        "conflict_groups": {},
    }

    # Resolve each conflict group
    for group_name, group_config in CONFLICT_GROUPS.items():
        config["conflict_groups"][group_name] = resolve_group(
            group_name, group_config, project_dir
        )

    # Write config to .claude/session-config.json
    config_dir = project_dir / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "session-config.json"

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    # Log selections for visibility
    for group_name, group_result in config["conflict_groups"].items():
        selected = group_result["selected"]
        method = group_result["selection_method"]
        log_info(f"Session guard [{group_name}]: {selected} ({method})")

    sys.exit(0)


if __name__ == "__main__":
    main()
