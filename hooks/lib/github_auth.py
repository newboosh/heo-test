#!/usr/bin/env python3
"""
GitHub authentication utilities for worktree-aware token loading.

This module provides functions to:
1. Find .env.local by searching UP the directory tree (worktree-aware)
2. Load GITHUB_PAT from .env.local or environment
3. Sync gh CLI authentication with the found token
4. Validate that auth is working for the current repo
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class AuthResult:
    """Result of auth validation."""

    has_token: bool
    token_source: Optional[str]  # ".env.local at /path", "env var", "gh cli"
    gh_cli_works: bool
    repo_accessible: bool
    error: Optional[str]
    fix_command: Optional[str]


def find_env_local(start_dir: Path, max_depth: int = 10) -> Optional[Path]:
    """
    Search up directory tree for .env.local.

    This mirrors the behavior of load-env.sh, searching parent directories
    to handle worktree setups where .env.local is in the parent.

    Args:
        start_dir: Directory to start searching from
        max_depth: Maximum number of parent directories to check

    Returns:
        Path to .env.local if found, None otherwise
    """
    current = start_dir.resolve()
    for _ in range(max_depth):
        env_file = current / ".env.local"
        if env_file.exists():
            return env_file
        if current.parent == current:
            break
        current = current.parent
    return None


def load_env_local(env_file: Path) -> Dict[str, str]:
    """
    Parse .env.local file into dict.

    Only parses simple VAR=value lines, ignores comments and empty lines.
    Strips quotes from values.

    Args:
        env_file: Path to .env.local file

    Returns:
        Dict of environment variables
    """
    result = {}
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip().strip("\"'")
    except (OSError, IOError):
        pass
    return result


def get_github_pat(project_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Get GitHub PAT, searching .env.local up the tree.

    Checks in order:
    1. Environment variables (REPO_ORIGIN_PAT, GITHUB_PAT, GITHUB_TOKEN, GH_TOKEN)
    2. .env.local file (searching up directory tree)

    Args:
        project_dir: Project directory to start search from

    Returns:
        Tuple of (token, source_description) or (None, None) if not found
    """
    # Token variable names in priority order (new names first, legacy fallbacks)
    token_vars = ["REPO_ORIGIN_PAT", "GITHUB_PAT", "GITHUB_TOKEN", "GH_TOKEN"]

    # 1. Check environment first
    for var in token_vars:
        token = os.environ.get(var)
        if token:
            return token, f"env var ${var}"

    # 2. Search for .env.local
    env_file = find_env_local(project_dir)
    if env_file:
        env_vars = load_env_local(env_file)
        for var in token_vars:
            token = env_vars.get(var)
            if token:
                return token, f".env.local at {env_file.parent}"

    return None, None


def get_origin_url(project_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Get origin repository URL.

    Checks in order:
    1. Environment variable REPO_ORIGIN_URL
    2. .env.local file (searching up directory tree)
    3. Git remote 'origin' URL (fallback)

    Args:
        project_dir: Project directory to start search from

    Returns:
        Tuple of (url, source_description) or (None, None) if not found
    """
    # 1. Check environment first
    url = os.environ.get("REPO_ORIGIN_URL")
    if url:
        return url, "env var $REPO_ORIGIN_URL"

    # 2. Search for .env.local
    env_file = find_env_local(project_dir)
    if env_file:
        env_vars = load_env_local(env_file)
        url = env_vars.get("REPO_ORIGIN_URL")
        if url:
            return url, f".env.local at {env_file.parent}"

    # 3. Fall back to git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), "git remote origin"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    return None, None


def get_repo_from_remote(project_dir: Path) -> Optional[Tuple[str, str]]:
    """
    Get owner/repo from git remote.

    Args:
        project_dir: Directory to run git command in

    Returns:
        Tuple of (owner, repo) or None if not found
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Match github.com/owner/repo or github.com:owner/repo
            match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", result.stdout)
            if match:
                return match.group(1), match.group(2)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return None


def check_gh_cli_auth() -> Tuple[bool, Optional[str]]:
    """
    Check if gh CLI is authenticated.

    Returns:
        Tuple of (is_authenticated, error_message)
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stderr if result.returncode != 0 else None
    except FileNotFoundError:
        return False, "gh CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "gh auth status timed out"
    except subprocess.SubprocessError as e:
        return False, str(e)


def sync_gh_auth_with_pat(token: str) -> Tuple[bool, Optional[str]]:
    """
    Sync gh CLI auth with provided PAT.

    Args:
        token: GitHub PAT to use for authentication

    Returns:
        Tuple of (success, error_message)
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "login", "--with-token"],
            input=token,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stderr if result.returncode != 0 else None
    except FileNotFoundError:
        return False, "gh CLI not installed"
    except subprocess.TimeoutExpired:
        return False, "gh auth login timed out"
    except subprocess.SubprocessError as e:
        return False, str(e)


def check_repo_access(owner: str, repo: str) -> bool:
    """
    Check if gh CLI can access the specified repo.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        True if accessible, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "repo", "view", f"{owner}/{repo}", "--json", "name"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return False


def validate_github_auth(project_dir: Path, auto_fix: bool = True) -> AuthResult:
    """
    Validate GitHub auth is working for this project.

    This is the main entry point for auth validation. It:
    1. Finds GITHUB_PAT (from env or .env.local)
    2. Checks if gh CLI is authenticated
    3. Checks if the current repo is accessible
    4. Optionally syncs gh CLI auth if needed

    Args:
        project_dir: Project directory (may be worktree subdirectory)
        auto_fix: If True, automatically sync gh CLI auth with found token

    Returns:
        AuthResult with validation status and any errors
    """
    # Get token
    token, token_source = get_github_pat(project_dir)
    if not token:
        return AuthResult(
            has_token=False,
            token_source=None,
            gh_cli_works=False,
            repo_accessible=False,
            error="No REPO_ORIGIN_PAT found in .env.local",
            fix_command="Add REPO_ORIGIN_PAT=<token> to .env.local in project root",
        )

    # Check gh CLI
    gh_works, gh_error = check_gh_cli_auth()

    # Check repo access
    repo_info = get_repo_from_remote(project_dir)
    repo_accessible = False

    if repo_info and gh_works:
        owner, repo = repo_info
        repo_accessible = check_repo_access(owner, repo)

    # Auto-fix if needed
    if auto_fix and token and (not gh_works or not repo_accessible):
        success, error = sync_gh_auth_with_pat(token)
        if success:
            gh_works = True
            # Re-check repo access
            if repo_info:
                repo_accessible = check_repo_access(repo_info[0], repo_info[1])

    return AuthResult(
        has_token=True,
        token_source=token_source,
        gh_cli_works=gh_works,
        repo_accessible=repo_accessible,
        error=None if repo_accessible else "Cannot access repository",
        fix_command=None
        if repo_accessible
        else 'gh auth login --with-token <<< "$GITHUB_PAT"',
    )


# Allow running as script for testing
if __name__ == "__main__":
    import sys

    project_dir = Path.cwd()
    print(f"Project dir: {project_dir}")

    # Find .env.local
    env_file = find_env_local(project_dir)
    if env_file:
        print(f"Found .env.local: {env_file}")
    else:
        print("No .env.local found")

    # Get token
    token, source = get_github_pat(project_dir)
    if token:
        # Mask token - show prefix only for safety
        masked = token[:8] + "..." if len(token) > 8 else "***"
        print(f"Token: {masked} (from {source})")
    else:
        print("No token found")

    # Validate auth
    result = validate_github_auth(project_dir, auto_fix=False)
    print(f"\nAuth Result:")
    print(f"  has_token: {result.has_token}")
    print(f"  token_source: {result.token_source}")
    print(f"  gh_cli_works: {result.gh_cli_works}")
    print(f"  repo_accessible: {result.repo_accessible}")
    if result.error:
        print(f"  error: {result.error}")
    if result.fix_command:
        print(f"  fix: {result.fix_command}")
