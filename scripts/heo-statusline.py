#!/usr/bin/env python3
"""heo plugin statusline for Claude Code.

Reads JSON session data from stdin, outputs a two-line status bar:
  Line 1: [Model] dir (worktree) | branch +staged ~modified
  Line 2: context-bar pct% | $cost | duration | +added/-removed
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

# --- ANSI colors ---
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"

# Balances freshness vs. subprocess overhead (statusline refreshes every ~1-2s)
CACHE_MAX_AGE = 5
GIT_TIMEOUT = 3


def _cache_path(project_dir):
    """Per-user, per-project cache file in temp directory."""
    uid = os.getuid()
    project_hash = hashlib.sha256(project_dir.encode()).hexdigest()[:12]
    return os.path.join(tempfile.gettempdir(), f"heo-sl-{uid}-{project_hash}")


def read_stdin():
    """Read JSON session data from stdin. Returns empty dict on bad input."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def git_info(project_dir):
    """Get git branch, staged, modified counts. Cached to avoid lag."""
    cache_file = _cache_path(project_dir)

    cache_stale = True
    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        cache_stale = age > CACHE_MAX_AGE

    if cache_stale:
        try:
            # Single git call: branch + staged + modified
            output = subprocess.check_output(
                ["git", "status", "--porcelain", "-b"],
                cwd=project_dir,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=GIT_TIMEOUT,
            )
            lines = output.strip().split("\n") if output.strip() else []

            # Line 1: ## branch...tracking or ## HEAD (no branch)
            branch = "detached"
            if lines and lines[0].startswith("## "):
                branch_line = lines[0][3:]
                # Strip tracking info: "main...origin/main" -> "main"
                branch = branch_line.split("...")[0].strip()
                if branch == "HEAD (no branch)":
                    branch = "detached"

            # Remaining lines: XY filename
            staged_count = 0
            modified_count = 0
            for line in lines[1:]:
                if len(line) < 2:
                    continue
                x, y = line[0], line[1]
                if x in "MADRCT":
                    staged_count += 1
                if y in "MADRCT":
                    modified_count += 1

            # Detect worktree name from heo task context
            # Only .claude-task-context.md is authoritative (created by /tree)
            worktree_name = ""
            task_ctx = os.path.join(project_dir, ".claude-task-context.md")
            if os.path.exists(task_ctx):
                try:
                    with open(task_ctx, encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("- **Name**:"):
                                worktree_name = line.split(":", 1)[1].strip()
                                break
                except OSError:
                    pass

            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(f"{branch}\t{staged_count}\t{modified_count}\t{worktree_name}")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write("\t\t\t")

    try:
        with open(cache_file, encoding="utf-8") as f:
            parts = f.read().strip().split("\t")
        if len(parts) == 4:
            return parts[0], int(parts[1] or 0), int(parts[2] or 0), parts[3]
    except (OSError, ValueError):
        pass
    return "", 0, 0, ""


def context_bar(pct):
    """Build a 10-char progress bar with threshold colors."""
    pct = max(0, min(100, pct))

    if pct >= 90:
        color = RED
    elif pct >= 70:
        color = YELLOW
    else:
        color = GREEN

    bar_width = 10
    filled = pct * bar_width // 100
    empty = bar_width - filled
    bar = "\u2588" * filled + "\u2591" * empty
    return f"{color}{bar}{RESET} {pct}%"


def format_duration(ms):
    """Convert milliseconds to Xm Ys."""
    if not ms or ms < 0:
        return "0m 0s"
    total_sec = int(ms) // 1000
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins}m {secs}s"


def main():
    data = read_stdin()
    if not data:
        print("[heo] waiting...")
        return

    # Model
    model = data.get("model", {}).get("display_name", "?")

    # Directory
    workspace = data.get("workspace", {})
    current_dir = workspace.get("current_dir", data.get("cwd", ""))
    project_dir = workspace.get("project_dir", current_dir)
    dir_name = os.path.basename(current_dir) if current_dir else "?"

    # Git info (cached)
    branch, staged, modified, worktree = git_info(project_dir or current_dir)

    # Cost & context — LBYL for non-numeric JSON values
    cost_data = data.get("cost", {})
    raw_cost = cost_data.get("total_cost_usd")
    cost_usd = float(raw_cost) if isinstance(raw_cost, (int, float)) else 0.0
    raw_duration = cost_data.get("total_duration_ms")
    duration_ms = int(raw_duration) if isinstance(raw_duration, (int, float)) else 0
    ctx = data.get("context_window", {})
    raw_pct = ctx.get("used_percentage")
    pct = int(raw_pct) if isinstance(raw_pct, (int, float)) else 0

    # --- Line 1: [Model] dir (worktree) | branch +staged ~modified ---
    line1_parts = [f"{CYAN}[{model}]{RESET}"]

    if worktree:
        line1_parts.append(f"{dir_name} ({DIM}{worktree}{RESET})")
    else:
        line1_parts.append(dir_name)

    if branch:
        git_part = f"| {branch}"
        if staged > 0:
            git_part += f" {GREEN}+{staged}{RESET}"
        if modified > 0:
            git_part += f" {YELLOW}~{modified}{RESET}"
        line1_parts.append(git_part)

    print(" ".join(line1_parts))

    # --- Line 2: context-bar | $cost | duration | +lines/-lines ---
    line2_parts = [context_bar(pct)]
    line2_parts.append(f"{YELLOW}${cost_usd:.2f}{RESET}")
    line2_parts.append(format_duration(duration_ms))

    lines_added = cost_data.get("total_lines_added") or 0
    lines_removed = cost_data.get("total_lines_removed") or 0
    if lines_added or lines_removed:
        line2_parts.append(
            f"{GREEN}+{lines_added}{RESET}/{RED}-{lines_removed}{RESET}"
        )

    print(" | ".join(line2_parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("[heo] statusline error")
