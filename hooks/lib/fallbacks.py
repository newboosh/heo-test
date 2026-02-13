#!/usr/bin/env python3
"""
Fallback implementations when hook_utils is unavailable.

These minimal implementations allow hooks to degrade gracefully
when the lib directory is missing or corrupted.

Usage in hooks:
    from fallbacks import import_hook_utils
    graceful_hook, read_hook_input, HookResult, write_hook_output, get_project_dir = import_hook_utils()
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Hook output prefix - consistent with hook_utils.py
HOOK_PREFIX = "[heo]"


def graceful_hook_fallback(blocking: bool = False, name: Optional[str] = None):
    """Minimal graceful_hook that fails open (or secure if blocking=True)."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SystemExit:
                raise  # Let explicit exits through
            except KeyboardInterrupt:
                sys.exit(130)
            except Exception as e:
                print(f"{HOOK_PREFIX} Hook error: {e}", file=sys.stderr)
                sys.exit(2 if blocking else 0)
        return wrapper
    return decorator


def read_hook_input_fallback() -> dict:
    """Minimal stdin reader."""
    try:
        if sys.stdin.isatty():
            return {}
        content = sys.stdin.read()
        return json.loads(content) if content.strip() else {}
    except Exception:
        return {}


def write_hook_output_fallback(data: dict) -> None:
    """Minimal output writer."""
    try:
        json.dump(data, sys.stdout)
    except Exception:
        pass


def get_project_dir_fallback() -> Path:
    """Minimal project dir getter."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


class HookResultFallback:
    """Minimal HookResult implementation."""

    def __init__(self):
        self.blocked = False
        self.block_reason: Optional[str] = None
        self.block_command: Optional[str] = None
        self.warnings = []

    def block(self, reason: str, command: Optional[str] = None) -> None:
        self.blocked = True
        self.block_reason = reason
        self.block_command = command

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def exit(self, pass_through: Optional[dict] = None) -> None:
        for warning in self.warnings:
            print(f"{HOOK_PREFIX} {warning}", file=sys.stderr)

        if self.blocked:
            print(f"{HOOK_PREFIX} BLOCKED: {self.block_reason}", file=sys.stderr)
            sys.exit(2)

        if pass_through is not None:
            write_hook_output_fallback(pass_through)

        sys.exit(0)


def import_hook_utils():
    """
    Import hook_utils with fallbacks.

    Returns tuple of (graceful_hook, read_hook_input, HookResult, write_hook_output, get_project_dir).

    Usage:
        graceful_hook, read_hook_input, HookResult, write_hook_output, get_project_dir = import_hook_utils()

        @graceful_hook(blocking=False)
        def main():
            input_data = read_hook_input()
            # ... hook logic ...
    """
    try:
        from hook_utils import (
            graceful_hook,
            read_hook_input,
            HookResult,
            write_hook_output,
            get_project_dir,
        )
        return graceful_hook, read_hook_input, HookResult, write_hook_output, get_project_dir
    except ImportError:
        return (
            graceful_hook_fallback,
            read_hook_input_fallback,
            HookResultFallback,
            write_hook_output_fallback,
            get_project_dir_fallback,
        )


# Convenience: also provide individual imports for hooks that only need some functions
def import_venv_runner():
    """
    Import venv_runner with fallbacks.

    Returns tuple of (find_venv, find_package_manager, get_venv_tool_path).
    """
    try:
        from venv_runner import find_venv, find_package_manager, get_venv_tool_path
        return find_venv, find_package_manager, get_venv_tool_path
    except ImportError:
        # Minimal fallbacks
        def find_venv_fallback(project_dir: Path) -> Optional[Path]:
            for name in [".venv", "venv"]:
                venv = project_dir / name
                if (venv / "bin" / "python").exists():
                    return venv
            return None

        def find_package_manager_fallback(project_dir: Path):
            return None

        def get_venv_tool_path_fallback(venv_path: Path, tool: str) -> Optional[Path]:
            path = venv_path / "bin" / tool
            return path if path.exists() else None

        return find_venv_fallback, find_package_manager_fallback, get_venv_tool_path_fallback
