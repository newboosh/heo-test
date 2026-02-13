#!/usr/bin/env python3
"""Track branches owned by this worktree for CodeRabbit loop scoping.

A worktree "owns" branches that:
1. Match its primary branch (from git worktree list)
2. Were explicitly pushed from this worktree and registered

Usage:
    python3 scripts/coderabbit/loop/branch_tracker.py list
    python3 scripts/coderabbit/loop/branch_tracker.py register BRANCH_NAME
    python3 scripts/coderabbit/loop/branch_tracker.py unregister BRANCH_NAME
    python3 scripts/coderabbit/loop/branch_tracker.py is-owned BRANCH_NAME
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.config import BRANCH_TRACKER_FILE
from coderabbit.utils import eprint, get_repo_root


def get_worktree_branch() -> str | None:
    """Get the branch associated with the current worktree."""
    try:
        # Get current working directory's worktree info
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        cwd = str(Path.cwd().resolve())
        lines = result.stdout.strip().split("\n")

        current_worktree = None
        for i, line in enumerate(lines):
            if line.startswith("worktree "):
                worktree_path = line[9:]
                if Path(worktree_path).resolve() == Path(cwd).resolve():
                    # Found our worktree, look for branch in next lines
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].startswith("branch "):
                            return lines[j][7:].replace("refs/heads/", "")
                        if lines[j] == "" or lines[j].startswith("worktree "):
                            break

        # Fallback: get current branch directly
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None

    except subprocess.CalledProcessError:
        return None


def get_worktree_prefix() -> str | None:
    """Extract the numeric prefix from the current worktree branch.

    Supports delimiters: '--' (preferred) or '---' (legacy)
    Examples: '05--feature' -> '05--', '05---legacy' -> '05---'
    """
    branch = get_worktree_branch()
    if not branch:
        return None

    # Try 3-dash first (longer pattern), then 2-dash
    # Must check longer pattern first since '--' is substring of '---'
    for delimiter in ("---", "--"):
        if delimiter in branch:
            prefix_end = branch.index(delimiter) + len(delimiter)
            prefix = branch[:prefix_end]
            # Validate it starts with digits
            numeric_part = prefix.rstrip("-")
            if numeric_part.isdigit():
                return prefix

    return None


def get_tracker_path() -> Path:
    """Get path to branch tracker file."""
    return get_repo_root() / BRANCH_TRACKER_FILE


def load_tracker() -> dict:
    """Load branch tracker data with graceful error handling."""
    path = get_tracker_path()
    default = {
        "version": 1,
        "worktree_branch": get_worktree_branch(),
        "additional_branches": [],
    }
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            # Corrupted or unreadable file - warn and use default
            import sys
            print(f"Warning: Could not load {path}: {e}", file=sys.stderr)
            return default
    return default


def save_tracker(data: dict):
    """Save branch tracker data."""
    path = get_tracker_path()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_owned_branches() -> list[str]:
    """Get all branches owned by this worktree."""
    tracker = load_tracker()
    branches = []

    # Primary worktree branch
    worktree_branch = get_worktree_branch()
    if worktree_branch:
        branches.append(worktree_branch)

    # Additional registered branches
    for entry in tracker.get("additional_branches", []):
        branch = entry if isinstance(entry, str) else entry.get("branch")
        if branch and branch not in branches:
            branches.append(branch)

    return branches


def is_owned_branch(branch: str) -> bool:
    """Check if a branch is owned by this worktree."""
    owned = get_owned_branches()

    # Direct match
    if branch in owned:
        return True

    # Check if branch has same prefix as worktree
    prefix = get_worktree_prefix()
    if prefix and branch.startswith(prefix):
        return True

    return False


def register_branch(branch: str) -> bool:
    """Register a branch as owned by this worktree."""
    tracker = load_tracker()

    # Check if already registered
    existing = [
        e.get("branch") if isinstance(e, dict) else e
        for e in tracker.get("additional_branches", [])
    ]
    if branch in existing:
        print(f"Branch '{branch}' already registered")
        return True

    tracker.setdefault("additional_branches", []).append({
        "branch": branch,
        "registered_at": datetime.now().isoformat(),
    })
    save_tracker(tracker)
    print(f"Registered branch '{branch}'")
    return True


def unregister_branch(branch: str) -> bool:
    """Unregister a branch from this worktree."""
    tracker = load_tracker()

    original_count = len(tracker.get("additional_branches", []))
    tracker["additional_branches"] = [
        e for e in tracker.get("additional_branches", [])
        if (e.get("branch") if isinstance(e, dict) else e) != branch
    ]

    if len(tracker["additional_branches"]) < original_count:
        save_tracker(tracker)
        print(f"Unregistered branch '{branch}'")
        return True
    else:
        print(f"Branch '{branch}' was not registered")
        return False


def cmd_list(args):
    """List owned branches."""
    branches = get_owned_branches()
    primary = get_worktree_branch()

    print(f"Worktree: {Path.cwd().name}")
    print(f"Primary branch: {primary}")
    print(f"\nOwned branches ({len(branches)}):")
    for branch in branches:
        marker = " (primary)" if branch == primary else ""
        print(f"  - {branch}{marker}")


def cmd_register(args):
    """Register a branch."""
    register_branch(args.branch)


def cmd_unregister(args):
    """Unregister a branch."""
    unregister_branch(args.branch)


def cmd_is_owned(args):
    """Check if branch is owned."""
    if is_owned_branch(args.branch):
        print(f"YES: '{args.branch}' is owned by this worktree")
        sys.exit(0)
    else:
        print(f"NO: '{args.branch}' is NOT owned by this worktree")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Track branches owned by this worktree")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    subparsers.add_parser("list", help="List owned branches")

    # register command
    reg_parser = subparsers.add_parser("register", help="Register a branch")
    reg_parser.add_argument("branch", help="Branch name to register")

    # unregister command
    unreg_parser = subparsers.add_parser("unregister", help="Unregister a branch")
    unreg_parser.add_argument("branch", help="Branch name to unregister")

    # is-owned command
    owned_parser = subparsers.add_parser("is-owned", help="Check if branch is owned")
    owned_parser.add_argument("branch", help="Branch name to check")

    args = parser.parse_args()

    try:
        if args.command == "list":
            cmd_list(args)
        elif args.command == "register":
            cmd_register(args)
        elif args.command == "unregister":
            cmd_unregister(args)
        elif args.command == "is-owned":
            cmd_is_owned(args)
    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
