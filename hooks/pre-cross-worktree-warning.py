#!/usr/bin/env python3
"""
Cross-worktree file access warning for Claude Code PreToolUse hook.

Warns when an agent in one worktree attempts to edit a file that lives
in a different worktree directory. Non-blocking — injects a warning into
the model's context window via additionalContext so it can reconsider.

Exit codes:
  0 = Allow (always - this hook only warns, never blocks)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))

from fallbacks import import_hook_utils
graceful_hook, read_hook_input, HookResult, _, _ = import_hook_utils()


def find_workspace_root(start: Path):
    """Walk up from start until we find a directory containing .trees/."""
    current = start.resolve()
    while True:
        if (current / ".trees").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def get_other_worktrees(trees_dir: Path, current_wt: Path):
    """List worktree directories under trees_dir that are not the current one."""
    result = []
    if not trees_dir.is_dir():
        return result
    current_resolved = current_wt.resolve()
    for entry in trees_dir.iterdir():
        if not entry.is_dir():
            continue
        # Skip internal directories (.build-history, .completed, .incomplete, etc.)
        if entry.name.startswith("."):
            continue
        if entry.resolve() != current_resolved:
            result.append(entry.resolve())
    return result


@graceful_hook(blocking=False, name="cross-worktree-warning")
def main():
    input_data = read_hook_input()
    result = HookResult()

    # Get file path from tool input (Edit, Write, or NotebookEdit)
    tool_input = input_data.get("tool_input", {})
    file_path_str = tool_input.get("file_path") or tool_input.get("notebook_path", "")
    if not file_path_str:
        result.exit()

    # Resolve the file path (may be relative)
    file_path = Path(file_path_str)
    if not file_path.is_absolute():
        file_path = Path(os.getcwd()) / file_path
    file_path = file_path.resolve()

    # Determine current worktree from Claude Code environment
    project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir_str:
        result.exit()

    current_wt = Path(project_dir_str).resolve()

    # Find workspace root (directory containing .trees/)
    workspace_root = find_workspace_root(current_wt)
    if not workspace_root:
        result.exit()  # Not in a trees-based worktree setup

    trees_dir = workspace_root / ".trees"

    # Get other worktrees to compare against
    other_worktrees = get_other_worktrees(trees_dir, current_wt)
    if not other_worktrees:
        result.exit()

    # Check if the file being edited lives inside a different worktree
    for wt_path in other_worktrees:
        try:
            file_path.relative_to(wt_path)
        except ValueError:
            continue  # File is not inside this worktree

        # File IS inside another worktree — warn the agent
        wt_name = wt_path.name
        current_name = current_wt.name

        context = (
            f"⚠️  Cross-worktree file access detected!\n\n"
            f"You are running in worktree '{current_name}' but the file you are about to edit "
            f"belongs to a different worktree '{wt_name}':\n"
            f"  {file_path}\n\n"
            f"Each worktree is an isolated environment checked out on its own branch. "
            f"Editing files inside another worktree's directory modifies that branch's "
            f"working tree, not your current one — this can corrupt the other agent's work "
            f"or cause unexpected merge conflicts.\n\n"
            f"Your current worktree root is:\n"
            f"  {current_wt}/\n\n"
            f"If you intended to edit a file in your own worktree, use a path relative "
            f"to your worktree root. If this cross-worktree edit is intentional and you "
            f"understand the implications, you may proceed."
        )
        result.add_context(context)
        print(
            f"[heo] WARNING: Cross-worktree edit — '{current_name}' attempting to modify '{wt_name}/{file_path.relative_to(wt_path)}'",
            file=sys.stderr,
        )
        result.exit()

    result.exit()


if __name__ == "__main__":
    main()
