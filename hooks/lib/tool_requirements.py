#!/usr/bin/env python3
"""
Detect project tool requirements from config files.

Scans the project for tool configuration and dependency files to determine
what tools should be available and at what versions.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback
    except ImportError:
        tomllib = None


def parse_pyproject_toml(project_dir: Path) -> dict:
    """Extract tool requirements from pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists() or not tomllib:
        return {}

    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    tools = {}

    # Check [tool.*] sections for configured tools
    tool_section = data.get("tool", {})
    for tool_name in tool_section:
        tools[tool_name] = {"configured": True, "version": None}

    # Check dev dependencies for version constraints
    # Poetry style
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("group", {}).get("dev", {}).get("dependencies", {})
    if not poetry_deps:
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})

    for dep, constraint in poetry_deps.items():
        if dep in tools:
            tools[dep]["version"] = _extract_version(constraint)
        else:
            tools[dep] = {"configured": False, "version": _extract_version(constraint)}

    # PEP 621 style (project.optional-dependencies.dev)
    pep621_dev = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    for dep_str in pep621_dev:
        name, version = _parse_requirement(dep_str)
        if name:
            if name in tools:
                tools[name]["version"] = tools[name].get("version") or version
            else:
                tools[name] = {"configured": False, "version": version}

    # uv style (tool.uv.dev-dependencies)
    uv_dev = data.get("tool", {}).get("uv", {}).get("dev-dependencies", [])
    for dep_str in uv_dev:
        name, version = _parse_requirement(dep_str)
        if name:
            if name in tools:
                tools[name]["version"] = tools[name].get("version") or version
            else:
                tools[name] = {"configured": False, "version": version}

    return tools


def _extract_version(constraint) -> Optional[str]:
    """Extract version from various constraint formats."""
    if isinstance(constraint, str):
        # "^1.0.0" or ">=1.0,<2.0" or "1.0.0"
        match = re.search(r'[\d]+\.[\d]+(?:\.[\d]+)?', constraint)
        return match.group(0) if match else None
    elif isinstance(constraint, dict):
        return constraint.get("version")
    return None


def _parse_requirement(req_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a PEP 508 requirement string."""
    # "ruff>=0.1.0" -> ("ruff", "0.1.0")
    match = re.match(r'^([a-zA-Z0-9_-]+)(?:[<>=!]+(.+))?', req_str.strip())
    if match:
        name = match.group(1).lower().replace("-", "_")
        version = match.group(2)
        if version:
            version = re.search(r'[\d]+\.[\d]+(?:\.[\d]+)?', version)
            version = version.group(0) if version else None
        return name, version
    return None, None


def detect_tool_configs(project_dir: Path) -> dict:
    """Detect tools by their config files."""
    config_files = {
        "ruff": ["ruff.toml", ".ruff.toml", "pyproject.toml"],
        "black": ["pyproject.toml", ".black"],
        "mypy": ["mypy.ini", ".mypy.ini", "pyproject.toml"],
        "pytest": ["pytest.ini", "pyproject.toml", "setup.cfg"],
        "flake8": [".flake8", "setup.cfg", "tox.ini"],
        "isort": [".isort.cfg", "pyproject.toml", "setup.cfg"],
        "pylint": [".pylintrc", "pylintrc", "pyproject.toml"],
        "bandit": [".bandit", "bandit.yaml", "pyproject.toml"],
        "pre-commit": [".pre-commit-config.yaml"],
        "prettier": [".prettierrc", ".prettierrc.json", ".prettierrc.yaml", "prettier.config.js"],
        "eslint": [".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js"],
        "typescript": ["tsconfig.json"],
    }

    tools = {}
    for tool, configs in config_files.items():
        for config in configs:
            if (project_dir / config).exists():
                tools[tool] = {"configured": True, "config_file": config}
                break

    return tools


def check_requirements_txt(project_dir: Path) -> dict:
    """Check requirements files for dev tools."""
    tools = {}
    req_files = [
        "requirements-dev.txt",
        "requirements_dev.txt",
        "dev-requirements.txt",
        "requirements/dev.txt",
        "requirements.txt",
    ]

    dev_tools = {
        "ruff", "black", "mypy", "pytest", "flake8", "isort",
        "pylint", "bandit", "pre-commit", "coverage", "pytest-cov",
    }

    for req_file in req_files:
        path = project_dir / req_file
        if not path.exists():
            continue

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    name, version = _parse_requirement(line)
                    if name and (name.replace("_", "-") in dev_tools or name in dev_tools):
                        tools[name] = {"version": version, "source": req_file}
        except IOError:
            continue

    return tools


def get_project_tool_requirements(project_dir: Path) -> dict:
    """
    Get complete picture of project tool requirements.

    Returns dict of tool name -> {
        "configured": bool,  # Has config in project
        "version": str|None,  # Required version
        "config_file": str|None,  # Where config lives
        "source": str|None,  # Where requirement came from
    }
    """
    tools = {}

    # Layer 1: Config files indicate tool is used
    config_tools = detect_tool_configs(project_dir)
    for name, info in config_tools.items():
        tools[name] = info

    # Layer 2: pyproject.toml has version requirements
    pyproject_tools = parse_pyproject_toml(project_dir)
    for name, info in pyproject_tools.items():
        if name in tools:
            tools[name].update(info)
        else:
            tools[name] = info

    # Layer 3: requirements.txt has version pins
    req_tools = check_requirements_txt(project_dir)
    for name, info in req_tools.items():
        if name in tools:
            tools[name].update(info)
        else:
            tools[name] = info

    return tools


if __name__ == "__main__":
    # CLI for testing
    project_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    tools = get_project_tool_requirements(project_dir)

    print(f"Detected tools in {project_dir}:\n")
    for name, info in sorted(tools.items()):
        version = info.get("version", "any")
        configured = "✓" if info.get("configured") else " "
        config_file = info.get("config_file", "")
        print(f"  [{configured}] {name:15} version={version:10} {config_file}")
