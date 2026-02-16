#!/usr/bin/env python3
"""Fetch unresolved CodeRabbit comments from a PR.

Usage:
    python3 scripts/coderabbit/loop/fetch_comments.py --pr <PR_NUMBER> [--json]

Returns structured data with both inline and general comments.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
    output_json,
)

# Pattern to extract Dignified Rule references
RULE_PATTERN = re.compile(r"(?:Dignified\s+)?Rule\s*#?(\d+)", re.IGNORECASE)

# Pattern to extract severity
SEVERITY_PATTERN = re.compile(r"\*\*(critical|major|minor|suggestion)\*\*", re.IGNORECASE)

# Pattern to extract file references in general comments
FILE_REF_PATTERN = re.compile(r"`([^`]+\.(?:py|js|ts|jsx|tsx|go|rs|rb|java|cpp|c|h))`(?::(\d+))?")


def parse_suggested_fix(body: str) -> dict | None:
    """Extract suggested fix from comment body."""
    # Look for diff blocks
    diff_match = re.search(r"```diff\n(.*?)\n```", body, re.DOTALL)
    if diff_match:
        diff_content = diff_match.group(1)
        # Extract the new code (lines starting with +)
        new_lines = []
        for line in diff_content.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                new_lines.append(line[1:])  # Remove the + prefix
            elif line.startswith("-") or line.startswith("@@"):
                continue
            else:
                new_lines.append(line)

        return {
            "type": "diff",
            "raw_diff": diff_content,
            "new_code": "\n".join(new_lines),
            "is_committable": True,
        }

    # Look for suggestion blocks
    suggestion_match = re.search(r"```suggestion\n(.*?)\n```", body, re.DOTALL)
    if suggestion_match:
        return {
            "type": "suggestion",
            "new_code": suggestion_match.group(1),
            "is_committable": True,
        }

    # Look for code blocks with replacement intent
    code_match = re.search(r"```(?:python|javascript|typescript|go|rust)?\n(.*?)\n```", body, re.DOTALL)
    if code_match and any(phrase in body.lower() for phrase in ["should be", "replace with", "change to", "use instead"]):
        return {
            "type": "code_block",
            "new_code": code_match.group(1),
            "is_committable": False,  # Needs human verification
        }

    return None


def parse_comment(thread: dict, comment: dict) -> dict:
    """Parse a single comment into structured format."""
    body = comment.get("body", "")

    # Extract rule number
    rule_match = RULE_PATTERN.search(body)
    rule_number = int(rule_match.group(1)) if rule_match else None

    # Extract severity
    severity_match = SEVERITY_PATTERN.search(body)
    severity = severity_match.group(1).lower() if severity_match else "minor"

    # Extract suggested fix
    suggested_fix = parse_suggested_fix(body)

    return {
        "thread_id": thread["id"],
        "file": thread.get("path"),
        "line": thread.get("line"),
        "body": body,
        "severity": severity,
        "rule_number": rule_number,
        "suggested_fix": suggested_fix,
        "has_committable_suggestion": suggested_fix is not None and suggested_fix.get("is_committable", False),
        "created_at": comment.get("createdAt"),
        "author": comment.get("author", {}).get("login"),
    }


def parse_general_comment(comment: dict) -> dict:
    """Parse a general (non-thread) comment."""
    body = comment.get("body", "")

    # Extract file references
    file_refs = []
    for match in FILE_REF_PATTERN.finditer(body):
        file_path = match.group(1)
        line = int(match.group(2)) if match.group(2) else None
        file_refs.append({"file_path": file_path, "line": line})

    # Extract rule number
    rule_match = RULE_PATTERN.search(body)
    rule_number = int(rule_match.group(1)) if rule_match else None

    # Determine if actionable
    is_actionable = bool(file_refs) or rule_number is not None or parse_suggested_fix(body) is not None

    return {
        "comment_id": comment.get("id"),
        "type": "general",
        "body": body,
        "file_references": file_refs,
        "rule_number": rule_number,
        "suggested_fix": parse_suggested_fix(body),
        "is_actionable": is_actionable,
        "created_at": comment.get("createdAt"),
        "author": comment.get("author", {}).get("login"),
    }


def fetch_comments(pr_number: int) -> dict:
    """Fetch all unresolved CodeRabbit comments from a PR."""
    owner, repo = get_repo_info()

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              isOutdated
              path
              line
              comments(first: 20) {
                nodes {
                  id
                  author { login }
                  body
                  createdAt
                }
              }
            }
          }
          comments(last: 100) {
            nodes {
              id
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
    pr_data = result["data"]["repository"]["pullRequest"]

    if not pr_data:
        return {"error": f"PR #{pr_number} not found", "comments": [], "general_comments": []}

    # Process inline comments (review threads)
    inline_comments = []
    for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
        if thread.get("isResolved"):
            continue

        comments = thread.get("comments", {}).get("nodes", [])
        for comment in comments:
            author = comment.get("author", {}).get("login", "")
            if author.lower() in ["coderabbitai", "coderabbit"]:
                parsed = parse_comment(thread, comment)
                inline_comments.append(parsed)
                break  # Only take the first CodeRabbit comment per thread

    # Process general comments
    general_comments = []
    for comment in pr_data.get("comments", {}).get("nodes", []):
        author = comment.get("author", {}).get("login", "")
        if author.lower() in ["coderabbitai", "coderabbit"]:
            # Skip review summary comments (they're informational, not actionable)
            body = comment.get("body", "")
            if "## Summary" in body or "## Walkthrough" in body:
                continue
            parsed = parse_general_comment(comment)
            if parsed["is_actionable"]:
                general_comments.append(parsed)

    return {
        "pr_number": pr_number,
        "comments": inline_comments,
        "general_comments": general_comments,
        "total_inline": len(inline_comments),
        "total_general": len(general_comments),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch unresolved CodeRabbit comments")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (default)")

    args = parser.parse_args()

    # Get PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    try:
        data = fetch_comments(pr_number)

        if "error" in data and data["error"]:
            eprint(f"ERROR: {data['error']}")
            sys.exit(1)

        # Always output as JSON (this script is meant for programmatic use)
        output_json(data, pretty=True)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
