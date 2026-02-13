#!/usr/bin/env python3
"""Smart resolver for CodeRabbit PR comments.

This script analyzes CodeRabbit comments and can auto-resolve non-security issues
after fixes have been applied.

Usage:
    python3 scripts/coderabbit/smart_resolver.py --pr PR_NUMBER [--dry-run] [--verbose] [--force-resolve]

Options:
    --dry-run        Show what would be resolved without making changes
    --verbose        Show detailed information about each comment
    --force-resolve  Resolve even security comments (use with caution)
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
    output_json,
)

# Keywords that indicate security-related comments
SECURITY_KEYWORDS = [
    "security",
    "vulnerability",
    "injection",
    "xss",
    "csrf",
    "authentication",
    "authorization",
    "password",
    "secret",
    "credential",
    "token",
    "sanitize",
    "escape",
    "sql injection",
    "command injection",
    "path traversal",
    "unsafe",
    "exploit",
]


def is_security_comment(body: str) -> bool:
    """Check if a comment is security-related."""
    body_lower = body.lower()
    return any(keyword in body_lower for keyword in SECURITY_KEYWORDS)


def get_unresolved_threads(pr_number: int) -> list[dict]:
    """Get all unresolved review threads from a PR."""
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
              comments(first: 10) {
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
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})
    pr_data = result["data"]["repository"]["pullRequest"]

    if not pr_data:
        return []

    threads = []
    for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
        if thread.get("isResolved"):
            continue

        comments = thread.get("comments", {}).get("nodes", [])
        coderabbit_comment = None
        for comment in comments:
            author = comment.get("author", {}).get("login", "")
            if author.lower() in ["coderabbitai", "coderabbit"]:
                coderabbit_comment = comment
                break

        if coderabbit_comment:
            threads.append({
                "thread_id": thread["id"],
                "file": thread.get("path"),
                "line": thread.get("line"),
                "is_outdated": thread.get("isOutdated", False),
                "body": coderabbit_comment["body"],
                "is_security": is_security_comment(coderabbit_comment["body"]),
            })

    return threads


def resolve_thread(thread_id: str) -> bool:
    """Resolve a review thread."""
    mutation = """
    mutation($threadId: ID!) {
      resolveReviewThread(input: {threadId: $threadId}) {
        thread {
          id
          isResolved
        }
      }
    }
    """

    try:
        result = gh_api_graphql(mutation, {"threadId": thread_id})
        resolved = result.get("data", {}).get("resolveReviewThread", {}).get("thread", {}).get("isResolved")
        return resolved is True
    except Exception as e:
        eprint(f"Failed to resolve thread: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Smart resolver for CodeRabbit comments")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be resolved")
    parser.add_argument("--verbose", action="store_true", help="Show detailed comment info")
    parser.add_argument("--force-resolve", action="store_true", help="Resolve even security comments")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    try:
        threads = get_unresolved_threads(pr_number)

        if not threads:
            print("No unresolved CodeRabbit comments found")
            sys.exit(0)

        # Categorize threads
        security_threads = [t for t in threads if t["is_security"]]
        safe_threads = [t for t in threads if not t["is_security"]]

        if args.json:
            output_json({
                "pr_number": pr_number,
                "total_unresolved": len(threads),
                "security_comments": len(security_threads),
                "safe_comments": len(safe_threads),
                "threads": threads,
            }, pretty=True)
            sys.exit(0)

        print(f"PR #{pr_number}: {len(threads)} unresolved CodeRabbit comments")
        print(f"  Security-related: {len(security_threads)}")
        print(f"  Safe to auto-resolve: {len(safe_threads)}")
        print()

        if args.verbose:
            for thread in threads:
                security_marker = " [SECURITY]" if thread["is_security"] else ""
                outdated_marker = " [OUTDATED]" if thread["is_outdated"] else ""
                print(f"- {thread['file']}:{thread['line']}{security_marker}{outdated_marker}")
                # Show first 100 chars of body
                preview = thread["body"][:100].replace("\n", " ")
                print(f"  {preview}...")
                print()

        if args.dry_run:
            print("DRY RUN - No changes made")
            print(f"Would resolve {len(safe_threads)} non-security threads")
            if security_threads and not args.force_resolve:
                print(f"Would SKIP {len(security_threads)} security threads (use --force-resolve to include)")
            sys.exit(0)

        # Resolve threads
        threads_to_resolve = safe_threads
        if args.force_resolve:
            threads_to_resolve = threads
            if security_threads:
                print("WARNING: Force-resolving security comments!")

        resolved_count = 0
        failed_count = 0

        for thread in threads_to_resolve:
            print(f"Resolving {thread['file']}:{thread['line']}...", end=" ")
            if resolve_thread(thread["thread_id"]):
                print("OK")
                resolved_count += 1
            else:
                print("FAILED")
                failed_count += 1

        print()
        print(f"Resolved: {resolved_count}")
        if failed_count:
            print(f"Failed: {failed_count}")
        if security_threads and not args.force_resolve:
            print(f"Skipped (security): {len(security_threads)}")

        sys.exit(0 if failed_count == 0 else 1)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
