#!/usr/bin/env python3
"""Check PR status including merge conflicts, unresolved threads, and CodeRabbit review status.

Usage:
    python3 scripts/coderabbit/check_pr_status.py --pr <PR_NUMBER> [--json]
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
    output_json,
    run_gh_command,
)

# CodeRabbit bot login variants (GitHub Apps appear as user[bot])
CODERABBIT_LOGINS = {"coderabbitai", "coderabbitai[bot]", "coderabbit"}


def is_coderabbit_user(login: str) -> bool:
    """Check if a login belongs to CodeRabbit bot."""
    return login.lower() in CODERABBIT_LOGINS


def get_pr_status(pr_number: int) -> dict:
    """Get comprehensive PR status."""
    owner, repo = get_repo_info()

    # GraphQL query for PR details
    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          number
          title
          state
          mergeable
          mergeStateStatus
          isDraft
          headRefName
          baseRefName
          reviewDecision
          reviews(last: 20) {
            nodes {
              author { login }
              state
              body
              submittedAt
            }
          }
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              isOutdated
              path
              line
              comments(first: 10) {
                nodes {
                  author { login }
                  body
                  createdAt
                }
              }
            }
          }
          comments(last: 50) {
            nodes {
              author { login }
              body
              createdAt
            }
          }
        }
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})

    # Defensive access - handle missing/malformed response
    try:
        pr_data = result["data"]["repository"]["pullRequest"]
    except (KeyError, TypeError):
        return {"error": f"Failed to fetch PR #{pr_number} - unexpected API response"}

    if not pr_data:
        return {"error": f"PR #{pr_number} not found"}

    # Count unresolved threads
    review_threads = pr_data.get("reviewThreads", {}).get("nodes", [])
    unresolved_threads = [t for t in review_threads if not t["isResolved"]]

    # Find CodeRabbit comments in unresolved threads
    coderabbit_comments = []
    coderabbit_thread_ids = set()  # Track threads with CodeRabbit comments
    for thread in unresolved_threads:
        comments = thread.get("comments", {}).get("nodes", [])
        for comment in comments:
            author = comment.get("author", {}).get("login", "")
            if is_coderabbit_user(author):
                coderabbit_thread_ids.add(thread["id"])
                coderabbit_comments.append(
                    {
                        "thread_id": thread["id"],
                        "file": thread.get("path"),
                        "line": thread.get("line"),
                        "body": comment["body"][:200] + "..."
                        if len(comment["body"]) > 200
                        else comment["body"],
                        "created_at": comment["createdAt"],
                    }
                )

    # Check for CodeRabbit general comments (PR-level, not inline)
    general_comments = pr_data.get("comments", {}).get("nodes", [])
    coderabbit_general = []
    for comment in general_comments:
        author = comment.get("author", {}).get("login", "")
        if is_coderabbit_user(author):
            body = comment.get("body", "")
            # Skip summary/walkthrough comments (not actionable)
            if not any(skip in body.lower() for skip in ["walkthrough", "summary by coderabbit"]):
                coderabbit_general.append(
                    {
                        "type": "general",
                        "body": body[:200] + "..." if len(body) > 200 else body,
                        "created_at": comment["createdAt"],
                    }
                )

    # Check if CodeRabbit is currently reviewing
    reviewing = False
    for comment in general_comments:
        author = comment.get("author", {}).get("login", "")
        body = comment.get("body", "").lower()
        if is_coderabbit_user(author):
            if "reviewing" in body or "analyzing" in body:
                reviewing = True

    # Determine PR state based on CodeRabbit feedback specifically
    mergeable = pr_data.get("mergeable", "UNKNOWN")
    has_conflicts = mergeable == "CONFLICTING"
    # Only consider unresolved if there are CodeRabbit comments to address
    has_coderabbit_feedback = len(coderabbit_thread_ids) > 0 or len(coderabbit_general) > 0

    if reviewing:
        state = "SKIP"
        state_reason = "CodeRabbit review in progress"
    elif has_coderabbit_feedback and has_conflicts:
        state = "CONFLICTS_BLOCKED"
        state_reason = "Has merge conflicts AND unresolved CodeRabbit comments - resolve comments first"
    elif has_conflicts and not has_coderabbit_feedback:
        state = "CONFLICTS_READY"
        state_reason = "Has merge conflicts but no unresolved CodeRabbit comments - can resolve conflicts"
    elif has_coderabbit_feedback:
        state = "WORK"
        state_reason = "Has unresolved CodeRabbit comments"
    else:
        state = "CLEAN"
        state_reason = "No unresolved CodeRabbit comments, no conflicts"

    return {
        "pr_number": pr_number,
        "title": pr_data["title"],
        "state": state,
        "state_reason": state_reason,
        "pr_state": pr_data["state"],
        "head_branch": pr_data["headRefName"],
        "base_branch": pr_data["baseRefName"],
        "mergeable": mergeable,
        "merge_state_status": pr_data.get("mergeStateStatus"),
        "is_draft": pr_data["isDraft"],
        "review_decision": pr_data.get("reviewDecision"),
        "has_conflicts": has_conflicts,
        "unresolved_threads": len(unresolved_threads),
        "total_threads": len(review_threads),
        "coderabbit_reviewing": reviewing,
        "coderabbit_inline_comments": len(coderabbit_comments),
        "coderabbit_general_comments": len(coderabbit_general),
        "coderabbit_comments": coderabbit_comments,
        "coderabbit_general": coderabbit_general,
    }


def print_human_readable(status: dict):
    """Print status in human-readable format."""
    print(f"PR #{status['pr_number']}: {status['title']}")
    print(f"Branch: {status['head_branch']} -> {status['base_branch']}")
    print(f"State: {status['state']} - {status['state_reason']}")
    print()

    print(f"Mergeable: {status['mergeable']}")
    if status["has_conflicts"]:
        print("  WARNING: Has merge conflicts!")

    print(f"Unresolved threads: {status['unresolved_threads']}/{status['total_threads']}")

    if status["coderabbit_reviewing"]:
        print("\nCodeRabbit is currently reviewing...")

    if status["coderabbit_inline_comments"]:
        print(f"\nCodeRabbit inline comments ({status['coderabbit_inline_comments']}):")
        for comment in status["coderabbit_comments"][:5]:
            print(f"  - {comment['file']}:{comment['line']}")
            print(f"    {comment['body'][:100]}...")

    if status["coderabbit_general_comments"]:
        print(f"\nCodeRabbit general comments ({status['coderabbit_general_comments']})")


def main():
    parser = argparse.ArgumentParser(description="Check PR status for CodeRabbit loop")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Get PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            eprint("Create a PR first with: gh pr create")
            sys.exit(1)

    try:
        status = get_pr_status(pr_number)

        if "error" in status:
            eprint(f"ERROR: {status['error']}")
            sys.exit(1)

        if args.json:
            output_json(status, pretty=True)
        else:
            print_human_readable(status)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
