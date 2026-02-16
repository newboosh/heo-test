#!/usr/bin/env python3
"""CodeRabbit Loop Orchestrator.

Processes CodeRabbit review comments on PRs owned by this worktree.

Usage:
    python3 scripts/coderabbit/loop/orchestrator.py [--status] [--pr PR] [--all]

The orchestrator:
1. Identifies PRs from branches owned by this worktree
2. Checks each PR for CodeRabbit comments
3. Outputs structured data for Claude Code to process
4. Handles merge conflicts intelligently
5. Tracks iterations and respects rate limits

Note: This script does NOT apply fixes - it provides structured output
for Claude Code to understand what needs to be fixed. Claude Code
applies fixes and calls back into the loop.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import with error handling to provide helpful messages
_import_errors = []

try:
    from coderabbit.check_pr_status import get_pr_status
except ImportError as e:
    _import_errors.append(f"check_pr_status: {e}")
    get_pr_status = None

try:
    from coderabbit.config import (
        CODERABBIT_WAIT_MINUTES,
        MAX_ITERATIONS,
        POLL_INTERVAL_SECONDS,
        RATE_LIMIT_THRESHOLD,
    )
except ImportError as e:
    _import_errors.append(f"config: {e}")
    MAX_ITERATIONS = 8
    POLL_INTERVAL_SECONDS = 30
    CODERABBIT_WAIT_MINUTES = 5
    RATE_LIMIT_THRESHOLD = 500

try:
    from coderabbit.loop.branch_tracker import get_owned_branches, is_owned_branch
except ImportError as e:
    _import_errors.append(f"branch_tracker: {e}")
    get_owned_branches = None
    is_owned_branch = None

try:
    from coderabbit.loop.check_cr_response import check_cr_response
except ImportError as e:
    _import_errors.append(f"check_cr_response: {e}")
    check_cr_response = None

try:
    from coderabbit.loop.check_exit_signals import check_exit_signals
except ImportError as e:
    _import_errors.append(f"check_exit_signals: {e}")
    check_exit_signals = None

try:
    from coderabbit.loop.check_rate_limits import get_rate_limits
except ImportError as e:
    _import_errors.append(f"check_rate_limits: {e}")
    get_rate_limits = None

try:
    from coderabbit.loop.conflict_resolver import check_has_conflicts, resolve_conflicts
except ImportError as e:
    _import_errors.append(f"conflict_resolver: {e}")
    check_has_conflicts = None
    resolve_conflicts = None

try:
    from coderabbit.loop.fetch_comments import fetch_comments
except ImportError as e:
    _import_errors.append(f"fetch_comments: {e}")
    fetch_comments = None

try:
    from coderabbit.loop.post_audit_log import post_audit_log
except ImportError as e:
    _import_errors.append(f"post_audit_log: {e}")
    post_audit_log = None

try:
    from coderabbit.loop.post_final_summary import post_final_summary
except ImportError as e:
    _import_errors.append(f"post_final_summary: {e}")
    post_final_summary = None

try:
    from coderabbit.utils import eprint, get_pr_for_branch, get_repo_info, run_gh_command
except ImportError as e:
    _import_errors.append(f"utils: {e}")
    eprint = lambda *args, **kwargs: print(*args, file=sys.stderr, **kwargs)
    get_pr_for_branch = None
    get_repo_info = None
    run_gh_command = None


def _check_imports():
    """Verify all required imports are available."""
    if _import_errors:
        eprint("Import errors detected:")
        for err in _import_errors:
            eprint(f"  - {err}")
        eprint("\nEnsure all coderabbit modules are properly installed.")
        return False
    return True


class LoopState(str, Enum):
    """State of the CodeRabbit loop."""
    READY = "ready"           # Ready to process
    FIXING = "fixing"         # Waiting for Claude Code to apply fixes
    WAITING = "waiting"       # Waiting for CodeRabbit response
    CONFLICTS = "conflicts"   # Has merge conflicts to resolve
    CLEAN = "clean"           # PR is clean, awaiting CodeRabbit merge
    MERGED = "merged"         # PR has been merged - SUCCESS EXIT
    CLOSED = "closed"         # PR was closed without merge
    MAX_ITER = "max_iter"     # Reached max iterations
    STOPPED = "stopped"       # User requested stop
    RATE_LIMIT = "rate_limit" # Rate limited
    ERROR = "error"           # Error occurred


@dataclass
class PRState:
    """State of a single PR in the loop."""
    pr_number: int
    branch: str
    state: LoopState
    iteration: int
    comments: list[dict]
    general_comments: list[dict]
    has_conflicts: bool
    conflict_resolution: dict | None
    last_cr_response: str | None  # approved, rejected, pending
    error: str | None

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "branch": self.branch,
            "state": self.state.value,
            "iteration": self.iteration,
            "comments": self.comments,
            "general_comments": self.general_comments,
            "has_conflicts": self.has_conflicts,
            "conflict_resolution": self.conflict_resolution,
            "last_cr_response": self.last_cr_response,
            "error": self.error,
        }


@dataclass
class LoopOutput:
    """Structured output from the orchestrator for Claude Code."""
    timestamp: str
    worktree_branches: list[str]
    prs: list[PRState]
    rate_limits: dict
    exit_signal: dict | None
    next_action: str
    message: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "worktree_branches": self.worktree_branches,
            "prs": [pr.to_dict() for pr in self.prs],
            "rate_limits": self.rate_limits,
            "exit_signal": self.exit_signal,
            "next_action": self.next_action,
            "message": self.message,
        }


def get_prs_for_branches(branches: list[str]) -> list[tuple[str, int]]:
    """Get PR numbers for branches that have open PRs."""
    prs = []
    for branch in branches:
        result = run_gh_command(
            ["pr", "list", "--head", branch, "--state", "open", "--json", "number"],
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                pr_list = json.loads(result.stdout)
                for pr in pr_list:
                    prs.append((branch, pr["number"]))
            except json.JSONDecodeError:
                pass
    return prs


def process_pr(pr_number: int, branch: str, iteration: int) -> PRState:
    """Process a single PR and return its state."""
    try:
        # Get PR status
        status = get_pr_status(pr_number)

        if "error" in status:
            return PRState(
                pr_number=pr_number,
                branch=branch,
                state=LoopState.ERROR,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=False,
                conflict_resolution=None,
                last_cr_response=None,
                error=status["error"],
            )

        # Check if PR is merged - this is the SUCCESS exit condition
        pr_state = status.get("pr_state", "").upper()
        if pr_state == "MERGED":
            return PRState(
                pr_number=pr_number,
                branch=branch,
                state=LoopState.MERGED,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=False,
                conflict_resolution=None,
                last_cr_response="approved",
                error=None,
            )

        # Check if PR was closed without merge
        if pr_state == "CLOSED":
            return PRState(
                pr_number=pr_number,
                branch=branch,
                state=LoopState.CLOSED,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=False,
                conflict_resolution=None,
                last_cr_response=None,
                error="PR was closed without merging",
            )

        # Check for conflicts
        has_conflicts = status.get("has_conflicts", False)
        conflict_resolution = None

        if has_conflicts:
            # Try to resolve conflicts (dry run to see what can be resolved)
            conflict_resolution = resolve_conflicts(pr_number, dry_run=True)

            # Return CONFLICTS state whether or not they're auto-resolvable
            # Claude Code needs to apply the resolutions (or handle failures)
            return PRState(
                pr_number=pr_number,
                branch=branch,
                state=LoopState.CONFLICTS,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=True,
                conflict_resolution=conflict_resolution,
                last_cr_response=None,
                error="Merge conflicts require resolution" if conflict_resolution.get("failed", 0) > 0 else None,
            )

        # Check if CodeRabbit is still reviewing
        if status.get("coderabbit_reviewing"):
            return PRState(
                pr_number=pr_number,
                branch=branch,
                state=LoopState.WAITING,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=has_conflicts,
                conflict_resolution=conflict_resolution,
                last_cr_response="pending",
                error=None,
            )

        # Fetch comments if there are unresolved threads OR CodeRabbit feedback
        has_coderabbit_feedback = (
            status.get("coderabbit_inline_comments", 0) > 0 or
            status.get("coderabbit_general_comments", 0) > 0
        )
        if status.get("unresolved_threads", 0) > 0 or has_coderabbit_feedback:
            comment_data = fetch_comments(pr_number)

            comments = comment_data.get("comments", [])
            general_comments = comment_data.get("general_comments", [])

            if comments or general_comments:
                return PRState(
                    pr_number=pr_number,
                    branch=branch,
                    state=LoopState.FIXING,
                    iteration=iteration,
                    comments=comments,
                    general_comments=general_comments,
                    has_conflicts=has_conflicts,
                    conflict_resolution=conflict_resolution,
                    last_cr_response=None,
                    error=None,
                )

        # No issues - PR is clean, waiting for CodeRabbit to merge
        return PRState(
            pr_number=pr_number,
            branch=branch,
            state=LoopState.CLEAN,
            iteration=iteration,
            comments=[],
            general_comments=[],
            has_conflicts=False,
            conflict_resolution=None,
            last_cr_response="approved",
            error=None,
        )

    except Exception as e:
        return PRState(
            pr_number=pr_number,
            branch=branch,
            state=LoopState.ERROR,
            iteration=iteration,
            comments=[],
            general_comments=[],
            has_conflicts=False,
            conflict_resolution=None,
            last_cr_response=None,
            error=str(e),
        )


def determine_next_action(pr_states: list[PRState]) -> tuple[str, str]:
    """Determine what action Claude Code should take next."""
    # Priority order: merged (done), closed, errors, conflicts, fixing, waiting, clean (await merge)

    # Check if all PRs are merged - SUCCESS!
    merged = [pr for pr in pr_states if pr.state == LoopState.MERGED]
    non_merged = [pr for pr in pr_states if pr.state != LoopState.MERGED]
    if merged and not non_merged:
        if len(merged) == 1:
            return "done", f"PR #{merged[0].pr_number} has been merged by CodeRabbit!"
        return "done", f"All {len(merged)} PRs have been merged by CodeRabbit!"

    # Check for closed PRs (not merged)
    closed = [pr for pr in pr_states if pr.state == LoopState.CLOSED]
    if closed:
        return "closed", f"PR #{closed[0].pr_number} was closed without merging"

    errors = [pr for pr in pr_states if pr.state == LoopState.ERROR]
    if errors:
        return "investigate_error", f"Error in PR #{errors[0].pr_number}: {errors[0].error}"

    conflicts = [pr for pr in pr_states if pr.state == LoopState.CONFLICTS]
    if conflicts:
        return "resolve_conflicts", f"PR #{conflicts[0].pr_number} has merge conflicts"

    fixing = [pr for pr in pr_states if pr.state == LoopState.FIXING]
    if fixing:
        pr = fixing[0]
        total_comments = len(pr.comments) + len(pr.general_comments)
        return "apply_fixes", f"PR #{pr.pr_number} has {total_comments} CodeRabbit comment(s) to address"

    waiting = [pr for pr in pr_states if pr.state == LoopState.WAITING]
    if waiting:
        return "wait", f"Waiting for CodeRabbit to review PR #{waiting[0].pr_number}"

    max_iter = [pr for pr in pr_states if pr.state == LoopState.MAX_ITER]
    if max_iter:
        return "escalate", f"PR #{max_iter[0].pr_number} reached max iterations"

    # PRs are clean but not yet merged - wait for CodeRabbit to merge
    clean = [pr for pr in pr_states if pr.state == LoopState.CLEAN]
    if clean:
        return "await_merge", f"PR #{clean[0].pr_number} is clean, waiting for CodeRabbit to merge"

    # Fallback (shouldn't reach here)
    return "unknown", "Unknown state"


def run_loop(
    pr_number: int | None = None,
    process_all: bool = False,
    status_only: bool = False,
    iteration: int = 1,
) -> LoopOutput:
    """Run the orchestrator loop.

    Args:
        pr_number: Specific PR to process (default: current branch's PR)
        process_all: Process all PRs from owned branches
        status_only: Only return status, skip rate limit/exit signal checks
        iteration: Current iteration number for loop tracking
    """
    timestamp = datetime.now().isoformat()

    # Get owned branches
    owned_branches = get_owned_branches()

    # Check rate limits (skip if status_only)
    rate_limits = get_rate_limits()
    if not status_only and rate_limits["github_remaining"] < RATE_LIMIT_THRESHOLD:
        return LoopOutput(
            timestamp=timestamp,
            worktree_branches=owned_branches,
            prs=[],
            rate_limits=rate_limits,
            exit_signal=None,
            next_action="pause",
            message=f"Rate limit low ({rate_limits['github_remaining']} remaining). Pause recommended.",
        )

    # Check for exit signals (skip if status_only)
    exit_signal = None
    if not status_only:
        if pr_number:
            try:
                exit_signal = check_exit_signals(pr_number)
            except ValueError:
                pass  # PR not found, continue
        else:
            # Check all owned PRs for exit signals
            for branch in owned_branches:
                branch_pr = get_pr_for_branch(branch)
                if branch_pr:
                    try:
                        signal = check_exit_signals(branch_pr)
                        if signal:
                            exit_signal = signal
                            break
                    except ValueError:
                        pass  # PR not found, continue

    if exit_signal:
        return LoopOutput(
            timestamp=timestamp,
            worktree_branches=owned_branches,
            prs=[],
            rate_limits=rate_limits,
            exit_signal=exit_signal,
            next_action="stop",
            message=f"Exit signal received: @claude-code {exit_signal['signal']}",
        )

    # Determine which PRs to process
    if pr_number:
        prs_to_process = [(None, pr_number)]  # Branch unknown, but PR specified
    elif process_all:
        prs_to_process = get_prs_for_branches(owned_branches)
    else:
        # Default: just the current branch's PR
        current_pr = get_pr_for_branch()
        if current_pr:
            prs_to_process = [(owned_branches[0] if owned_branches else None, current_pr)]
        else:
            prs_to_process = []

    if not prs_to_process:
        return LoopOutput(
            timestamp=timestamp,
            worktree_branches=owned_branches,
            prs=[],
            rate_limits=rate_limits,
            exit_signal=None,
            next_action="none",
            message="No open PRs found for owned branches",
        )

    # Process each PR
    pr_states = []
    for branch, pr_num in prs_to_process:
        # Check iteration limit
        if iteration > MAX_ITERATIONS:
            pr_states.append(PRState(
                pr_number=pr_num,
                branch=branch or "unknown",
                state=LoopState.MAX_ITER,
                iteration=iteration,
                comments=[],
                general_comments=[],
                has_conflicts=False,
                conflict_resolution=None,
                last_cr_response=None,
                error=f"Reached max iterations ({MAX_ITERATIONS})",
            ))
        else:
            state = process_pr(pr_num, branch or "unknown", iteration)
            pr_states.append(state)

    # Determine next action
    next_action, message = determine_next_action(pr_states)

    return LoopOutput(
        timestamp=timestamp,
        worktree_branches=owned_branches,
        prs=pr_states,
        rate_limits=rate_limits,
        exit_signal=None,
        next_action=next_action,
        message=message,
    )


def print_status(output: LoopOutput):
    """Print human-readable status."""
    print(f"\n{'=' * 60}")
    print("CodeRabbit Loop Status")
    print(f"{'=' * 60}")
    print(f"Timestamp: {output.timestamp}")
    print(f"Owned branches: {', '.join(output.worktree_branches)}")
    print(f"\nRate limits: {output.rate_limits['github_remaining']} remaining")

    if output.exit_signal:
        print(f"\nEXIT SIGNAL: @claude-code {output.exit_signal['signal']}")

    print(f"\nPRs ({len(output.prs)}):")
    for pr in output.prs:
        state_icon = {
            LoopState.MERGED: "[MERGED]",
            LoopState.CLEAN: "[CLEAN]",
            LoopState.CLOSED: "[CLOSED]",
            LoopState.FIXING: "[FIX]",
            LoopState.WAITING: "[WAIT]",
            LoopState.CONFLICTS: "[CONFLICT]",
            LoopState.ERROR: "[ERR]",
            LoopState.MAX_ITER: "[MAX]",
        }.get(pr.state, "[?]")

        print(f"\n  {state_icon} PR #{pr.pr_number} ({pr.branch})")
        print(f"      State: {pr.state.value}")
        print(f"      Iteration: {pr.iteration}/{MAX_ITERATIONS}")

        if pr.comments:
            print(f"      Inline comments: {len(pr.comments)}")
        if pr.general_comments:
            print(f"      General comments: {len(pr.general_comments)}")
        if pr.has_conflicts:
            print(f"      Has merge conflicts!")
        if pr.error:
            print(f"      Error: {pr.error}")

    print(f"\n{'=' * 60}")
    print(f"Next action: {output.next_action}")
    print(f"Message: {output.message}")
    print(f"{'=' * 60}\n")


def main():
    # Check imports before doing anything
    if not _check_imports():
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="CodeRabbit Loop Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status              Show status of all owned PRs
  %(prog)s --pr 123              Process specific PR
  %(prog)s --all                 Process all PRs from owned branches
  %(prog)s --json                Output as JSON for Claude Code
  %(prog)s --iteration 3         Set current iteration number
        """,
    )
    parser.add_argument("--pr", type=int, help="Specific PR number to process")
    parser.add_argument("--all", action="store_true", help="Process all PRs from owned branches")
    parser.add_argument("--status", action="store_true", help="Show status only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--iteration", type=int, default=1, help="Current iteration number")

    args = parser.parse_args()

    try:
        output = run_loop(
            pr_number=args.pr,
            process_all=args.all,
            status_only=args.status,
            iteration=args.iteration,
        )

        if args.json:
            print(json.dumps(output.to_dict(), indent=2))
        else:
            print_status(output)

        # Exit codes based on next action
        exit_codes = {
            "done": 0,             # PR merged - success!
            "apply_fixes": 10,     # Fixes needed
            "resolve_conflicts": 11,  # Conflicts need resolution
            "wait": 12,            # Waiting for CodeRabbit review
            "await_merge": 13,     # Clean, waiting for CodeRabbit to merge
            "pause": 14,           # Rate limited
            "stop": 15,            # Exit signal
            "escalate": 16,        # Max iterations
            "investigate_error": 17,  # Error occurred
            "closed": 18,          # PR closed without merge
            "none": 0,
            "unknown": 1,
        }
        sys.exit(exit_codes.get(output.next_action, 1))

    except Exception as e:
        eprint(f"ERROR: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
