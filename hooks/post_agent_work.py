#!/usr/bin/env python3
"""
Post-Agent-Work Hook - Automatic Quality Validation

This hook runs automatically after the agent completes significant work.
It performs quick validation on changed files to catch issues early.

Hook Event: PostToolUse (after substantial agent activity)
Trigger: After agent changes >= threshold (files/lines/time)
Scope: Files changed in current session
Mode: Warn-only (non-blocking)

Configuration: .claude/settings.local.json
  hooks.post_agent_work.enabled
  hooks.post_agent_work.threshold
  hooks.post_agent_work.validation

Related:
  - docs/development/quality-validation-coordination.md
  - tools/librarian_validate.py
  - .claude/commands/lint.md
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from safeguards import (
        guard_hook_execution,
        safe_subprocess_run,
        limit_files,
        is_tool_available,
        log_diagnostic,
        MAX_FILES_PER_OPERATION,
    )
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return True
    def safe_subprocess_run(cmd, **kw):
        import subprocess
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=kw.get('timeout', 10), cwd=kw.get('cwd'))
        return r.returncode == 0, r.stdout, r.stderr
    def limit_files(files, max_files=20): return files[:max_files]
    def is_tool_available(name): return True
    def log_diagnostic(msg, **_): pass
    MAX_FILES_PER_OPERATION = 20


class ValidationConfig:
    """Validation configuration from settings"""

    def __init__(self, settings: Dict):
        hook_config = settings.get("hooks", {}).get("post_agent_work", {})

        self.enabled = hook_config.get("enabled", True)

        threshold = hook_config.get("threshold", {})
        self.threshold_files = threshold.get("files_changed", 3)
        self.threshold_lines = threshold.get("lines_changed", 50)
        self.threshold_minutes = threshold.get("session_minutes", 10)

        validation = hook_config.get("validation", {})
        self.mode = validation.get("mode", "warn_only")
        self.show_details = validation.get("show_details", "on_failure")
        self.timeout = validation.get("timeout_seconds", 10)


def load_settings() -> Dict:
    """Load validation configuration"""
    try:
        # Try validation-config.json first (preferred)
        config_path = Path.cwd() / ".claude" / "validation-config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)

        # Fallback to settings.local.json
        settings_path = Path.cwd() / ".claude" / "settings.local.json"
        if settings_path.exists():
            with open(settings_path, "r") as f:
                settings = json.load(f)
                # Look for validation_config key
                if "validation_config" in settings:
                    return settings["validation_config"]
                return settings
    except Exception as e:
        print(f"⚠️ Could not load settings: {e}", file=sys.stderr)

    return {}


def get_changed_files(cwd: str) -> Tuple[List[str], List[str]]:
    """
    Get files changed in recent agent activity.

    Returns:
        Tuple of (py_files, md_files)
    """
    try:
        # Check if git is available first (no subprocess)
        if not is_tool_available("git"):
            log_diagnostic("git not available, skipping file detection")
            return [], []

        # Get recently changed files (last 15 minutes)
        success, stdout, stderr = safe_subprocess_run(
            ["git", "diff", "--name-only", "HEAD@{15 minutes ago}", "HEAD"],
            cwd=cwd,
            timeout=5,
            tool_name="git",
        )

        if not success or not stdout:
            # Fallback: use unstaged changes
            success, stdout, stderr = safe_subprocess_run(
                ["git", "diff", "--name-only"],
                cwd=cwd,
                timeout=5,
                tool_name="git",
            )

        if not stdout:
            return [], []

        all_files = [f.strip() for f in stdout.split("\n") if f.strip()]

        # Apply file limits to prevent overload
        all_files = limit_files(all_files, MAX_FILES_PER_OPERATION)

        py_files = [f for f in all_files if f.endswith(".py")]
        md_files = [f for f in all_files if f.endswith(".md")]

        log_diagnostic(
            f"Found {len(py_files)} Python and {len(md_files)} markdown files",
            py_count=len(py_files),
            md_count=len(md_files)
        )

        return py_files, md_files

    except Exception as e:
        print(f"⚠️ Error detecting changed files: {e}", file=sys.stderr)
        log_diagnostic(f"Error detecting files: {e}", error=str(e))
        return [], []


def should_run_validation(tool_name: str, settings: Dict, cwd: str) -> Tuple[bool, str]:
    """
    Determine if validation should run based on activity threshold.

    Returns:
        Tuple of (should_run, reason)
    """
    config = ValidationConfig(settings)

    if not config.enabled:
        return False, "Hook disabled in settings"

    # Only run after certain high-impact tools
    high_impact_tools = ["Edit", "Write", "Task"]
    if tool_name not in high_impact_tools:
        return False, f"Tool {tool_name} not high-impact"

    # Check file change threshold
    py_files, md_files = get_changed_files(cwd)
    total_files = len(py_files) + len(md_files)

    if total_files >= config.threshold_files:
        return (
            True,
            f"{total_files} files changed (threshold: {config.threshold_files})",
        )

    return (
        False,
        f"Only {total_files} files changed (threshold: {config.threshold_files})",
    )


def validate_python_files(py_files: List[str], cwd: str, timeout: int) -> Dict:
    """Run Black formatting check on Python files"""
    if not py_files:
        return {"status": "skipped", "reason": "no Python files"}

    # Check tool availability BEFORE spawning subprocess
    if not is_tool_available("black"):
        log_diagnostic("black not available, skipping Python validation")
        return {
            "status": "skipped",
            "reason": "Black not installed",
            "files": len(py_files),
        }

    # Limit files to prevent overload
    py_files = limit_files(py_files)

    try:
        success, stdout, stderr = safe_subprocess_run(
            ["black", "--check", "--quiet"] + py_files,
            cwd=cwd,
            timeout=timeout,
            tool_name="black",
        )

        if stderr and "blocked" in stderr.lower():
            # Safeguard blocked the call
            return {
                "status": "skipped",
                "reason": stderr,
                "files": len(py_files),
            }

        if success:
            return {
                "status": "pass",
                "files": len(py_files),
                "message": f"✅ {len(py_files)} Python file(s) formatted correctly",
            }
        else:
            # Count files needing formatting
            needs_formatting = (stdout or "").count("would reformat")
            return {
                "status": "warning",
                "files": len(py_files),
                "issues": needs_formatting,
                "message": f"⚠️  {needs_formatting} Python file(s) need formatting",
                "details": f"Run: black {' '.join(py_files[:5])}{'...' if len(py_files) > 5 else ''}",
            }

    except Exception as e:
        log_diagnostic(f"Black validation error: {e}", error=str(e))
        return {
            "status": "error",
            "message": f"⚠️ Black validation error: {e}",
            "files": len(py_files),
        }


def validate_markdown_files(md_files: List[str], cwd: str, timeout: int) -> Dict:
    """Run librarian metadata validation on markdown files"""
    if not md_files:
        return {"status": "skipped", "reason": "no markdown files"}

    # Check if librarian tool exists BEFORE spawning subprocess
    validator_path = Path(cwd) / "tools" / "librarian_validate.py"
    if not validator_path.exists():
        log_diagnostic("librarian_validate.py not found, skipping markdown validation")
        return {
            "status": "skipped",
            "reason": "librarian_validate.py not found",
            "files": len(md_files),
        }

    # Check python availability
    if not is_tool_available("python"):
        return {
            "status": "skipped",
            "reason": "Python not available",
            "files": len(md_files),
        }

    # Limit files to prevent overload
    md_files = limit_files(md_files)

    try:
        # Run validation on specific files
        success, stdout, stderr = safe_subprocess_run(
            ["python", str(validator_path), "--errors-only"] + md_files,
            cwd=cwd,
            timeout=timeout,
            tool_name="python",
        )

        if stderr and "blocked" in stderr.lower():
            return {
                "status": "skipped",
                "reason": stderr,
                "files": len(md_files),
            }

        # Parse output for errors
        output = (stdout or "") + (stderr or "")

        if "Error" in output or "FAILED" in output:
            error_count = output.count("Error:")
            return {
                "status": "warning",
                "files": len(md_files),
                "issues": error_count,
                "message": f"⚠️  {error_count} metadata issue(s) found",
                "details": output[:200] + "..." if len(output) > 200 else output,
            }
        else:
            return {
                "status": "pass",
                "files": len(md_files),
                "message": f"✅ {len(md_files)} markdown file(s) validated",
            }

    except Exception as e:
        log_diagnostic(f"Librarian validation error: {e}", error=str(e))
        return {
            "status": "error",
            "message": f"⚠️ Librarian validation error: {e}",
            "files": len(md_files),
        }


def format_validation_report(
    py_result: Dict, md_result: Dict, show_details: str
) -> str:
    """Format validation results as user-friendly report"""
    lines = []
    lines.append("\n🔍 Quick validation complete:")
    lines.append("")

    # Python validation results
    if py_result["status"] == "pass":
        lines.append(f"  {py_result['message']}")
    elif py_result["status"] == "warning":
        lines.append(f"  {py_result['message']}")
        if show_details in ["always", "on_failure"]:
            lines.append(f"     {py_result.get('details', '')}")
    elif py_result["status"] == "skipped":
        pass  # Don't show skipped
    elif py_result["status"] == "error":
        lines.append(f"  {py_result['message']}")

    # Markdown validation results
    if md_result["status"] == "pass":
        lines.append(f"  {md_result['message']}")
    elif md_result["status"] == "warning":
        lines.append(f"  {md_result['message']}")
        if show_details in ["always", "on_failure"]:
            lines.append(f"     {md_result.get('details', '')}")
    elif md_result["status"] == "skipped":
        pass  # Don't show skipped
    elif md_result["status"] == "error":
        lines.append(f"  {md_result['message']}")

    # Summary
    has_warnings = py_result["status"] == "warning" or md_result["status"] == "warning"
    has_errors = py_result["status"] == "error" or md_result["status"] == "error"

    lines.append("")
    if has_errors:
        lines.append("⚠️  Validation encountered errors (non-blocking)")
    elif has_warnings:
        lines.append("💡 Consider fixing issues before committing")
    else:
        lines.append("✅ All checks passed!")

    return "\n".join(lines)


def main():
    """Hook entry point"""
    try:
        # SAFEGUARD: Check if hooks should run at all
        if not guard_hook_execution():
            print(json.dumps({}))
            sys.exit(0)

        log_diagnostic("post_agent_work hook started")

        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")
        cwd = hook_input.get("cwd", os.getcwd())

        # Load settings
        settings = load_settings()

        # Check if validation should run
        should_run, reason = should_run_validation(tool_name, settings, cwd)

        if not should_run:
            # Skip validation - no output
            log_diagnostic(f"Validation skipped: {reason}")
            print(json.dumps({}))
            sys.exit(0)

        # Get configuration
        config = ValidationConfig(settings)

        # Get changed files
        py_files, md_files = get_changed_files(cwd)

        if not py_files and not md_files:
            # No files to validate
            print(json.dumps({}))
            sys.exit(0)

        # Run validation
        py_result = validate_python_files(py_files, cwd, config.timeout)
        md_result = validate_markdown_files(md_files, cwd, config.timeout)

        # Format report
        report = format_validation_report(py_result, md_result, config.show_details)

        # Return results
        response = {"hookSpecificOutput": {"message": report}}

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, allow operation but log
        error_response = {
            "hookSpecificOutput": {
                "message": f"⚠️ Post-agent-work validation hook error: {e}\n(Validation skipped)"
            }
        }
        print(json.dumps(error_response))
        sys.exit(0)


if __name__ == "__main__":
    main()
