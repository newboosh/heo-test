#!/usr/bin/env python3
"""Track CodeRabbit comments for pattern analysis.

Usage:
    python3 scripts/coderabbit/loop/comment_tracker.py record --pr PR --thread-id ID --file FILE --line LINE --rule RULE --severity SEV --body BODY
    python3 scripts/coderabbit/loop/comment_tracker.py increment --pr PR
    python3 scripts/coderabbit/loop/comment_tracker.py check
    python3 scripts/coderabbit/loop/comment_tracker.py analyze
    python3 scripts/coderabbit/loop/comment_tracker.py suggest
    python3 scripts/coderabbit/loop/comment_tracker.py reset

The tracker stores data in .coderabbit-tracker.json in the repo root.
Pattern analysis runs every 12 PRs to identify recurring issues.
"""

import argparse
import fcntl
import json
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import eprint, get_repo_root

TRACKER_FILE = ".coderabbit-tracker.json"
ANALYSIS_INTERVAL = 12  # Run analysis every N PRs
MAX_STORED_COMMENTS = 500  # Prevent unbounded growth


@contextmanager
def file_lock(path: Path, exclusive: bool = True):
    """Context manager for file locking to prevent race conditions."""
    lock_path = path.with_suffix(".lock")
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def get_tracker_path() -> Path:
    """Get path to tracker file."""
    return get_repo_root() / TRACKER_FILE


def _default_tracker() -> dict:
    """Return default tracker structure."""
    return {
        "version": 1,
        "pr_count": 0,
        "last_analysis": None,
        "comments": [],
    }


def load_tracker() -> dict:
    """Load tracker data from file (for read-only access)."""
    path = get_tracker_path()
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return _default_tracker()
    return _default_tracker()


def save_tracker(data: dict):
    """Save tracker data to file with size limits."""
    path = get_tracker_path()

    # Enforce size limit on stored comments
    if len(data.get("comments", [])) > MAX_STORED_COMMENTS:
        # Keep most recent comments
        data["comments"] = data["comments"][-MAX_STORED_COMMENTS:]

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@contextmanager
def update_tracker():
    """Context manager for atomic read-modify-write operations.

    Usage:
        with update_tracker() as tracker:
            tracker["pr_count"] += 1
            # Changes are automatically saved on exit
    """
    path = get_tracker_path()

    with file_lock(path, exclusive=True):
        # Load current data
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = _default_tracker()
        else:
            data = _default_tracker()

        # Yield for modification
        yield data

        # Enforce size limit
        if len(data.get("comments", [])) > MAX_STORED_COMMENTS:
            data["comments"] = data["comments"][-MAX_STORED_COMMENTS:]

        # Save atomically
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def cmd_record(args):
    """Record a comment for tracking."""
    with update_tracker() as tracker:
        comment = {
            "pr": args.pr,
            "thread_id": args.thread_id,
            "file": args.file,
            "line": args.line,
            "rule": args.rule,
            "severity": args.severity,
            "body_preview": args.body[:200] if args.body else "",
            "timestamp": datetime.now().isoformat(),
        }
        tracker["comments"].append(comment)
    print(f"Recorded comment for PR #{args.pr}")


def cmd_increment(args):
    """Increment PR counter."""
    with update_tracker() as tracker:
        tracker["pr_count"] = tracker.get("pr_count", 0) + 1
        pr_count = tracker["pr_count"]
    print(f"PR count: {pr_count}")


def cmd_check(args):
    """Check if analysis is due."""
    tracker = load_tracker()
    pr_count = tracker.get("pr_count", 0)

    if pr_count >= ANALYSIS_INTERVAL:
        print(f"Analysis due (processed {pr_count} PRs)")
        sys.exit(0)  # Exit 0 = analysis due
    else:
        print(f"Analysis not due yet ({pr_count}/{ANALYSIS_INTERVAL} PRs)")
        sys.exit(1)  # Exit 1 = not due


def cmd_analyze(args):
    """Analyze patterns in recorded comments."""
    tracker = load_tracker()
    comments = tracker.get("comments", [])

    if not comments:
        print("No comments recorded for analysis")
        return

    # Analyze patterns
    analysis = {
        "total_comments": len(comments),
        "by_rule": Counter(),
        "by_file": Counter(),
        "by_severity": Counter(),
        "by_pr": Counter(),
    }

    for comment in comments:
        if comment.get("rule"):
            analysis["by_rule"][f"Rule #{comment['rule']}"] += 1
        if comment.get("file"):
            analysis["by_file"][comment["file"]] += 1
        if comment.get("severity"):
            analysis["by_severity"][comment["severity"]] += 1
        if comment.get("pr"):
            analysis["by_pr"][f"PR #{comment['pr']}"] += 1

    # Print analysis
    print("=" * 60)
    print("CodeRabbit Comment Pattern Analysis")
    print("=" * 60)
    print(f"\nTotal comments analyzed: {analysis['total_comments']}")

    if analysis["by_rule"]:
        print("\nMost violated rules:")
        for rule, count in analysis["by_rule"].most_common(5):
            print(f"  {rule}: {count} violations")

    if analysis["by_file"]:
        print("\nFiles with most comments:")
        for file, count in analysis["by_file"].most_common(5):
            print(f"  {file}: {count} comments")

    if analysis["by_severity"]:
        print("\nBy severity:")
        for severity, count in analysis["by_severity"].most_common():
            print(f"  {severity}: {count}")

    # Store analysis result
    tracker["last_analysis"] = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": analysis["total_comments"],
            "top_rules": dict(analysis["by_rule"].most_common(5)),
            "top_files": dict(analysis["by_file"].most_common(5)),
        },
    }
    save_tracker(tracker)


def cmd_suggest(args):
    """Suggest improvements based on patterns."""
    tracker = load_tracker()
    comments = tracker.get("comments", [])

    if not comments:
        print("No patterns to analyze")
        return

    suggestions = []

    # Analyze rule violations
    rule_counts = Counter(c.get("rule") for c in comments if c.get("rule"))
    for rule, count in rule_counts.most_common(3):
        if count >= 3:
            suggestions.append({
                "type": "recurring_rule",
                "rule": rule,
                "count": count,
                "suggestion": f"Rule #{rule} violated {count} times. Consider adding a pre-commit hook or linter rule to catch this automatically.",
            })

    # Analyze file hotspots
    file_counts = Counter(c.get("file") for c in comments if c.get("file"))
    for file, count in file_counts.most_common(3):
        if count >= 3:
            suggestions.append({
                "type": "file_hotspot",
                "file": file,
                "count": count,
                "suggestion": f"'{file}' has {count} comments. Consider refactoring this file or adding file-specific linting rules.",
            })

    # Print suggestions
    if suggestions:
        print("\n" + "=" * 60)
        print("Suggested Improvements")
        print("=" * 60)
        for i, s in enumerate(suggestions, 1):
            print(f"\n{i}. {s['suggestion']}")
    else:
        print("No specific improvements suggested based on current patterns.")

    # Reset counter after analysis
    tracker["pr_count"] = 0
    tracker["comments"] = []  # Clear old comments after analysis
    save_tracker(tracker)
    print("\nTracker reset for next analysis cycle.")


def cmd_reset(args):
    """Reset the tracker."""
    save_tracker({
        "version": 1,
        "pr_count": 0,
        "last_analysis": None,
        "comments": [],
    })
    print("Tracker reset")


def main():
    parser = argparse.ArgumentParser(description="Track CodeRabbit comments for pattern analysis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # record command
    record_parser = subparsers.add_parser("record", help="Record a comment")
    record_parser.add_argument("--pr", type=int, required=True)
    record_parser.add_argument("--thread-id", required=True)
    record_parser.add_argument("--file", default="")
    record_parser.add_argument("--line", type=int, default=0)
    record_parser.add_argument("--rule", type=int, default=0)
    record_parser.add_argument("--severity", default="minor")
    record_parser.add_argument("--body", default="")

    # increment command
    increment_parser = subparsers.add_parser("increment", help="Increment PR counter")
    increment_parser.add_argument("--pr", type=int, required=True)

    # check command
    subparsers.add_parser("check", help="Check if analysis is due")

    # analyze command
    subparsers.add_parser("analyze", help="Analyze patterns")

    # suggest command
    subparsers.add_parser("suggest", help="Suggest improvements")

    # reset command
    subparsers.add_parser("reset", help="Reset tracker")

    args = parser.parse_args()

    try:
        if args.command == "record":
            cmd_record(args)
        elif args.command == "increment":
            cmd_increment(args)
        elif args.command == "check":
            cmd_check(args)
        elif args.command == "analyze":
            cmd_analyze(args)
        elif args.command == "suggest":
            cmd_suggest(args)
        elif args.command == "reset":
            cmd_reset(args)
    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
