#!/bin/bash
# Load environment from project root
#
# This script finds and sources .env.local from the project root,
# which may be in a parent directory (especially for worktrees).
#
# Usage:
#   source /path/to/load-env.sh
#   # or in a script:
#   source "$(dirname "${BASH_SOURCE[0]}")/load-env.sh"
#
# After sourcing, these variables will be available:
#   - REPO_ORIGIN_URL (origin repository URL)
#   - REPO_ORIGIN_PAT (token for git operations)
#   - GITHUB_PAT (legacy, still supported)
#   - PRODUCTION_* (for deployment scripts)
#   - All other .env.local variables
#
# Exit codes:
#   0 - Successfully loaded .env.local
#   1 - .env.local not found (non-fatal, continue with env vars)

find_and_load_env() {
    local current_dir="$1"
    local max_depth=10
    local depth=0

    # Start from current directory if not provided
    if [ -z "$current_dir" ]; then
        current_dir="$(pwd)"
    fi

    # CRITICAL FIX #10: Canonicalize path to prevent symlink attacks
    if ! current_dir=$(cd "$current_dir" && pwd -P 2>/dev/null); then
        echo "Error: Unable to resolve directory: $current_dir" >&2
        return 1
    fi

    local start_dir="$current_dir"

    # Search up the directory tree for .env.local
    while [ $depth -lt $max_depth ]; do
        if [ -f "$current_dir/.env.local" ]; then
            # CRITICAL FIX #3: Validate .env.local before sourcing
            if ! validate_env_file "$current_dir/.env.local"; then
                return 1
            fi

            # Found .env.local, load it
            set -a
            # shellcheck source=/dev/null
            source "$current_dir/.env.local"
            set +a

            # FIX #5: Only export variables that are actually set
            [ -n "$REPO_ORIGIN_URL" ] && export REPO_ORIGIN_URL
            [ -n "$REPO_ORIGIN_PAT" ] && export REPO_ORIGIN_PAT
            [ -n "$GITHUB_PAT" ] && export GITHUB_PAT  # Legacy support
            [ -n "$PRODUCTION_DOMAIN" ] && export PRODUCTION_DOMAIN
            [ -n "$PRODUCTION_SERVER_IP" ] && export PRODUCTION_SERVER_IP
            [ -n "$SSH_USER" ] && export SSH_USER
            [ -n "$SSH_KEY_NAME" ] && export SSH_KEY_NAME
            [ -n "$APP_NAME" ] && export APP_NAME
            [ -n "$COMPOSE_PROJECT" ] && export COMPOSE_PROJECT

            return 0
        fi

        # Move up one directory
        current_dir="$(cd "$current_dir/.." && pwd -P 2>/dev/null)" || break
        depth=$((depth + 1))

        # Stop at filesystem root
        if [ "$current_dir" = "/" ]; then
            break
        fi
    done

    # .env.local not found, but don't error
    # Variables may be set in shell environment already
    return 1
}

# CRITICAL FIX #3: Validate .env.local contains only safe content
validate_env_file() {
    local env_file="$1"

    if [ ! -f "$env_file" ]; then
        echo "Error: .env.local file not found: $env_file" >&2
        return 1
    fi

    # Check for dangerous patterns that could indicate command injection
    if grep -qE '\$\(|`|;[^=]|&&|\|\||[^=]>' "$env_file"; then
        echo "Error: .env.local contains suspicious patterns (possible command injection)" >&2
        echo "Only VAR=value format is allowed" >&2
        return 1
    fi

    # Verify file only contains comments and VAR=value lines
    if ! grep -vE '^\s*(#|$|[A-Z_][A-Z0-9_]*=)' "$env_file" | grep -q .; then
        # File is clean
        return 0
    fi

    echo "Error: .env.local contains invalid syntax. Only VAR=value lines allowed." >&2
    return 1
}

# Helper: Check if required variables are loaded
verify_github_token() {
    # Check for new variable name first, then legacy
    if [ -z "$REPO_ORIGIN_PAT" ] && [ -z "$GITHUB_PAT" ]; then
        echo "Error: REPO_ORIGIN_PAT not found in environment" >&2
        echo "Make sure .env.local exists in project root with REPO_ORIGIN_PAT=<token>" >&2
        return 1
    fi
    return 0
}

verify_production_config() {
    local missing=()

    [ -z "$PRODUCTION_DOMAIN" ] && missing+=("PRODUCTION_DOMAIN")
    [ -z "$PRODUCTION_SERVER_IP" ] && missing+=("PRODUCTION_SERVER_IP")

    if [ ${#missing[@]} -gt 0 ]; then
        echo "Error: Missing required variables: ${missing[*]}" >&2
        return 1
    fi
    return 0
}

# Auto-load when sourced
find_and_load_env "$(pwd)"
