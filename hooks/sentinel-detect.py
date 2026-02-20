#!/usr/bin/env python3
"""
Sentinel Auto-Detection Hook - Diff-Scoped Emerging Issue Scanner

Scans files after Write/Edit operations for patterns that indicate
emerging issues. Only scans CHANGED lines (diff-scoped) to avoid
flagging pre-existing issues in touched files.

Scoping model:
  - Edit: diffs old_string vs new_string (no subprocess, pure Python)
  - Write on new file: scans everything (you wrote it all)
  - Write on git-tracked file: diffs against git HEAD (one subprocess)
  - Fallback: full file scan if diff cannot be computed

Hook Event: PostToolUse
Trigger: After Write or Edit tool use on scannable file types
Scope: Changed lines in the specific file (diff-scoped)
Mode: Warn-only (non-blocking, appends to .sentinel/auto-detected.md)

Related:
  - hooks/lib/sentinel_patterns.py - Pattern definitions
  - agents/sentinel.md - Consolidation agent
  - skills/sentinel/SKILL.md - /sentinel command
"""

import difflib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from safeguards import (
        guard_hook_execution,
        log_diagnostic,
        safe_subprocess_run,
    )
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return True
    def log_diagnostic(msg, **_): pass
    def safe_subprocess_run(cmd, **kw):
        import subprocess
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=kw.get('timeout', 10), cwd=kw.get('cwd'),
            )
            return r.returncode == 0, r.stdout, r.stderr
        except Exception:
            return False, None, None

try:
    from sentinel_patterns import (
        scan_file_content,
        format_finding_md,
        should_skip_file,
        is_scannable,
    )
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False

try:
    from reasoning import classify_reasoning, read_agent_context, apply_context_to_findings
    REASONING_AVAILABLE = True
except ImportError:
    REASONING_AVAILABLE = False


# ============================================================================
# DIFF-SCOPING FUNCTIONS
# ============================================================================

def compute_changed_lines(old_text: str, new_text: str) -> Set[int]:
    """Compute which line numbers in new_text are new or modified.

    Uses difflib.SequenceMatcher to compare old and new content and
    returns the 1-based line numbers of added or replaced lines.

    Args:
        old_text: The previous version of the content.
        new_text: The current version of the content.

    Returns:
        Set of 1-based line numbers in new_text that are new or changed.
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    changed = set()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            for idx in range(j1, j2):
                changed.add(idx + 1)  # 1-based line numbers

    return changed


def get_changed_lines_for_edit(hook_input: dict) -> Optional[Set[int]]:
    """Determine changed line numbers for an Edit operation.

    Diffs old_string vs new_string to find which lines were actually
    changed, then locates new_string within the full file to compute
    correct file-level line numbers.

    Args:
        hook_input: The hook input dict containing tool_input with
            old_string, new_string, and file_path.

    Returns:
        Set of 1-based file line numbers that changed, or None if
        the diff cannot be computed (falls back to full scan).
    """
    tool_input = hook_input.get("tool_input", {})
    old_string = tool_input.get("old_string")
    new_string = tool_input.get("new_string")
    file_path = tool_input.get("file_path", "")

    if old_string is None or new_string is None:
        return None

    # Diff old vs new to find changed line indices within the replacement
    old_lines = old_string.splitlines()
    new_lines = new_string.splitlines()

    changed_within_new = set()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            for idx in range(j1, j2):
                changed_within_new.add(idx)  # 0-based within new_string

    if not changed_within_new:
        return set()  # No lines changed — nothing to scan

    # Read the full file to find where new_string starts
    if not file_path or not Path(file_path).exists():
        return None

    try:
        full_content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except (IOError, OSError):
        return None

    full_lines = full_content.splitlines()

    # Find the starting line offset of new_string in the full file
    offset = _find_block_offset(full_lines, new_lines)
    if offset is None:
        return None  # Can't locate new_string — fall back to full scan

    # Convert to file-level 1-based line numbers
    return {offset + idx + 1 for idx in changed_within_new}


def get_changed_lines_for_write(
    filepath: str,
    new_content: str,
    cwd: str,
) -> Optional[Set[int]]:
    """Determine changed line numbers for a Write operation.

    Compares the new content against the git HEAD version of the file.
    If the file is new (not in git), returns None to indicate a full
    scan is appropriate.

    Args:
        filepath: Absolute path to the written file.
        new_content: The content that was written.
        cwd: The project working directory.

    Returns:
        Set of 1-based line numbers that are new/changed, or None if
        the file is new or git comparison failed (full scan fallback).
    """
    try:
        rel_path = os.path.relpath(filepath, cwd)
    except ValueError:
        return None

    # Get the committed version from git HEAD
    success, old_content, _stderr = safe_subprocess_run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=cwd,
        timeout=5,
        tool_name="git",
    )

    if not success or old_content is None:
        return None  # New file or git error — scan everything

    return compute_changed_lines(old_content, new_content)


def _find_block_offset(full_lines: list, block_lines: list) -> Optional[int]:
    """Find the starting line index of a block within the full file.

    Args:
        full_lines: All lines in the file.
        block_lines: The block of lines to locate.

    Returns:
        The 0-based starting index, or None if the block is not found.
    """
    if not block_lines:
        return None

    block_len = len(block_lines)
    first_line = block_lines[0]

    for i in range(len(full_lines) - block_len + 1):
        if full_lines[i] == first_line:
            if full_lines[i:i + block_len] == block_lines:
                return i

    return None


# ============================================================================
# FILE CONTENT AND PATH HELPERS
# ============================================================================

def get_sentinel_dir(cwd: str) -> Path:
    """Get or create the .sentinel directory in the project root.

    Args:
        cwd: The project working directory.

    Returns:
        Path to the .sentinel directory (created if it did not exist).
    """
    sentinel_dir = Path(cwd) / ".sentinel"
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    return sentinel_dir


def get_file_content(hook_input: dict) -> Optional[str]:
    """Extract or read the file content that was just written or edited.

    For Write operations the content is available in tool_input.content.
    For Edit operations the file is read from disk after modification.

    Args:
        hook_input: The hook input dict from stdin with tool_name and tool_input.

    Returns:
        The file content as a string, or None if content is unavailable.
    """
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "Write":
        return tool_input.get("content")

    elif tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        if file_path and Path(file_path).exists():
            try:
                return Path(file_path).read_text(encoding="utf-8", errors="replace")
            except (IOError, OSError):
                return None

    return None


def get_file_path(hook_input: dict) -> Optional[str]:
    """Extract the file path from hook input.

    Args:
        hook_input: The hook input dict from stdin with tool_input.

    Returns:
        The file_path string from tool_input, or None if not present.
    """
    tool_input = hook_input.get("tool_input", {})
    return tool_input.get("file_path")


# ============================================================================
# FINDINGS PERSISTENCE
# ============================================================================

def append_findings(
    sentinel_dir: Path,
    filepath: str,
    findings: list,
    scope_label: str,
) -> list:
    """Append new findings to .sentinel/auto-detected.md with deduplication.

    Reads the existing file to check for already-recorded findings by
    exact file:line key match, then appends only new ones.

    Args:
        sentinel_dir: Path to the .sentinel directory.
        filepath: The source file that was scanned.
        findings: List of finding dicts from scan_file_content().
        scope_label: Scope description for the header (e.g., "diff-scoped",
            "new file", "full scan").

    Returns:
        List of newly appended findings (empty if all were duplicates).
    """
    auto_file = sentinel_dir / "auto-detected.md"

    # Read existing content for deduplication
    existing_content = ""
    if auto_file.exists():
        try:
            existing_content = auto_file.read_text(encoding="utf-8")
        except (IOError, OSError):
            existing_content = ""

    # Filter out findings already recorded (match exact backtick-wrapped file:line)
    new_findings = []
    for finding in findings:
        key = f"`{finding['file']}:{finding['line']}`"
        if key not in existing_content:
            new_findings.append(finding)

    if not new_findings:
        return []

    # Build the entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    # Add header if file is new or empty
    if not existing_content.strip():
        lines.append("# Sentinel Auto-Detected Issues\n")
        lines.append("_Auto-generated by sentinel-detect.py hook. Do not edit manually._\n")
        lines.append("_Consolidated by the sentinel agent at end-of-cycle._\n")
        lines.append("")

    lines.append(f"### {timestamp} | Scan: `{filepath}` ({scope_label})")
    lines.append("")

    for finding in new_findings:
        lines.append(format_finding_md(finding))

    lines.append("")

    # Append to file
    try:
        with open(auto_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return new_findings
    except (IOError, OSError) as e:
        log_diagnostic(f"Failed to write sentinel findings: {e}")
        return []


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Hook entry point."""
    try:
        # SAFEGUARD: Check if hooks should run
        if not guard_hook_execution():
            print(json.dumps({}))
            sys.exit(0)

        # Check if patterns library is available
        if not PATTERNS_AVAILABLE:
            log_diagnostic("sentinel_patterns not available, skipping detection")
            print(json.dumps({}))
            sys.exit(0)

        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")
        cwd = hook_input.get("cwd", os.getcwd())

        # Only process Write and Edit
        if tool_name not in ("Write", "Edit"):
            print(json.dumps({}))
            sys.exit(0)

        # Get the file path
        filepath = get_file_path(hook_input)
        if not filepath:
            print(json.dumps({}))
            sys.exit(0)

        # Check if file should be scanned
        if should_skip_file(filepath) or not is_scannable(filepath):
            log_diagnostic(f"Sentinel skipping non-scannable: {filepath}")
            print(json.dumps({}))
            sys.exit(0)

        # Get file content
        content = get_file_content(hook_input)
        if not content:
            print(json.dumps({}))
            sys.exit(0)

        # Determine diff scope based on tool type
        changed_lines = None
        scope_label = "full scan"

        if tool_name == "Edit":
            changed_lines = get_changed_lines_for_edit(hook_input)
            if changed_lines is not None:
                scope_label = "diff-scoped"
                if not changed_lines:
                    # Edit didn't change any scannable content
                    print(json.dumps({}))
                    sys.exit(0)

        elif tool_name == "Write":
            changed_lines = get_changed_lines_for_write(filepath, content, cwd)
            if changed_lines is not None:
                scope_label = "diff-scoped"
                if not changed_lines:
                    # Write didn't change any lines vs HEAD
                    print(json.dumps({}))
                    sys.exit(0)
            else:
                scope_label = "new file"

        # Scan for patterns (diff-scoped if changed_lines available)
        findings = scan_file_content(filepath, content, changed_lines=changed_lines)

        if not findings:
            print(json.dumps({}))
            sys.exit(0)

        # Apply reasoning context to findings (suppress acknowledged / escalate uncontextualized)
        if REASONING_AVAILABLE:
            last_msg = hook_input.get("last_assistant_message", "")
            classification = classify_reasoning(last_msg)
            agent_context = read_agent_context(cwd)
            active, suppressed, escalated = apply_context_to_findings(
                findings, classification, agent_context
            )
        else:
            active, suppressed, escalated = findings, [], []

        # If all findings suppressed by context, exit quietly
        if not active:
            if suppressed:
                log_diagnostic(
                    f"[sentinel] {len(suppressed)} finding(s) suppressed by context "
                    f"in {Path(filepath).name}"
                )
            print(json.dumps({}))
            sys.exit(0)

        # Get sentinel directory
        sentinel_dir = get_sentinel_dir(cwd)

        # Append active findings (with dedup)
        new_findings = append_findings(sentinel_dir, filepath, active, scope_label)

        if new_findings:
            new_count = len(new_findings)
            # Build summary for hook output (from deduped new findings only)
            critical = sum(1 for f in new_findings if f["severity"] == "critical")
            important = sum(1 for f in new_findings if f["severity"] == "important")

            parts = []
            if critical:
                parts.append(f"{critical} critical")
            if important:
                parts.append(f"{important} important")
            if not parts:
                parts.append(f"{new_count} minor")

            severity_summary = ", ".join(parts)

            # Annotate with context notes (suppression, escalation)
            context_notes = []
            if suppressed:
                context_notes.append(f"{len(suppressed)} suppressed")
            if escalated:
                context_notes.append(f"{len(escalated)} escalated")
            context_str = f" [{', '.join(context_notes)}]" if context_notes else ""

            escalation_line = ""
            if escalated:
                escalation_line = (
                    "\n[sentinel] !! ESCALATED: critical finding(s) with no context — review needed"
                )

            message = (
                f"{escalation_line}\n[sentinel] {new_count} emerging issue(s) detected "
                f"({severity_summary}) in {Path(filepath).name} [{scope_label}]{context_str}\n"
                f"  Run /sentinel report for details\n"
            )

            response = {"hookSpecificOutput": {"message": message}}
        else:
            response = {}

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, allow operation but log
        log_diagnostic(f"Sentinel detect hook error: {e}", error=str(e))
        error_response = {
            "hookSpecificOutput": {
                "message": f"[sentinel] Detection hook error: {e}\n"
            }
        }
        print(json.dumps(error_response))
        sys.exit(0)


if __name__ == "__main__":
    main()
