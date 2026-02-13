#!/usr/bin/env python3
"""
Shared utilities for hook scripts.

Provides graceful failure handling and common operations.
"""

import functools
import json
import os
import sys
import time
import traceback
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Hook output prefix - use this constant for consistent messaging
HOOK_PREFIX = "[heo]"

# Minimum Python version required
MIN_PYTHON_VERSION = (3, 9)


@dataclass
class HookContext:
    """
    Context for a hook execution.

    Uses contextvars for thread-safe state management instead of module globals.
    """
    log_file: Optional[str] = None
    hook_name: Optional[str] = None
    start_time: Optional[float] = None


# Thread-safe context variable (replaces module-level globals)
_hook_context: ContextVar[HookContext] = ContextVar(
    'hook_context',
    default=HookContext(log_file=os.environ.get("HEO_LOG_FILE"))
)


def get_context() -> HookContext:
    """Get the current hook context."""
    return _hook_context.get()


def set_context(ctx: HookContext) -> None:
    """Set the hook context."""
    _hook_context.set(ctx)


def init_context(log_file: Optional[str] = None) -> HookContext:
    """
    Initialize a new hook context.

    Args:
        log_file: Path to structured log file, or None to use HEO_LOG_FILE env var.

    Returns:
        The initialized context.
    """
    ctx = HookContext(
        log_file=log_file if log_file is not None else os.environ.get("HEO_LOG_FILE"),
    )
    _hook_context.set(ctx)
    return ctx


def check_python_version() -> bool:
    """
    Check if Python version meets minimum requirements.

    Returns True if version is sufficient, False otherwise.
    """
    if sys.version_info < MIN_PYTHON_VERSION:
        print(
            f"{HOOK_PREFIX} WARNING: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required, "
            f"have {sys.version_info.major}.{sys.version_info.minor}",
            file=sys.stderr
        )
        return False
    return True


def graceful_hook(blocking: bool = False, name: Optional[str] = None):
    """
    Decorator for hook main functions that handles errors gracefully.

    Args:
        blocking: If True, errors cause exit(2) to block. If False, exit(0) to allow.
        name: Optional hook name for logging. Defaults to function name.

    Usage:
        @graceful_hook(blocking=True, name="git-safety")
        def main():
            # hook logic that might fail
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            hook_name = name or func.__name__
            log_hook_start(hook_name)
            try:
                result = func(*args, **kwargs)
                log_hook_end(blocked=False)
                return result
            except SystemExit as e:
                # Track if blocked (exit code 2)
                log_hook_end(blocked=(e.code == 2))
                raise
            except KeyboardInterrupt:
                log_hook_end(blocked=False)
                sys.exit(130)
            except BrokenPipeError:
                # stdout closed, common when piping
                log_hook_end(blocked=False)
                sys.exit(0)
            except Exception as e:
                # Log error but don't crash
                log_error(f"Hook error: {e}", exception=str(e))
                if "--debug" in sys.argv or os.environ.get("HEO_DEBUG"):
                    traceback.print_exc(file=sys.stderr)
                log_hook_end(blocked=blocking)
                # Fail open (allow) unless explicitly blocking
                sys.exit(2 if blocking else 0)
        return wrapper
    return decorator


def read_hook_input() -> dict:
    """
    Read and parse hook input from stdin.

    Returns empty dict if stdin is empty or invalid JSON.
    """
    try:
        # Check if stdin has data
        if sys.stdin.isatty():
            return {}
        content = sys.stdin.read()
        if not content.strip():
            return {}
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}


def write_hook_output(data: dict) -> None:
    """
    Write hook output to stdout (for PostToolUse pass-through).
    """
    try:
        json.dump(data, sys.stdout)
    except (IOError, BrokenPipeError):
        pass


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    return Path.cwd()


def get_plugin_dir() -> Path:
    """Get plugin directory from environment."""
    plugin_dir = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_dir:
        return Path(plugin_dir)
    # Fallback: assume we're in hooks/ or hooks/lib/
    here = Path(__file__).parent
    if here.name == "lib":
        return here.parent.parent
    return here.parent


def check_dependencies(*modules: str) -> List[str]:
    """
    Check if required modules are available.

    Returns list of missing module names.
    """
    missing = []
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    return missing


def _write_to_log_file(entry: dict) -> None:
    """Write a structured log entry to the log file if configured."""
    ctx = get_context()
    if not ctx.log_file:
        return
    try:
        with open(ctx.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except (IOError, OSError) as e:
        # Log to stderr in debug mode
        if os.environ.get("HEO_DEBUG"):
            print(f"{HOOK_PREFIX} Log write failed: {e}", file=sys.stderr)


def _make_log_entry(level: str, message: str, **extra) -> dict:
    """Create a structured log entry."""
    ctx = get_context()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
    }
    if ctx.hook_name:
        entry["hook"] = ctx.hook_name
    entry.update(extra)
    return entry


def log_warning(message: str, **extra) -> None:
    """Log a warning message to stderr and optionally to log file."""
    print(f"{HOOK_PREFIX} {message}", file=sys.stderr)
    _write_to_log_file(_make_log_entry("WARNING", message, **extra))


def log_error(message: str, **extra) -> None:
    """Log an error message to stderr and optionally to log file."""
    print(f"{HOOK_PREFIX} ERROR: {message}", file=sys.stderr)
    _write_to_log_file(_make_log_entry("ERROR", message, **extra))


def log_info(message: str, **extra) -> None:
    """Log an info message to stderr and optionally to log file."""
    print(f"{HOOK_PREFIX} {message}", file=sys.stderr)
    _write_to_log_file(_make_log_entry("INFO", message, **extra))


def log_blocked(command: str, reason: str) -> None:
    """Log a blocked command with structured data."""
    log_error(f"BLOCKED: {reason}", command=command[:200], reason=reason)


def log_hook_start(hook_name: str) -> None:
    """Record hook start time for duration tracking."""
    ctx = get_context()
    ctx.hook_name = hook_name
    ctx.start_time = time.time()
    if ctx.log_file:
        _write_to_log_file(_make_log_entry("DEBUG", f"Hook started: {hook_name}"))


def log_hook_end(blocked: bool = False) -> None:
    """Log hook completion with duration."""
    ctx = get_context()
    if ctx.start_time is not None:
        duration_ms = (time.time() - ctx.start_time) * 1000
        if ctx.log_file:
            _write_to_log_file(_make_log_entry(
                "DEBUG",
                f"Hook completed: {ctx.hook_name}",
                duration_ms=round(duration_ms, 2),
                blocked=blocked
            ))
    ctx.hook_name = None
    ctx.start_time = None


class HookResult:
    """
    Result of a hook check.

    Usage:
        result = HookResult()
        result.block("Dangerous command detected", command="git push --no-verify")
        result.warn("Consider using a different approach")
        result.exit()
    """

    def __init__(self):
        self.blocked = False
        self.block_reason: Optional[str] = None
        self.block_command: Optional[str] = None
        self.warnings: List[str] = []

    def block(self, reason: str, command: Optional[str] = None) -> None:
        """Mark this hook as blocking with a reason."""
        self.blocked = True
        self.block_reason = reason
        self.block_command = command

    def warn(self, message: str) -> None:
        """Add a warning (non-blocking)."""
        self.warnings.append(message)

    def exit(self, pass_through: Optional[dict] = None) -> None:
        """
        Exit with appropriate code and output.

        Args:
            pass_through: For PostToolUse hooks, data to pass through to stdout.
        """
        for warning in self.warnings:
            log_warning(warning)

        if self.blocked:
            if self.block_command:
                log_blocked(self.block_command, self.block_reason)
            else:
                log_error(f"BLOCKED: {self.block_reason}")
            sys.exit(2)

        if pass_through is not None:
            write_hook_output(pass_through)

        sys.exit(0)
