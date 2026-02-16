#!/usr/bin/env python3
"""
Post-Task Hook - Comprehensive Quality Validation

This hook runs automatically after /task command completes.
It performs comprehensive validation on all files changed during the task.

Hook Event: PostSlashCommand (after /task completion)
Trigger: After any /task command completes
Scope: All files changed during task execution
Mode: Comprehensive validation (more thorough than post-agent-work)

Configuration: .claude/settings.local.json
  hooks.post_task.enabled
  hooks.post_task.validation

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
        hook_config = settings.get("hooks", {}).get("post_task", {})

        self.enabled = hook_config.get("enabled", True)

        validation = hook_config.get("validation", {})
        self.mode = validation.get("mode", "strict")
        self.show_details = validation.get("show_details", "always")
        raw_timeout = validation.get("timeout_seconds", 60)
        try:
            timeout_val = int(float(raw_timeout))
        except (TypeError, ValueError):
            timeout_val = 60
        self.timeout = max(5, min(300, timeout_val))


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


def get_task_changed_files(cwd: str) -> Tuple[List[str], List[str]]:
    """
    Get all files changed during task execution.

    Looks for files changed since task started (approximation: last 30 minutes).

    Returns:
        Tuple of (py_files, md_files)
    """
    try:
        # Check if git is available first (no subprocess needed)
        if not is_tool_available("git"):
            log_diagnostic("git not available, skipping file detection")
            return [], []

        # Try to get files changed in current session
        success, stdout, stderr = safe_subprocess_run(
            ["git", "diff", "--name-only", "HEAD@{30 minutes ago}", "HEAD"],
            cwd=cwd,
            timeout=5,
            tool_name="git",
        )

        if not success or not stdout:
            # Fallback: use all uncommitted changes
            success, stdout, stderr = safe_subprocess_run(
                ["git", "diff", "--name-only", "HEAD"],
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
        print(f"⚠️ Error detecting task files: {e}", file=sys.stderr)
        log_diagnostic(f"Error detecting files: {e}", error=str(e))
        return [], []


def validate_python_comprehensive(py_files: List[str], cwd: str, timeout: int) -> Dict:
    """
    Run comprehensive Python validation: Black, Flake8, Vulture.

    Returns dict with status, results for each tool.
    """
    if not py_files:
        return {"status": "skipped", "reason": "no Python files"}

    # Limit files to prevent overload
    py_files = limit_files(py_files)

    results = {"black": None, "flake8": None, "vulture": None}

    # Black formatting check
    if is_tool_available("black"):
        try:
            success, stdout, stderr = safe_subprocess_run(
                ["black", "--check", "--diff"] + py_files,
                cwd=cwd,
                timeout=timeout // 3,
                tool_name="black",
            )

            if stderr and "blocked" in stderr.lower():
                results["black"] = {"status": "skipped", "message": stderr}
            elif success:
                results["black"] = {
                    "status": "pass",
                    "message": "✅ Black: All files formatted correctly",
                }
            else:
                needs_formatting = len([f for f in py_files if f in (stdout or "")])
                results["black"] = {
                    "status": "warning",
                    "message": f"⚠️  Black: {needs_formatting} file(s) need formatting",
                    "fix": f'black {" ".join(py_files[:5])}{"..." if len(py_files) > 5 else ""}',
                }
        except Exception as e:
            results["black"] = {"status": "error", "message": f"Black error: {e}"}
    else:
        results["black"] = {"status": "skipped", "message": "Black not installed"}

    # Flake8 linting
    if is_tool_available("flake8"):
        try:
            success, stdout, stderr = safe_subprocess_run(
                ["flake8"] + py_files,
                cwd=cwd,
                timeout=timeout // 3,
                tool_name="flake8",
            )

            if stderr and "blocked" in stderr.lower():
                results["flake8"] = {"status": "skipped", "message": stderr}
            elif success:
                results["flake8"] = {
                    "status": "pass",
                    "message": "✅ Flake8: No linting issues",
                }
            else:
                issue_count = len((stdout or "").strip().split("\n")) if stdout else 0
                results["flake8"] = {
                    "status": "warning",
                    "message": f"⚠️  Flake8: {issue_count} issue(s) found",
                    "details": (
                        stdout[:300] + "..."
                        if stdout and len(stdout) > 300
                        else stdout
                    ),
                }
        except Exception as e:
            results["flake8"] = {"status": "error", "message": f"Flake8 error: {e}"}
    else:
        results["flake8"] = {"status": "skipped", "message": "Flake8 not installed"}

    # Vulture dead code detection
    if is_tool_available("vulture"):
        try:
            success, stdout, stderr = safe_subprocess_run(
                ["vulture", "--min-confidence", "80"] + py_files,
                cwd=cwd,
                timeout=timeout // 3,
                tool_name="vulture",
            )

            if stderr and "blocked" in stderr.lower():
                results["vulture"] = {"status": "skipped", "message": stderr}
            elif not (stdout or "").strip():
                results["vulture"] = {
                    "status": "pass",
                    "message": "✅ Vulture: No dead code detected",
                }
            else:
                issue_count = len(stdout.strip().split("\n")) if stdout else 0
                results["vulture"] = {
                    "status": "info",
                    "message": f"💡 Vulture: {issue_count} potential dead code item(s)",
                    "details": (
                        stdout[:300] + "..."
                        if stdout and len(stdout) > 300
                        else stdout
                    ),
                }
        except Exception as e:
            results["vulture"] = {"status": "error", "message": f"Vulture error: {e}"}
    else:
        results["vulture"] = {"status": "skipped", "message": "Vulture not installed"}

    # Determine overall status
    has_warnings = any(r and r.get("status") == "warning" for r in results.values())
    has_errors = any(r and r.get("status") == "error" for r in results.values())

    return {
        "status": "error" if has_errors else ("warning" if has_warnings else "pass"),
        "results": results,
        "files": len(py_files),
    }


def validate_markdown_comprehensive(
    md_files: List[str], cwd: str, timeout: int
) -> Dict:
    """
    Run comprehensive markdown validation: metadata, links, placement.

    Returns dict with status, results for each check.
    """
    if not md_files:
        return {"status": "skipped", "reason": "no markdown files"}

    # Limit files to prevent overload
    md_files = limit_files(md_files)

    results = {"metadata": None, "links": None}

    validator_path = Path(cwd) / "tools" / "librarian_validate.py"
    link_validator_path = Path(cwd) / "tools" / "validate_links.py"

    # Check python availability first
    if not is_tool_available("python"):
        return {
            "status": "skipped",
            "reason": "Python not available",
            "results": results,
            "files": len(md_files),
        }

    # Metadata validation
    if validator_path.exists():
        try:
            success, stdout, stderr = safe_subprocess_run(
                ["python", str(validator_path)] + md_files,
                cwd=cwd,
                timeout=timeout // 2,
                tool_name="python",
            )

            if stderr and "blocked" in stderr.lower():
                results["metadata"] = {"status": "skipped", "message": stderr}
            else:
                output = (stdout or "") + (stderr or "")

                if "Error" in output or "FAILED" in output:
                    error_count = output.count("Error:")
                    results["metadata"] = {
                        "status": "warning",
                        "message": f"⚠️  Metadata: {error_count} issue(s) found",
                        "details": output[:300] + "..." if len(output) > 300 else output,
                    }
                else:
                    results["metadata"] = {
                        "status": "pass",
                        "message": f"✅ Metadata: {len(md_files)} file(s) validated",
                    }
        except Exception as e:
            results["metadata"] = {"status": "error", "message": f"Metadata error: {e}"}
    else:
        results["metadata"] = {
            "status": "skipped",
            "message": "librarian_validate.py not found",
        }

    # Link validation
    if link_validator_path.exists():
        try:
            success, stdout, stderr = safe_subprocess_run(
                ["python", str(link_validator_path)] + md_files,
                cwd=cwd,
                timeout=timeout // 2,
                tool_name="python",
            )

            if stderr and "blocked" in stderr.lower():
                results["links"] = {"status": "skipped", "message": stderr}
            else:
                output = (stdout or "") + (stderr or "")

                if "broken" in output.lower() or "error" in output.lower():
                    results["links"] = {
                        "status": "warning",
                        "message": "⚠️  Links: Broken links detected",
                        "details": output[:200] + "..." if len(output) > 200 else output,
                    }
                else:
                    results["links"] = {"status": "pass", "message": "✅ Links: All valid"}
        except Exception as e:
            results["links"] = {"status": "error", "message": f"Links error: {e}"}
    else:
        results["links"] = {
            "status": "skipped",
            "message": "validate_links.py not found",
        }

    # Determine overall status
    has_warnings = any(r and r.get("status") == "warning" for r in results.values())
    has_errors = any(r and r.get("status") == "error" for r in results.values())

    return {
        "status": "error" if has_errors else ("warning" if has_warnings else "pass"),
        "results": results,
        "files": len(md_files),
    }


def format_comprehensive_report(
    py_result: Dict,
    md_result: Dict,
    py_files: List[str],
    md_files: List[str],
    show_details: str,
) -> str:
    """Format comprehensive validation report"""
    lines = []
    lines.append("\n" + "━" * 50)
    lines.append("📊 Task Validation Complete")
    lines.append("━" * 50)

    # Files summary
    lines.append(f"\n📝 Files Changed: {len(py_files) + len(md_files)}")
    if py_files:
        lines.append(f"   • Python: {len(py_files)} file(s)")
    if md_files:
        lines.append(f"   • Markdown: {len(md_files)} file(s)")

    # Python validation results
    if py_result["status"] != "skipped":
        lines.append("\n🔧 Code Quality:")
        for tool_name, tool_result in py_result.get("results", {}).items():
            if tool_result:
                lines.append(f"   {tool_result.get('message', '')}")
                if show_details == "always" and "details" in tool_result:
                    for detail_line in tool_result["details"].split("\n")[:5]:
                        lines.append(f"      {detail_line}")
                if "fix" in tool_result:
                    lines.append(f"      Fix: {tool_result['fix']}")

    # Markdown validation results
    if md_result["status"] != "skipped":
        lines.append("\n📚 Documentation Quality:")
        for check_name, check_result in md_result.get("results", {}).items():
            if check_result:
                lines.append(f"   {check_result.get('message', '')}")
                if show_details == "always" and "details" in check_result:
                    for detail_line in check_result["details"].split("\n")[:5]:
                        lines.append(f"      {detail_line}")

    # Overall summary
    lines.append("\n" + "━" * 50)

    has_warnings = (
        py_result.get("status") == "warning" or md_result.get("status") == "warning"
    )
    has_errors = (
        py_result.get("status") == "error" or md_result.get("status") == "error"
    )

    if has_errors:
        lines.append("❌ Validation completed with errors")
        lines.append("   Some validation checks failed to run")
    elif has_warnings:
        lines.append("⚠️  Issues found - please review")
        lines.append("   Fix issues before committing (recommended)")
    else:
        lines.append("✅ All validation passed!")
        lines.append("   Task output meets quality standards")

    lines.append("━" * 50 + "\n")

    return "\n".join(lines)


def main():
    """Hook entry point"""
    try:
        # SAFEGUARD: Check if hooks should run at all
        if not guard_hook_execution():
            print(json.dumps({}))
            sys.exit(0)

        log_diagnostic("post_task hook started")

        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        command = hook_input.get("command", "")
        cwd = hook_input.get("cwd", os.getcwd())

        # Only run after /task commands
        if not command.startswith("task"):
            log_diagnostic(f"Skipping: not a task command ({command})")
            print(json.dumps({}))
            sys.exit(0)

        # Load settings
        settings = load_settings()
        config = ValidationConfig(settings)

        if not config.enabled:
            log_diagnostic("Validation disabled in settings")
            print(json.dumps({}))
            sys.exit(0)

        # Get changed files
        py_files, md_files = get_task_changed_files(cwd)

        if not py_files and not md_files:
            # No files changed during task
            response = {
                "hookSpecificOutput": {
                    "message": "\n✅ Task complete (no file changes detected)\n"
                }
            }
            print(json.dumps(response))
            sys.exit(0)

        # Run comprehensive validation
        py_result = validate_python_comprehensive(py_files, cwd, config.timeout)
        md_result = validate_markdown_comprehensive(md_files, cwd, config.timeout)

        # Format report
        report = format_comprehensive_report(
            py_result, md_result, py_files, md_files, config.show_details
        )

        # Return results
        response = {"hookSpecificOutput": {"message": report}}

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, allow operation but log
        error_response = {
            "hookSpecificOutput": {
                "message": f"⚠️ Post-task validation hook error: {e}\n(Validation skipped)\n"
            }
        }
        print(json.dumps(error_response))
        sys.exit(0)


if __name__ == "__main__":
    main()
