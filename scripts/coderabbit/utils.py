#!/usr/bin/env python3
"""Shared utilities for CodeRabbit integration scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_repo_root() -> Path:
    """Get the git repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return Path(result.stdout.strip())


def load_env() -> dict[str, str]:
    """Load environment variables, searching up tree for .env.local.

    This is worktree-aware: it searches parent directories to find .env.local,
    which may be located above the worktree directory.
    """
    env = dict(os.environ)

    # Try to use github_auth module for worktree-aware loading
    try:
        hooks_lib = Path(__file__).parent.parent.parent / "hooks" / "lib"
        if hooks_lib.exists():
            hooks_lib_str = str(hooks_lib)
            if hooks_lib_str not in sys.path:
                sys.path.append(hooks_lib_str)
            from github_auth import find_env_local, load_env_local

            repo_root = get_repo_root()
            env_file = find_env_local(repo_root)
            if env_file:
                env.update(load_env_local(env_file))
            return env
    except ImportError:
        pass

    # Fallback: search up directory tree for .env.local (worktree-aware)
    repo_root = get_repo_root()
    current = repo_root
    found_env_file = None

    # Search up to 10 parent directories for .env.local
    for _ in range(10):
        for name in [".env.local", ".env"]:
            env_file = current / name
            if env_file.exists():
                found_env_file = env_file
                break
        if found_env_file:
            break
        if current.parent == current:
            break
        current = current.parent

    if found_env_file:
        with open(found_env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    # Strip optional "export " prefix
                    if line.lower().startswith("export "):
                        line = line[7:].lstrip()
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    env[key] = value

    return env


def get_github_token() -> str:
    """Get GitHub token from environment or .env file."""
    env = load_env()

    for key in ["REPO_ORIGIN_PAT", "GITHUB_TOKEN", "GITHUB_PAT", "GH_TOKEN"]:
        if key in env and env[key]:
            return env[key]

    # Try gh auth token as fallback
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        pass

    raise RuntimeError(
        "No GitHub token found. Set GITHUB_TOKEN env var or run 'gh auth login'"
    )


# Track if we've already synced gh CLI this session
_gh_auth_synced = False


def ensure_gh_auth() -> None:
    """Ensure gh CLI is authenticated with the correct token.

    This syncs the gh CLI with the token from .env.local if they differ.
    Only syncs once per session to avoid repeated subprocess calls.
    """
    global _gh_auth_synced
    if _gh_auth_synced:
        return

    try:
        token = get_github_token()
    except RuntimeError:
        # No token available, can't sync (allow retry later)
        return

    # Check current gh token
    gh_available = True
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_token = result.stdout.strip()
    except subprocess.CalledProcessError:
        # gh installed but not authenticated
        current_token = ""
    except FileNotFoundError:
        # gh not installed
        gh_available = False
        current_token = ""

    if not gh_available:
        return

    # Sync if different
    if current_token != token:
        try:
            subprocess.run(
                ["gh", "auth", "login", "--with-token"],
                input=token,
                capture_output=True,
                text=True,
                check=True,
            )
            eprint("[utils] Synced gh CLI with project token")
            _gh_auth_synced = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            eprint(f"[utils] Warning: Failed to sync gh CLI: {e}")
            return
    else:
        _gh_auth_synced = True


def run_gh_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result.

    Automatically ensures gh CLI is authenticated with the project token.
    """
    # Ensure gh CLI is synced with project token before running commands
    ensure_gh_auth()

    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=False,
    )

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["gh"] + args, result.stdout, result.stderr
        )

    return result


def gh_api(
    endpoint: str,
    method: str = "GET",
    data: dict | None = None,
    headers: dict | None = None,
    fields: dict | None = None,
) -> Any:
    """Make a GitHub API call using gh CLI.

    Args:
        endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/pulls")
        method: HTTP method (GET, POST, PATCH, DELETE)
        data: JSON body data (sent via stdin)
        headers: Additional headers
        fields: Form fields (-f key=value pairs)
    """
    args = ["api", endpoint, "--method", method]

    if headers:
        for key, value in headers.items():
            args.extend(["-H", f"{key}: {value}"])

    if fields:
        for key, value in fields.items():
            args.extend(["-f", f"{key}={value}"])

    if data:
        # Use stdin for JSON body data
        json_data = json.dumps(data)
        result = subprocess.run(
            ["gh"] + args + ["--input", "-"],
            input=json_data,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, ["gh"] + args, result.stdout, result.stderr
            )
    else:
        result = run_gh_command(args)

    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


def gh_api_graphql(query: str, variables: dict | None = None) -> Any:
    """Make a GraphQL query using gh CLI."""
    args = ["api", "graphql", "-f", f"query={query}"]

    if variables:
        for key, value in variables.items():
            if isinstance(value, bool):
                args.extend(["-F", f"{key}={str(value).lower()}"])
            elif isinstance(value, int):
                args.extend(["-F", f"{key}={value}"])
            else:
                args.extend(["-f", f"{key}={value}"])

    result = run_gh_command(args)
    return json.loads(result.stdout)


def gh_api_graphql_paginated(
    query: str,
    variables: dict | None = None,
    path_to_connection: List[str] = None,
    max_pages: int = 10,
) -> Any:
    """Make a paginated GraphQL query, fetching all pages.

    Args:
        query: GraphQL query with $cursor variable and pageInfo { hasNextPage endCursor }
        variables: Query variables (cursor will be added/updated automatically)
        path_to_connection: Path to the connection object in response (e.g., ["repository", "pullRequest", "reviewThreads"])
        max_pages: Maximum number of pages to fetch (safety limit)

    Returns:
        Combined result with all nodes from all pages
    """
    if path_to_connection is None:
        # No pagination path specified, just do single query
        return gh_api_graphql(query, variables)

    variables = dict(variables) if variables else {}
    all_nodes = []
    cursor = None

    for _ in range(max_pages):
        if cursor:
            variables["cursor"] = cursor

        result = gh_api_graphql(query, variables)

        # Navigate to the connection object
        connection = result
        try:
            for key in ["data"] + path_to_connection:
                connection = connection[key]
        except (KeyError, TypeError):
            break

        # Collect nodes
        nodes = connection.get("nodes", [])
        all_nodes.extend(nodes)

        # Check for next page
        page_info = connection.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break

    # Reconstruct result with all nodes
    # Note: This returns a simplified structure with just the nodes
    return {"nodes": all_nodes, "totalCount": len(all_nodes)}


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout.strip()


def get_pr_for_branch(branch: str | None = None) -> int | None:
    """Get the PR number for a branch, or None if no PR exists."""
    if branch is None:
        branch = get_current_branch()

    result = run_gh_command(
        ["pr", "view", branch, "--json", "number", "-q", ".number"],
        check=False,
    )

    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip())
    return None


def get_repo_info() -> tuple[str, str]:
    """Get the owner and repo name from the current git remote."""
    result = run_gh_command(["repo", "view", "--json", "owner,name"])
    data = json.loads(result.stdout)
    return data["owner"]["login"], data["name"]


def eprint(*args, **kwargs):
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


def output_json(data: Any, pretty: bool = False):
    """Output data as JSON to stdout."""
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))
