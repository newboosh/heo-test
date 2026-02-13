#!/usr/bin/env python3
"""
Virtual environment aware command runner.

Discovers the project's venv and runs tools using that environment,
ensuring project-specific tool versions are used.

Usage:
    python venv_runner.py <tool> [args...]

Examples:
    python venv_runner.py ruff format src/
    python venv_runner.py pytest tests/
    python venv_runner.py mypy src/
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Common venv directory names, in priority order
VENV_DIRS = [
    ".venv",
    "venv",
    ".env",
    "env",
]

# Common package manager lock files that indicate how to run tools
PACKAGE_MANAGERS = {
    "poetry.lock": ["poetry", "run"],
    "Pipfile.lock": ["pipenv", "run"],
    "uv.lock": ["uv", "run"],
    "pdm.lock": ["pdm", "run"],
}


def find_venv(project_dir: Path) -> Optional[Path]:
    """Find virtual environment directory in project."""
    for venv_name in VENV_DIRS:
        venv_path = project_dir / venv_name
        if venv_path.is_dir():
            # Verify it's a valid venv (has bin/python or Scripts/python.exe)
            if (venv_path / "bin" / "python").exists():
                return venv_path
            if (venv_path / "Scripts" / "python.exe").exists():
                return venv_path
    return None


def find_package_manager(project_dir: Path) -> Optional[List[str]]:
    """Find package manager based on lock files."""
    for lock_file, run_cmd in PACKAGE_MANAGERS.items():
        if (project_dir / lock_file).exists():
            # Verify the package manager is installed
            if shutil.which(run_cmd[0]):
                return run_cmd
    return None


def get_venv_tool_path(venv_path: Path, tool: str) -> Optional[Path]:
    """Get path to tool in venv's bin directory."""
    # Unix
    tool_path = venv_path / "bin" / tool
    if tool_path.exists():
        return tool_path

    # Windows
    tool_path = venv_path / "Scripts" / f"{tool}.exe"
    if tool_path.exists():
        return tool_path

    return None


def run_tool(tool: str, args: List[str], project_dir: Path) -> int:
    """
    Run a tool using the project's environment.

    Priority:
    1. Package manager (poetry run, pipenv run, etc.) if lock file present
    2. Venv's tool binary if venv found
    3. Global tool as fallback
    """
    # Try package manager first
    pkg_manager = find_package_manager(project_dir)
    if pkg_manager:
        cmd = pkg_manager + [tool] + args
        result = subprocess.run(cmd, cwd=project_dir)
        return result.returncode

    # Try venv
    venv_path = find_venv(project_dir)
    if venv_path:
        tool_path = get_venv_tool_path(venv_path, tool)
        if tool_path:
            cmd = [str(tool_path)] + args
            result = subprocess.run(cmd, cwd=project_dir)
            return result.returncode

        # Tool not in venv, try python -m
        python_path = venv_path / "bin" / "python"
        if not python_path.exists():
            python_path = venv_path / "Scripts" / "python.exe"

        if python_path.exists():
            cmd = [str(python_path), "-m", tool] + args
            result = subprocess.run(cmd, cwd=project_dir)
            # returncode 2 with -m often means module not found, fall through to global
            if result.returncode != 2:
                return result.returncode

    # Fallback to global
    global_tool = shutil.which(tool)
    if global_tool:
        cmd = [global_tool] + args
        result = subprocess.run(cmd, cwd=project_dir)
        return result.returncode

    print(f"[frosty] Tool not found: {tool}", file=sys.stderr)
    return 127  # Command not found


def main():
    if len(sys.argv) < 2:
        print("Usage: venv_runner.py <tool> [args...]", file=sys.stderr)
        sys.exit(1)

    tool = sys.argv[1]
    args = sys.argv[2:]

    # Get project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        project_dir = Path(project_dir)
    else:
        project_dir = Path.cwd()

    returncode = run_tool(tool, args, project_dir)
    sys.exit(returncode)


if __name__ == "__main__":
    main()
