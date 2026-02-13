#!/usr/bin/env python3
"""Post an audit log comment to a PR.

Usage:
    python3 scripts/coderabbit/loop/post_audit_log.py --pr PR_NUMBER --iteration N --action ACTION

Actions:
    - fixes_pushed: Fixes were committed and pushed
    - conflicts_resolved: Merge conflicts were resolved
    - escalated: Issue escalated to human
    - paused: Loop paused due to rate limit or exit signal
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.config import MAX_ITERATIONS
from coderabbit.utils import eprint, run_gh_command


def post_audit_log(pr_number: int, iteration: int | None, action: str, details: str | None = None) -> bool:
    """Post an audit log comment to a PR."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    action_messages = {
        "fixes_pushed": "Pushed fixes for CodeRabbit review comments",
        "conflicts_resolved": "Resolved merge conflicts with main branch",
        "escalated": "Issue escalated to human review",
        "paused": "Loop paused",
        "started": "CodeRabbit loop started",
        "completed": "CodeRabbit loop completed successfully",
    }

    message = action_messages.get(action, action)

    body_parts = [
        "### CodeRabbit Loop Audit Log",
        "",
        f"**Timestamp:** {timestamp}",
    ]

    if iteration is not None:
        body_parts.append(f"**Iteration:** {iteration}/{MAX_ITERATIONS}")

    body_parts.extend([
        f"**Action:** {message}",
    ])

    if details:
        body_parts.extend([
            "",
            "**Details:**",
            details,
        ])

    body_parts.extend([
        "",
        "---",
        "*Automated by Claude Code CodeRabbit Loop*",
    ])

    body = "\n".join(body_parts)

    try:
        result = run_gh_command(
            ["pr", "comment", str(pr_number), "--body", body],
            check=True,
        )
        print(f"Audit log posted to PR #{pr_number}")
        return True
    except Exception as e:
        eprint(f"Failed to post audit log: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post audit log to PR")
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument("--iteration", type=int, help="Current iteration number")
    parser.add_argument(
        "--action",
        required=True,
        choices=["fixes_pushed", "conflicts_resolved", "escalated", "paused", "started", "completed"],
        help="Action being logged",
    )
    parser.add_argument("--details", help="Additional details")

    args = parser.parse_args()

    success = post_audit_log(args.pr, args.iteration, args.action, args.details)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
