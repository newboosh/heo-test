#!/usr/bin/env python3
"""
Git hooks manager - detects and configures project's git hook tool.

Supports: Husky, pre-commit, lefthook, simple-git-hooks, lint-staged
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Literal, Optional

HookTool = Literal["husky", "pre-commit", "lefthook", "simple-git-hooks", "none"]


def detect_hook_tool(project_dir: Path) -> HookTool:
    """Detect which git hook tool the project uses."""

    # Check for pre-commit (Python)
    if (project_dir / ".pre-commit-config.yaml").exists():
        return "pre-commit"

    # Check for lefthook
    if (project_dir / "lefthook.yml").exists() or (project_dir / "lefthook.yaml").exists():
        return "lefthook"

    # Check for Husky
    if (project_dir / ".husky").is_dir():
        return "husky"

    # Check package.json for JS-based tools
    package_json = project_dir / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg = json.load(f)

            dev_deps = pkg.get("devDependencies", {})
            deps = pkg.get("dependencies", {})
            all_deps = {**deps, **dev_deps}

            if "husky" in all_deps:
                return "husky"
            if "simple-git-hooks" in all_deps:
                return "simple-git-hooks"
        except (json.JSONDecodeError, IOError):
            pass

    return "none"


def detect_project_type(project_dir: Path) -> Literal["python", "node", "mixed", "unknown"]:
    """Detect the primary project type."""
    has_python = (
        (project_dir / "pyproject.toml").exists() or
        (project_dir / "setup.py").exists() or
        (project_dir / "requirements.txt").exists()
    )
    has_node = (project_dir / "package.json").exists()

    if has_python and has_node:
        return "mixed"
    elif has_python:
        return "python"
    elif has_node:
        return "node"
    return "unknown"


def suggest_hook_tool(project_dir: Path) -> HookTool:
    """Suggest the best hook tool for this project."""
    project_type = detect_project_type(project_dir)

    if project_type == "python":
        return "pre-commit"
    elif project_type == "node":
        return "husky"
    elif project_type == "mixed":
        # pre-commit is more language-agnostic
        return "pre-commit"
    return "pre-commit"  # Default to pre-commit


# ============================================================================
# Husky Configuration
# ============================================================================

def setup_husky(project_dir: Path) -> bool:
    """Set up Husky in a Node.js project."""
    package_json = project_dir / "package.json"
    if not package_json.exists():
        return False

    # Check if npm/yarn/pnpm is available
    npm = shutil.which("npm") or shutil.which("yarn") or shutil.which("pnpm")
    if not npm:
        return False

    # Install husky
    try:
        subprocess.run(
            [npm, "install", "--save-dev", "husky"],
            cwd=project_dir,
            capture_output=True,
            timeout=60
        )

        # Initialize husky
        subprocess.run(
            ["npx", "husky", "init"],
            cwd=project_dir,
            capture_output=True,
            timeout=30
        )
        return True
    except Exception:
        return False


def configure_husky_hook(project_dir: Path, hook_name: str, commands: List[str]) -> bool:
    """Configure a specific Husky hook."""
    husky_dir = project_dir / ".husky"
    husky_dir.mkdir(exist_ok=True)

    hook_file = husky_dir / hook_name

    content = "#!/usr/bin/env sh\n"
    content += ". \"$(dirname -- \"$0\")/_/husky.sh\"\n\n"
    content += "\n".join(commands) + "\n"

    try:
        with open(hook_file, "w") as f:
            f.write(content)
        hook_file.chmod(0o755)
        return True
    except IOError:
        return False


# ============================================================================
# pre-commit Configuration
# ============================================================================

def setup_pre_commit(project_dir: Path) -> bool:
    """Set up pre-commit in a Python project."""
    # Check if pre-commit is available
    pre_commit = shutil.which("pre-commit")
    if not pre_commit:
        # Try to install it
        pip = shutil.which("pip") or shutil.which("pip3")
        if pip:
            try:
                subprocess.run(
                    [pip, "install", "pre-commit"],
                    capture_output=True,
                    timeout=60
                )
                pre_commit = shutil.which("pre-commit")
            except Exception:
                pass

    if not pre_commit:
        return False

    # Install hooks
    try:
        subprocess.run(
            [pre_commit, "install"],
            cwd=project_dir,
            capture_output=True,
            timeout=30
        )
        return True
    except Exception:
        return False


def generate_pre_commit_config(project_dir: Path, tools: List[str] = None) -> str:
    """Generate a .pre-commit-config.yaml for the project."""
    if tools is None:
        tools = ["ruff", "mypy"]

    config = """# See https://pre-commit.com for more information
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
"""

    if "ruff" in tools:
        config += """
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
"""

    if "mypy" in tools:
        config += """
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: []
"""

    if "black" in tools and "ruff" not in tools:
        config += """
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
"""

    return config


def configure_pre_commit(project_dir: Path, tools: List[str] = None) -> bool:
    """Configure pre-commit with standard hooks."""
    config_file = project_dir / ".pre-commit-config.yaml"

    # Don't overwrite existing config
    if config_file.exists():
        return True

    config = generate_pre_commit_config(project_dir, tools)

    try:
        with open(config_file, "w") as f:
            f.write(config)
        return True
    except IOError:
        return False


# ============================================================================
# lefthook Configuration
# ============================================================================

def generate_lefthook_config(project_dir: Path) -> str:
    """Generate a lefthook.yml for the project."""
    project_type = detect_project_type(project_dir)

    config = """# lefthook.yml - Git hooks configuration
# https://github.com/evilmartians/lefthook

pre-commit:
  parallel: true
  commands:
"""

    if project_type in ("python", "mixed"):
        config += """    ruff-check:
      glob: "*.py"
      run: ruff check --fix {staged_files}
    ruff-format:
      glob: "*.py"
      run: ruff format {staged_files}
"""

    if project_type in ("node", "mixed"):
        config += """    prettier:
      glob: "*.{js,ts,jsx,tsx,json,md}"
      run: npx prettier --write {staged_files}
    eslint:
      glob: "*.{js,ts,jsx,tsx}"
      run: npx eslint --fix {staged_files}
"""

    config += """
pre-push:
  commands:
    test:
      run: """

    if project_type == "python":
        config += "pytest --tb=short -q"
    elif project_type == "node":
        config += "npm test"
    else:
        config += "echo 'No tests configured'"

    config += "\n"

    return config


def configure_lefthook(project_dir: Path) -> bool:
    """Configure lefthook with standard hooks."""
    config_file = project_dir / "lefthook.yml"

    if config_file.exists():
        return True

    config = generate_lefthook_config(project_dir)

    try:
        with open(config_file, "w") as f:
            f.write(config)

        # Install lefthook hooks
        lefthook = shutil.which("lefthook")
        if lefthook:
            subprocess.run(
                [lefthook, "install"],
                cwd=project_dir,
                capture_output=True,
                timeout=30
            )
        return True
    except (IOError, Exception):
        return False


# ============================================================================
# Main API
# ============================================================================

def ensure_git_hooks(project_dir: Path, force_tool: HookTool = None) -> dict:
    """
    Ensure git hooks are configured for the project.

    Returns:
        {
            "tool": str,  # Which tool is/was configured
            "was_setup": bool,  # Whether we had to set it up
            "success": bool,
            "message": str,
        }
    """
    current_tool = detect_hook_tool(project_dir)

    if current_tool != "none" and not force_tool:
        return {
            "tool": current_tool,
            "was_setup": False,
            "success": True,
            "message": f"Project already uses {current_tool}",
        }

    # Determine which tool to use
    tool = force_tool or suggest_hook_tool(project_dir)

    success = False
    message = ""

    if tool == "pre-commit":
        if configure_pre_commit(project_dir):
            success = setup_pre_commit(project_dir)
            message = "Configured pre-commit" if success else "Created config but failed to install"

    elif tool == "husky":
        success = setup_husky(project_dir)
        if success:
            configure_husky_hook(project_dir, "pre-commit", ["npx lint-staged"])
            message = "Configured Husky"
        else:
            message = "Failed to set up Husky"

    elif tool == "lefthook":
        success = configure_lefthook(project_dir)
        message = "Configured lefthook" if success else "Failed to configure lefthook"

    return {
        "tool": tool,
        "was_setup": True,
        "success": success,
        "message": message,
    }


def get_hook_status(project_dir: Path) -> dict:
    """Get status of git hooks in the project."""
    tool = detect_hook_tool(project_dir)
    project_type = detect_project_type(project_dir)

    hooks_installed = False
    if tool == "husky":
        hooks_installed = (project_dir / ".husky" / "pre-commit").exists()
    elif tool == "pre-commit":
        hooks_installed = (project_dir / ".git" / "hooks" / "pre-commit").exists()
    elif tool == "lefthook":
        hooks_installed = (project_dir / ".git" / "hooks" / "pre-commit").exists()

    return {
        "tool": tool,
        "project_type": project_type,
        "hooks_installed": hooks_installed,
        "suggested_tool": suggest_hook_tool(project_dir) if tool == "none" else tool,
    }


if __name__ == "__main__":
    # CLI for testing
    project_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    status = get_hook_status(project_dir)
    print(f"Project: {project_dir}")
    print(f"Type: {status['project_type']}")
    print(f"Hook tool: {status['tool']}")
    print(f"Hooks installed: {status['hooks_installed']}")

    if status['tool'] == 'none':
        print(f"Suggested: {status['suggested_tool']}")
