#!/usr/bin/env python3
"""
Safeguards module - Prevents runaway subprocess spawning and permission floods.

PRIMARY PROTECTION: Project scope validation
--------------------------------------------
Hooks only run in "heo-compatible" projects - those with marker files like
CLAUDE.md, .claude/hooks.json, etc. This prevents hooks from running in
arbitrary directories where they shouldn't.

SECONDARY PROTECTION: Emergency limits
--------------------------------------
High-water-mark limits that only kick in if something goes seriously wrong:
- 20 subprocesses per hook (normal hooks use ~6)
- 100 files per operation (catches runaway recursion)
- 500 subprocesses per session (emergency brake)

These limits are intentionally generous for normal use.

The problem this solves:
------------------------
When hooks spawn subprocesses (git, black, flake8, etc.) on macOS with
sandboxing enabled, each subprocess can trigger a permission dialog. If hooks
run in an unexpected project or loop over many files, this creates popup floods.

The solution: Don't run hooks in unknown projects in the first place.
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime
import json

# Import logging utilities
try:
    from .hook_utils import log_info, log_warning, log_error, HOOK_PREFIX, get_context
except ImportError:
    # Fallback for direct execution
    HOOK_PREFIX = "[heo]"
    def log_info(msg, **_): print(f"{HOOK_PREFIX} {msg}", file=sys.stderr)
    def log_warning(msg, **_): print(f"{HOOK_PREFIX} WARNING: {msg}", file=sys.stderr)
    def log_error(msg, **_): print(f"{HOOK_PREFIX} ERROR: {msg}", file=sys.stderr)
    def get_context(): return None


# ============================================================================
# CONSTANTS - Configurable limits
# ============================================================================

# Maximum subprocesses per hook execution
# Set high enough for normal use (git + black + flake8 + vulture + validators)
# This is a safety valve, not a performance limit
MAX_SUBPROCESS_PER_HOOK = 20

# Maximum files to process per operation
# Generous for normal use, prevents runaway on huge repos
MAX_FILES_PER_OPERATION = 100

# Rate limit: minimum seconds between subprocess calls
# Set to 0 for no performance impact - scope validation is the real protection
MIN_SUBPROCESS_INTERVAL = 0

# Session-wide subprocess limit (reset on session start)
# Very high - this is emergency brake only
MAX_SUBPROCESS_PER_SESSION = 500

# Timeout for subprocess operations
DEFAULT_SUBPROCESS_TIMEOUT = 30

# Marker file to detect heo-compatible projects
HEO_MARKER_FILES = [
    ".claude/hooks.json",
    ".claude/settings.local.json",
    "CLAUDE.md",
]


# ============================================================================
# GLOBAL STATE - Track subprocess calls
# ============================================================================

@dataclass
class SubprocessTracker:
    """Track subprocess calls to enforce rate limits."""
    calls_this_hook: int = 0
    calls_this_session: int = 0
    last_call_time: float = 0.0
    disabled_reason: Optional[str] = None
    session_start: float = field(default_factory=time.time)

    def reset_hook(self) -> None:
        """Reset per-hook counters."""
        self.calls_this_hook = 0

    def reset_session(self) -> None:
        """Reset session counters."""
        self.calls_this_hook = 0
        self.calls_this_session = 0
        self.session_start = time.time()
        self.disabled_reason = None


# Module-level tracker (reset per hook via reset_hook())
_tracker = SubprocessTracker()


def reset_safeguards() -> None:
    """Reset safeguard state. Call at start of each hook."""
    _tracker.reset_hook()


def reset_session_safeguards() -> None:
    """Reset all safeguard state. Call at session start."""
    _tracker.reset_session()


# ============================================================================
# PROJECT SCOPE VALIDATION
# ============================================================================

def is_heo_project(project_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Check if the project directory is a heo-compatible project.

    Returns:
        Tuple of (is_valid, reason)
    """
    if project_dir is None:
        # Prefer CLAUDE_PROJECT_DIR env var when available (avoids misclassification
        # when hooks run from plugin root)
        claude_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if claude_project_dir:
            project_dir = Path(claude_project_dir)
        else:
            project_dir = Path.cwd()

    # Check for marker files
    for marker in HEO_MARKER_FILES:
        marker_path = project_dir / marker
        if marker_path.exists():
            return True, f"Found {marker}"

    # Check environment variable override
    if os.environ.get("HEO_FORCE_ENABLE"):
        return True, "HEO_FORCE_ENABLE set"

    # Check if we're in the plugin itself (use path-aware check to avoid false positives)
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        try:
            if Path(project_dir).is_relative_to(Path(plugin_root)):
                return True, "Inside plugin directory"
        except (TypeError, ValueError):
            pass  # is_relative_to not available or invalid path

    return False, "No heo marker files found"


def is_safe_project_scope(project_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Check if hooks should run in this project.

    This prevents hooks from running in arbitrary directories that might
    trigger sandbox permission issues.

    Returns:
        Tuple of (is_safe, reason)
    """
    if project_dir is None:
        # Prefer CLAUDE_PROJECT_DIR env var when available (avoids misclassification
        # when hooks run from plugin root)
        claude_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if claude_project_dir:
            project_dir = Path(claude_project_dir)
        else:
            project_dir = Path.cwd()

    # Check if hooks are explicitly disabled - check this FIRST for consistent behavior
    if os.environ.get("HEO_DISABLE_HOOKS"):
        return False, "HEO_DISABLE_HOOKS set"

    # Check for skip file BEFORE accepting heo project result
    # This allows per-project disable even for heo-compatible projects
    skip_file = project_dir / ".heo-skip-hooks"
    if skip_file.exists():
        return False, ".heo-skip-hooks file exists"

    # Check if this is a heo project
    is_heo, reason = is_heo_project(project_dir)
    if is_heo:
        return True, reason

    # Default: don't run in unknown projects
    log_warning(
        f"Skipping hooks: not a heo project. "
        f"Create CLAUDE.md or set HEO_FORCE_ENABLE=1 to enable.",
        project_dir=str(project_dir)
    )
    return False, "Unknown project - hooks disabled for safety"


# ============================================================================
# SUBPROCESS RATE LIMITING
# ============================================================================

def can_spawn_subprocess(tool_name: str = "unknown") -> Tuple[bool, str]:
    """
    Check if spawning a subprocess is allowed.

    Enforces rate limits and maximum subprocess counts to prevent
    permission dialog floods.

    Args:
        tool_name: Name of the tool being spawned (for logging)

    Returns:
        Tuple of (allowed, reason)
    """
    global _tracker

    # Check if disabled
    if _tracker.disabled_reason:
        return False, _tracker.disabled_reason

    # Check per-hook limit
    if _tracker.calls_this_hook >= MAX_SUBPROCESS_PER_HOOK:
        reason = f"Per-hook subprocess limit reached ({MAX_SUBPROCESS_PER_HOOK})"
        log_warning(f"Subprocess blocked: {reason}", tool=tool_name)
        return False, reason

    # Check session limit
    if _tracker.calls_this_session >= MAX_SUBPROCESS_PER_SESSION:
        reason = f"Session subprocess limit reached ({MAX_SUBPROCESS_PER_SESSION})"
        _tracker.disabled_reason = reason
        log_error(f"Subprocess blocked: {reason}", tool=tool_name)
        return False, reason

    # Check rate limit
    now = time.time()
    elapsed = now - _tracker.last_call_time
    if elapsed < MIN_SUBPROCESS_INTERVAL:
        # Rate limit hit - sleep briefly
        time.sleep(MIN_SUBPROCESS_INTERVAL - elapsed)

    return True, "allowed"


def record_subprocess_call(tool_name: str = "unknown") -> None:
    """Record a subprocess call for rate limiting."""
    global _tracker
    _tracker.calls_this_hook += 1
    _tracker.calls_this_session += 1
    _tracker.last_call_time = time.time()

    # Log if approaching limits
    if _tracker.calls_this_hook >= MAX_SUBPROCESS_PER_HOOK - 1:
        log_warning(
            f"Approaching per-hook subprocess limit "
            f"({_tracker.calls_this_hook}/{MAX_SUBPROCESS_PER_HOOK})",
            tool=tool_name
        )


# ============================================================================
# TOOL AVAILABILITY CHECKS
# ============================================================================

_tool_cache: dict = {}

def is_tool_available(tool_name: str) -> bool:
    """
    Check if a tool is available WITHOUT spawning a subprocess.

    Uses shutil.which() which doesn't trigger permission dialogs.

    Args:
        tool_name: Name of the tool (e.g., "black", "flake8", "git")

    Returns:
        True if tool is available, False otherwise
    """
    if tool_name in _tool_cache:
        return _tool_cache[tool_name]

    available = shutil.which(tool_name) is not None
    _tool_cache[tool_name] = available

    if not available:
        # Use diagnostic log - don't spam stderr for missing optional tools
        log_diagnostic(f"Tool not available: {tool_name}")

    return available


def check_required_tools(*tools: str) -> Tuple[List[str], List[str]]:
    """
    Check which tools are available.

    Args:
        *tools: Tool names to check

    Returns:
        Tuple of (available_tools, missing_tools)
    """
    available = []
    missing = []

    for tool in tools:
        if is_tool_available(tool):
            available.append(tool)
        else:
            missing.append(tool)

    return available, missing


# ============================================================================
# SAFE SUBPROCESS WRAPPER
# ============================================================================

def safe_subprocess_run(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: int = DEFAULT_SUBPROCESS_TIMEOUT,
    tool_name: Optional[str] = None,
    capture_output: bool = True,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Run a subprocess with safeguards.

    Checks rate limits, tool availability, and enforces timeouts.

    Args:
        cmd: Command and arguments to run
        cwd: Working directory
        timeout: Maximum seconds to wait
        tool_name: Name of tool for logging (default: first element of cmd)
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (success, stdout, stderr)
        Returns (False, None, None) if blocked by safeguards
    """
    import subprocess

    # Guard against empty commands
    if not cmd:
        return False, None, "Empty command"

    tool = tool_name or os.path.basename(cmd[0])
    cmd0 = cmd[0]

    # Check tool availability - handle explicit paths differently
    if os.path.isabs(cmd0) or os.path.sep in cmd0 or (os.path.altsep and os.path.altsep in cmd0):
        # cmd[0] is an explicit path - check if it exists and is executable
        if not Path(cmd0).exists():
            return False, None, f"Tool not found: {cmd0}"
        if not os.access(cmd0, os.X_OK):
            return False, None, f"Tool not executable: {cmd0}"
    else:
        # Simple command name - use shutil.which (no subprocess needed)
        if not is_tool_available(tool):
            return False, None, f"Tool not available: {tool}"

    # Check rate limits
    allowed, reason = can_spawn_subprocess(tool)
    if not allowed:
        return False, None, f"Subprocess blocked: {reason}"

    # Record the call
    record_subprocess_call(tool)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )
        return (
            result.returncode == 0,
            result.stdout if capture_output else None,
            result.stderr if capture_output else None,
        )
    except subprocess.TimeoutExpired:
        log_warning(f"{tool} timed out after {timeout}s")
        return False, None, f"Timeout after {timeout}s"
    except FileNotFoundError:
        log_warning(f"{tool} not found")
        return False, None, f"Tool not found: {tool}"
    except PermissionError as e:
        log_error(f"{tool} permission error: {e}")
        return False, None, f"Permission error: {e}"
    except Exception as e:
        log_error(f"{tool} error: {e}")
        return False, None, str(e)


# ============================================================================
# FILE LIMITING
# ============================================================================

def limit_files(files: List[str], max_files: int = MAX_FILES_PER_OPERATION) -> List[str]:
    """
    Limit the number of files to process.

    Args:
        files: List of file paths
        max_files: Maximum files to process

    Returns:
        Truncated list of files
    """
    if len(files) > max_files:
        log_warning(
            f"Limiting files from {len(files)} to {max_files} to prevent overload"
        )
        return files[:max_files]
    return files


# ============================================================================
# LOGGING HELPERS
# ============================================================================

_log_file: Optional[str] = None

def init_logging(log_dir: Optional[Path] = None) -> Path:
    """
    Initialize hook logging for diagnostics.

    Creates a log file in the specified directory or a default location.

    Returns:
        Path to the log file
    """
    global _log_file

    if log_dir is None:
        # Use plugin directory or temp
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if plugin_root:
            log_dir = Path(plugin_root) / "logs"
        else:
            log_dir = Path.home() / ".heo" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Create date-based log file
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = log_dir / f"hooks-{date_str}.log"

    _log_file = str(log_path)
    os.environ["HEO_LOG_FILE"] = _log_file

    return log_path


def log_diagnostic(message: str, **data) -> None:
    """
    Log diagnostic information for troubleshooting.

    Writes to the log file if initialized, otherwise stderr.
    """
    global _log_file

    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": "DIAGNOSTIC",
        "message": message,
        **data
    }

    if _log_file:
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except (IOError, OSError):
            pass

    if os.environ.get("HEO_DEBUG"):
        print(f"{HOOK_PREFIX} [DIAG] {message}", file=sys.stderr)


# ============================================================================
# EARLY BAILOUT
# ============================================================================

def should_skip_hooks() -> Tuple[bool, str]:
    """
    Check if hooks should be skipped entirely.

    Call this at the start of each hook to bail out early if conditions
    indicate hooks shouldn't run.

    Returns:
        Tuple of (should_skip, reason)
    """
    # Check environment disable flag
    if os.environ.get("HEO_DISABLE_HOOKS"):
        return True, "HEO_DISABLE_HOOKS set"

    # Check if we've hit the session limit
    if _tracker.disabled_reason:
        return True, _tracker.disabled_reason

    # Check project scope
    is_safe, reason = is_safe_project_scope()
    if not is_safe:
        return True, reason

    return False, ""


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def guard_hook_execution() -> bool:
    """
    Guard hook execution with all safeguards.

    Call at the start of each hook. Returns True if hook should proceed,
    False if it should exit early.

    Usage:
        def main():
            if not guard_hook_execution():
                return  # Exit early
            # ... rest of hook logic
    """
    reset_safeguards()

    skip, reason = should_skip_hooks()
    if skip:
        log_diagnostic(f"Hook skipped: {reason}")
        return False

    return True


if __name__ == "__main__":
    # Self-test
    print(f"Project scope check: {is_safe_project_scope()}")
    print(f"Tool availability: git={is_tool_available('git')}, black={is_tool_available('black')}")
    print(f"Can spawn subprocess: {can_spawn_subprocess('test')}")
