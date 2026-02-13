#!/usr/bin/env python3
"""Post final summary when the CodeRabbit loop exits.

Usage:
    python3 scripts/coderabbit/loop/post_final_summary.py [--pr PR_NUMBER] [--reason REASON]

Reasons:
    - clean: All PRs are clean (no issues)
    - max_iterations: Reached max iterations
    - exit_signal: User requested exit
    - rate_limit: Rate limit reached
    - error: An error occurred
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.config import MAX_ITERATIONS
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_root,
    run_gh_command,
)

TRACKER_FILE = ".coderabbit-tracker.json"


def load_tracker() -> dict:
    """Load tracker data with graceful error handling."""
    path = get_repo_root() / TRACKER_FILE
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            eprint(f"Warning: Could not load tracker file: {e}")
            return {}
    return {}


def post_final_summary(pr_number: int, reason: str, details: str | None = None) -> bool:
    """Post final summary to a PR."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    tracker = load_tracker()

    reason_messages = {
        "clean": "All CodeRabbit comments resolved - PR is clean!",
        "max_iterations": f"Reached maximum iterations ({MAX_ITERATIONS}) - escalating to human review",
        "exit_signal": "Exit signal received - stopping as requested",
        "rate_limit": "Paused due to GitHub API rate limits",
        "error": "Stopped due to an error",
    }

    reason_emojis = {
        "clean": "",
        "max_iterations": "",
        "exit_signal": "",
        "rate_limit": "",
        "error": "",
    }

    emoji = reason_emojis.get(reason, "")
    message = reason_messages.get(reason, reason)

    body_parts = [
        f"## {emoji} CodeRabbit Loop Complete",
        "",
        f"**Status:** {message}",
        f"**Completed at:** {timestamp}",
    ]

    # Add session stats if available
    pr_count = tracker.get("pr_count", 0)
    comments = tracker.get("comments", [])
    if pr_count > 0 or comments:
        body_parts.extend([
            "",
            "### Session Statistics",
            f"- PRs processed this cycle: {pr_count}",
            f"- Comments addressed: {len(comments)}",
        ])

    # Add pattern analysis if available
    last_analysis = tracker.get("last_analysis", {})
    if last_analysis:
        summary = last_analysis.get("summary", {})
        if summary.get("top_rules"):
            body_parts.extend([
                "",
                "### Pattern Analysis",
                "**Most common rule violations:**",
            ])
            for rule, count in list(summary["top_rules"].items())[:3]:
                body_parts.append(f"- {rule}: {count} occurrences")

    if details:
        body_parts.extend([
            "",
            "### Details",
            details,
        ])

    body_parts.extend([
        "",
        "---",
        "*Automated by Claude Code CodeRabbit Loop*",
    ])

    body = "\n".join(body_parts)

    try:
        run_gh_command(
            ["pr", "comment", str(pr_number), "--body", body],
            check=True,
        )
        print(f"Final summary posted to PR #{pr_number}")
        return True
    except Exception as e:
        eprint(f"Failed to post final summary: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post final summary to PR")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument(
        "--reason",
        default="clean",
        choices=["clean", "max_iterations", "exit_signal", "rate_limit", "error"],
        help="Reason for completion",
    )
    parser.add_argument("--details", help="Additional details")

    args = parser.parse_args()

    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    success = post_final_summary(pr_number, args.reason, args.details)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
