#!/usr/bin/env python3
"""Intelligent merge conflict resolution for CodeRabbit loop.

Strategy:
1. Prioritize current branch changes
2. Analyze context of both versions
3. Include both if complementary
4. Flag as potential error source
5. Cite sources of competing changes

Usage:
    python3 scripts/coderabbit/loop/conflict_resolver.py --pr PR_NUMBER [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.config import CONFLICT_AUTO_RESOLVE_FILES, CONFLICT_STRATEGY
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
    run_gh_command,
)


@dataclass
class ConflictInfo:
    """Information about a merge conflict."""
    file_path: str
    ours_content: str
    theirs_content: str
    base_content: str | None
    ours_commit: str
    theirs_commit: str
    conflict_markers: list[tuple[int, int]]  # (start_line, end_line)


@dataclass
class ResolutionResult:
    """Result of a conflict resolution attempt."""
    file_path: str
    success: bool
    strategy_used: str
    resolved_content: str | None
    error: str | None
    needs_review: bool
    citation: str


def get_pr_base_branch(pr_number: int) -> str:
    """Get the base branch of a PR."""
    owner, repo = get_repo_info()

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          baseRefName
          headRefName
        }
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})
    pr_data = result["data"]["repository"]["pullRequest"]
    return pr_data["baseRefName"]


def check_has_conflicts(pr_number: int) -> bool:
    """Check if a PR has merge conflicts."""
    owner, repo = get_repo_info()

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          mergeable
        }
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})
    mergeable = result["data"]["repository"]["pullRequest"]["mergeable"]
    return mergeable == "CONFLICTING"


def get_conflicting_files() -> list[str]:
    """Get list of files with merge conflicts in current working tree."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return []


def get_conflict_details(file_path: str) -> ConflictInfo | None:
    """Get detailed information about conflicts in a file."""
    try:
        # Read current file with conflict markers
        with open(file_path) as f:
            content = f.read()

        # Find conflict markers (handles multi-line conflicts)
        conflict_pattern = re.compile(
            r"<<<<<<< ([^\n]*)\n(.*?)=======\n(.*?)>>>>>>> ([^\n]*)\n",
            re.DOTALL
        )

        markers = []
        for match in conflict_pattern.finditer(content):
            start = content[:match.start()].count("\n") + 1
            end = content[:match.end()].count("\n")
            markers.append((start, end))

        if not markers:
            return None

        # Get ours version
        result_ours = subprocess.run(
            ["git", "show", f":2:{file_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        ours_content = result_ours.stdout if result_ours.returncode == 0 else ""

        # Get theirs version
        result_theirs = subprocess.run(
            ["git", "show", f":3:{file_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        theirs_content = result_theirs.stdout if result_theirs.returncode == 0 else ""

        # Get base version
        result_base = subprocess.run(
            ["git", "show", f":1:{file_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        base_content = result_base.stdout if result_base.returncode == 0 else None

        # Get commit info
        result_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        ours_commit = result_head.stdout.strip()[:8]

        result_merge = subprocess.run(
            ["git", "rev-parse", "MERGE_HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        theirs_commit = result_merge.stdout.strip()[:8] if result_merge.returncode == 0 else "unknown"

        return ConflictInfo(
            file_path=file_path,
            ours_content=ours_content,
            theirs_content=theirs_content,
            base_content=base_content,
            ours_commit=ours_commit,
            theirs_commit=theirs_commit,
            conflict_markers=markers,
        )

    except Exception as e:
        eprint(f"Error analyzing conflict in {file_path}: {e}")
        return None


def is_auto_resolvable(file_path: str) -> bool:
    """Check if a file type can be auto-resolved."""
    file_name = Path(file_path).name
    return file_name in CONFLICT_AUTO_RESOLVE_FILES


def resolve_lock_file(conflict: ConflictInfo) -> ResolutionResult:
    """Resolve conflicts in lock files by regenerating."""
    # For lock files, we take ours and will regenerate after
    return ResolutionResult(
        file_path=conflict.file_path,
        success=True,
        strategy_used="regenerate",
        resolved_content=conflict.ours_content,
        error=None,
        needs_review=False,
        citation=f"Lock file conflict resolved by keeping current branch version. Regenerate with package manager.",
    )


def analyze_conflict_context(conflict: ConflictInfo) -> dict:
    """Analyze the semantic context of a conflict."""
    analysis = {
        "ours_adds_lines": 0,
        "ours_removes_lines": 0,
        "theirs_adds_lines": 0,
        "theirs_removes_lines": 0,
        "overlapping_changes": False,
        "complementary_changes": False,
    }

    if conflict.base_content:
        base_lines = set(conflict.base_content.split("\n"))
        ours_lines = set(conflict.ours_content.split("\n"))
        theirs_lines = set(conflict.theirs_content.split("\n"))

        analysis["ours_adds_lines"] = len(ours_lines - base_lines)
        analysis["ours_removes_lines"] = len(base_lines - ours_lines)
        analysis["theirs_adds_lines"] = len(theirs_lines - base_lines)
        analysis["theirs_removes_lines"] = len(base_lines - theirs_lines)

        # Check if changes are in same areas
        ours_changed = ours_lines.symmetric_difference(base_lines)
        theirs_changed = theirs_lines.symmetric_difference(base_lines)
        analysis["overlapping_changes"] = bool(ours_changed & theirs_changed)

        # Complementary if both add without removing same things
        ours_removes = base_lines - ours_lines
        theirs_removes = base_lines - theirs_lines
        if not (ours_removes & theirs_removes):
            analysis["complementary_changes"] = True

    return analysis


def resolve_with_current_priority(conflict: ConflictInfo) -> ResolutionResult:
    """Resolve conflict prioritizing current branch changes."""
    analysis = analyze_conflict_context(conflict)

    # If changes are complementary, try to include both
    if analysis["complementary_changes"] and not analysis["overlapping_changes"]:
        # Simple merge: take ours as base, add theirs additions
        if conflict.base_content:
            base_lines = conflict.base_content.split("\n")
            ours_lines = conflict.ours_content.split("\n")
            theirs_lines = conflict.theirs_content.split("\n")

            # Find lines theirs added that ours doesn't have
            theirs_additions = [
                line for line in theirs_lines
                if line not in base_lines and line not in ours_lines
            ]

            if theirs_additions:
                # Append theirs additions to ours
                resolved = conflict.ours_content.rstrip("\n")
                resolved += "\n" + "\n".join(theirs_additions) + "\n"

                return ResolutionResult(
                    file_path=conflict.file_path,
                    success=True,
                    strategy_used="include_both",
                    resolved_content=resolved,
                    error=None,
                    needs_review=True,
                    citation=(
                        f"Merged complementary changes from both branches.\n"
                        f"- Current branch ({conflict.ours_commit}): primary changes\n"
                        f"- Incoming branch ({conflict.theirs_commit}): {len(theirs_additions)} additional lines appended\n"
                        f"**FLAGGED FOR REVIEW**: Naive line-based merge used.\n"
                        f"Limitations: Lines appended at end regardless of context. "
                        f"Verify logical ordering and semantic correctness."
                    ),
                )

    # Default: prioritize current branch
    return ResolutionResult(
        file_path=conflict.file_path,
        success=True,
        strategy_used="current_priority",
        resolved_content=conflict.ours_content,
        error=None,
        needs_review=True,
        citation=(
            f"Conflict resolved by prioritizing current branch.\n"
            f"- Kept: Current branch ({conflict.ours_commit})\n"
            f"- Discarded: Incoming branch ({conflict.theirs_commit})\n"
            f"**FLAGGED FOR REVIEW**: Incoming changes were discarded.\n"
            f"This resolution may lose important changes from the incoming branch. "
            f"Review the diff to verify no critical changes were lost."
        ),
    )


def apply_resolution(result: ResolutionResult) -> bool:
    """Apply a resolution to a file and stage it."""
    if not result.success or result.resolved_content is None:
        return False

    try:
        with open(result.file_path, "w") as f:
            f.write(result.resolved_content)

        subprocess.run(
            ["git", "add", result.file_path],
            check=True,
        )
        return True
    except Exception as e:
        eprint(f"Failed to apply resolution for {result.file_path}: {e}")
        return False


def resolve_conflicts(pr_number: int, dry_run: bool = False) -> dict:
    """Attempt to resolve all conflicts for a PR."""
    results = {
        "pr_number": pr_number,
        "conflicts_found": 0,
        "resolved": 0,
        "failed": 0,
        "needs_review": [],
        "citations": [],
        "resolutions": [],
    }

    # First, try to merge the base branch
    base_branch = get_pr_base_branch(pr_number)

    # Fetch and attempt merge
    subprocess.run(["git", "fetch", "origin", base_branch], check=False)

    merge_result = subprocess.run(
        ["git", "merge", f"origin/{base_branch}", "--no-commit"],
        capture_output=True,
        text=True,
        check=False,
    )

    if merge_result.returncode == 0:
        # No conflicts
        subprocess.run(["git", "merge", "--abort"], check=False)
        results["message"] = "No merge conflicts detected"
        return results

    # Get conflicting files
    conflicting_files = get_conflicting_files()
    results["conflicts_found"] = len(conflicting_files)

    for file_path in conflicting_files:
        conflict = get_conflict_details(file_path)
        if not conflict:
            results["failed"] += 1
            continue

        # Choose resolution strategy
        if is_auto_resolvable(file_path):
            resolution = resolve_lock_file(conflict)
        elif CONFLICT_STRATEGY == "current_priority":
            resolution = resolve_with_current_priority(conflict)
        else:
            # Manual resolution needed
            resolution = ResolutionResult(
                file_path=file_path,
                success=False,
                strategy_used="manual",
                resolved_content=None,
                error="Manual resolution required",
                needs_review=True,
                citation=f"Conflict in {file_path} requires manual resolution.",
            )

        results["resolutions"].append({
            "file": resolution.file_path,
            "success": resolution.success,
            "strategy": resolution.strategy_used,
            "needs_review": resolution.needs_review,
        })
        results["citations"].append(resolution.citation)

        if resolution.needs_review:
            results["needs_review"].append(file_path)

        if resolution.success:
            if not dry_run:
                if apply_resolution(resolution):
                    results["resolved"] += 1
                else:
                    results["failed"] += 1
            else:
                results["resolved"] += 1
        else:
            results["failed"] += 1

    # Commit if we resolved anything and not dry run
    if not dry_run and results["resolved"] > 0:
        commit_msg = (
            f"Resolve merge conflicts with {base_branch}\n\n"
            f"Conflicts resolved: {results['resolved']}/{results['conflicts_found']}\n"
            f"Strategy: {CONFLICT_STRATEGY}\n\n"
            "**AUTOMATED MERGE - FLAGGED FOR REVIEW**\n\n"
            "This commit was created by the CodeRabbit loop to resolve merge conflicts.\n"
            "Please verify the resolutions are correct.\n\n"
            "Conflict citations:\n" + "\n".join(f"- {c}" for c in results["citations"])
        )

        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
            check=False,
        )

        if commit_result.returncode != 0:
            results["commit_failed"] = True
            results["commit_error"] = commit_result.stderr or commit_result.stdout
            results["failed"] += results["resolved"]  # All resolutions failed to commit
            results["resolved"] = 0
            eprint(f"Commit failed: {results['commit_error']}")
        else:
            results["commit_failed"] = False

    return results


def main():
    parser = argparse.ArgumentParser(description="Resolve merge conflicts for CodeRabbit loop")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be resolved")

    args = parser.parse_args()

    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    try:
        if not check_has_conflicts(pr_number):
            print(f"PR #{pr_number} has no merge conflicts")
            sys.exit(0)

        results = resolve_conflicts(pr_number, args.dry_run)

        print(f"\nConflict Resolution Results for PR #{pr_number}")
        print("=" * 50)
        print(f"Conflicts found: {results['conflicts_found']}")
        print(f"Resolved: {results['resolved']}")
        print(f"Failed: {results['failed']}")

        if results["needs_review"]:
            print(f"\nFiles needing review: {len(results['needs_review'])}")
            for f in results["needs_review"]:
                print(f"  - {f}")

        if results["citations"]:
            print("\nCitations:")
            for citation in results["citations"]:
                print(f"\n{citation}")

        if args.dry_run:
            print("\n[DRY RUN - No changes applied]")

        sys.exit(0 if results["failed"] == 0 else 1)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
