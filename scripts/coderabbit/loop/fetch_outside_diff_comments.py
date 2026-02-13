#!/usr/bin/env python3
"""Fetch CodeRabbit comments that are outside the diff.

These are comments that CodeRabbit couldn't post inline due to GitHub platform
limitations. They contain the caution message:
"Some comments are outside the diff and can't be posted inline due to platform limitations."

Usage:
    python3 scripts/coderabbit/loop/fetch_outside_diff_comments.py --pr <PR_NUMBER> [--json]
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

# The exact caution message CodeRabbit uses for out-of-diff comments
OUTSIDE_DIFF_CAUTION = "Some comments are outside the diff and can't be posted inline due to platform limitations."

# Pattern to extract file:line references in various formats
FILE_LINE_PATTERNS = [
    # `path/to/file.py:42` - backtick format
    re.compile(r"`([^`]+?\.[a-zA-Z0-9]+):(\d+)`"),
    # path/to/file.py:42 - plain format
    re.compile(r"(?:^|\s)([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):(\d+)(?:\s|$|[,;])"),
    # **path/to/file.py** line 42 - bold format with line keyword
    re.compile(r"\*\*([^*]+?\.[a-zA-Z0-9]+)\*\*.*?line\s+(\d+)", re.IGNORECASE),
    # [path/to/file.py](link) line 42 - markdown link format
    re.compile(r"\[([^\]]+?\.[a-zA-Z0-9]+)\]\([^)]+\).*?line\s+(\d+)", re.IGNORECASE),
]

# Pattern to extract Dignified Rule references
RULE_PATTERN = re.compile(r"(?:Dignified\s+)?Rule\s*#?(\d+)", re.IGNORECASE)

# Pattern to extract severity
SEVERITY_PATTERN = re.compile(r"\*\*(critical|major|minor|suggestion)\*\*", re.IGNORECASE)


def extract_file_references(text: str) -> list[dict]:
    """Extract file:line references from text using multiple patterns."""
    refs = []
    seen = set()

    for pattern in FILE_LINE_PATTERNS:
        for match in pattern.finditer(text):
            file_path = match.group(1)
            line = int(match.group(2))
            key = (file_path, line)
            if key not in seen:
                seen.add(key)
                refs.append({"file_path": file_path, "line": line})

    return refs


def parse_suggested_fix(body: str) -> dict | None:
    """Extract suggested fix from comment body."""
    # Look for diff blocks
    diff_match = re.search(r"```diff\n(.*?)\n```", body, re.DOTALL)
    if diff_match:
        diff_content = diff_match.group(1)
        new_lines = []
        for line in diff_content.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                new_lines.append(line[1:])
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
    code_match = re.search(
        r"```(?:python|javascript|typescript|go|rust)?\n(.*?)\n```", body, re.DOTALL
    )
    if code_match and any(
        phrase in body.lower()
        for phrase in ["should be", "replace with", "change to", "use instead"]
    ):
        return {
            "type": "code_block",
            "new_code": code_match.group(1),
            "is_committable": False,
        }

    return None


def parse_outside_diff_comment(comment: dict) -> dict | None:
    """Parse a comment that contains the outside-diff caution message.

    Returns None if the comment doesn't contain the caution message.
    """
    body = comment.get("body", "")

    # Check for the exact caution message
    if OUTSIDE_DIFF_CAUTION not in body:
        return None

    # Extract file references
    file_refs = extract_file_references(body)

    # Extract rule number
    rule_match = RULE_PATTERN.search(body)
    rule_number = int(rule_match.group(1)) if rule_match else None

    # Extract severity
    severity_match = SEVERITY_PATTERN.search(body)
    severity = severity_match.group(1).lower() if severity_match else "minor"

    # Extract suggested fix
    suggested_fix = parse_suggested_fix(body)

    # Extract the actual comment content (after the caution block)
    # CodeRabbit typically puts the caution in a blockquote or details section
    content_after_caution = body.split(OUTSIDE_DIFF_CAUTION)[-1].strip()

    return {
        "comment_id": comment.get("id"),
        "type": "outside_diff",
        "body": body,
        "content_after_caution": content_after_caution,
        "file_references": file_refs,
        "rule_number": rule_number,
        "severity": severity,
        "suggested_fix": suggested_fix,
        "has_actionable_content": bool(file_refs) or suggested_fix is not None,
        "created_at": comment.get("createdAt"),
        "author": comment.get("author", {}).get("login"),
        "url": comment.get("url"),
    }


def fetch_outside_diff_comments(pr_number: int) -> dict:
    """Fetch all CodeRabbit comments with outside-diff content from a PR."""
    owner, repo = get_repo_info()

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          comments(last: 100) {
            nodes {
              id
              url
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
        return {
            "error": f"PR #{pr_number} not found",
            "outside_diff_comments": [],
        }

    outside_diff_comments = []
    for comment in pr_data.get("comments", {}).get("nodes", []):
        author = comment.get("author", {}).get("login", "")
        if author.lower() not in ["coderabbitai", "coderabbit"]:
            continue

        parsed = parse_outside_diff_comment(comment)
        if parsed:
            outside_diff_comments.append(parsed)

    return {
        "pr_number": pr_number,
        "outside_diff_comments": outside_diff_comments,
        "total": len(outside_diff_comments),
        "actionable_count": sum(
            1 for c in outside_diff_comments if c["has_actionable_content"]
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch CodeRabbit outside-diff comments"
    )
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (default)")

    args = parser.parse_args()

    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    try:
        data = fetch_outside_diff_comments(pr_number)

        if "error" in data and data["error"]:
            eprint(f"ERROR: {data['error']}")
            sys.exit(1)

        output_json(data, pretty=True)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
