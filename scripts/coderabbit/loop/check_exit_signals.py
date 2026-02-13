#!/usr/bin/env python3
"""Check for exit signals in PR comments.

Exit signals:
- @claude-code stop
- @claude-code pause
- @claude-code exit

Usage:
    python3 scripts/coderabbit/loop/check_exit_signals.py [--pr PR_NUMBER]

Exit codes:
    0 - No exit signal found
    1 - Exit signal found (prints the signal)
    2 - Error occurred
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
)

EXIT_SIGNALS = ["stop", "pause", "exit"]
SIGNAL_PATTERN = re.compile(r"@claude-code\s+(stop|pause|exit)", re.IGNORECASE)


def check_exit_signals(pr_number: int | None = None) -> dict | None:
    """Check for exit signals in PR comments.

    Returns dict with signal info if found, None otherwise.
    """
    owner, repo = get_repo_info()

    # If no PR specified, check the current branch's PR
    if pr_number is None:
        pr_number = get_pr_for_branch()
        if not pr_number:
            return None

    # Query for recent comments
    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          comments(last: 20) {
            nodes {
              author { login }
              body
              createdAt
            }
          }
          reviewThreads(first: 50) {
            nodes {
              comments(last: 5) {
                nodes {
                  author { login }
                  body
                  createdAt
                }
              }
            }
          }
        }
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})
    pr_data = result["data"]["repository"]["pullRequest"]

    if not pr_data:
        raise ValueError(f"PR #{pr_number} not found in {owner}/{repo}")

    # Check general comments
    for comment in pr_data.get("comments", {}).get("nodes", []):
        body = comment.get("body", "")
        match = SIGNAL_PATTERN.search(body)
        if match:
            return {
                "signal": match.group(1).lower(),
                "pr": pr_number,
                "author": comment.get("author", {}).get("login"),
                "timestamp": comment.get("createdAt"),
                "source": "pr_comment",
            }

    # Check review thread comments
    for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
        for comment in thread.get("comments", {}).get("nodes", []):
            body = comment.get("body", "")
            match = SIGNAL_PATTERN.search(body)
            if match:
                return {
                    "signal": match.group(1).lower(),
                    "pr": pr_number,
                    "author": comment.get("author", {}).get("login"),
                    "timestamp": comment.get("createdAt"),
                    "source": "review_thread",
                }

    return None


def main():
    parser = argparse.ArgumentParser(description="Check for exit signals in PR comments")
    parser.add_argument("--pr", type=int, help="PR number to check")

    args = parser.parse_args()

    try:
        signal = check_exit_signals(args.pr)

        if signal:
            print(f"EXIT_SIGNAL_FOUND: {signal['signal']}")
            print(f"  PR: #{signal['pr']}")
            print(f"  Author: {signal['author']}")
            print(f"  Source: {signal['source']}")
            sys.exit(1)
        else:
            print("No exit signals found")
            sys.exit(0)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
