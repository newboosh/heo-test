#!/bin/bash
# shellcheck shell=bash
# GitHub authentication setup - resilient for worktrees
# NOTE: This script is designed to work with both bash and zsh
#
# This script provides a single source of truth for GitHub auth:
# 1. Finds REPO_ORIGIN_URL and REPO_ORIGIN_PAT from multiple sources
# 2. Syncs gh CLI with the found token (with confirmation)
# 3. Works from any worktree depth
#
# Usage:
#   source scripts/github-auth.sh
#   # or with explicit actions:
#   source scripts/github-auth.sh && github_auth_sync
#
# Options (set before sourcing or calling functions):
#   GITHUB_AUTH_FORCE=1    - Skip all confirmation prompts
#   GITHUB_AUTH_NO_SYNC=1  - Don't sync gh CLI automatically
#
# After sourcing:
#   - GITHUB_REPO_OWNER  - Repository owner (e.g., "your-username")
#   - GITHUB_REPO_NAME   - Repository name (e.g., "your-repo")
#   - GITHUB_REPO_URL    - Clean URL (without embedded token)
#   - GITHUB_PAT         - Token for authentication
#   - gh CLI will be authenticated with the same token (if synced)

# NOTE: Do NOT set shell options (set -e, set -o pipefail) here.
# This file is sourced by other scripts and setting global shell options
# would pollute the caller's environment and break pipelines.

# Colors for output (only if terminal)
if [ -t 2 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

_github_auth_log() { echo -e "${BLUE}[github-auth]${NC} $*" >&2; }
_github_auth_warn() { echo -e "${YELLOW}[github-auth]${NC} $*" >&2; }
_github_auth_error() { echo -e "${RED}[github-auth]${NC} $*" >&2; }
_github_auth_success() { echo -e "${GREEN}[github-auth]${NC} $*" >&2; }

# Mask token to prevent leakage (shows first 4 and last 4 chars)
_github_auth_mask_token() {
    local token="$1"
    local head=4
    local tail=4
    if [ ${#token} -le $((head + tail)) ]; then
        echo "***"
        return
    fi
    echo "${token:0:$head}...${token: -$tail}"
}

# Prompt user for confirmation (returns 0 for yes, 1 for no)
# Skips prompt if GITHUB_AUTH_FORCE=1 or not interactive
_github_auth_confirm() {
    local prompt="$1"
    local default="${2:-n}"  # Default to no

    # Skip if force mode
    if [ "${GITHUB_AUTH_FORCE:-0}" = "1" ]; then
        return 0
    fi

    # Skip if not interactive terminal
    if [ ! -t 0 ]; then
        _github_auth_warn "Non-interactive mode, skipping: $prompt"
        return 1
    fi

    local yn_hint="[y/N]"
    [ "$default" = "y" ] && yn_hint="[Y/n]"

    echo -en "${YELLOW}[github-auth]${NC} $prompt $yn_hint " >&2
    read -r response

    case "${response:-$default}" in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

# Show diff between two tokens (masked for safety)
_github_auth_show_token_diff() {
    local label1="$1" token1="$2" label2="$3" token2="$4"
    echo "  $label1: $(_github_auth_mask_token "$token1")" >&2
    echo "  $label2: $(_github_auth_mask_token "$token2")" >&2
}

# Find project root by searching up for .env.local or .git
_find_project_root() {
    local current_dir="${1:-$(pwd)}"
    local max_depth=10
    local depth=0

    # Canonicalize
    current_dir=$(cd "$current_dir" && pwd -P 2>/dev/null) || return 1

    while [ $depth -lt $max_depth ]; do
        # Check for .env.local (primary indicator)
        if [ -f "$current_dir/.env.local" ]; then
            echo "$current_dir"
            return 0
        fi
        # Check for .git directory (secondary indicator, but only real dir not worktree file)
        if [ -d "$current_dir/.git" ]; then
            echo "$current_dir"
            return 0
        fi

        # Move up
        current_dir=$(cd "$current_dir/.." && pwd -P 2>/dev/null) || break
        depth=$((depth + 1))

        [ "$current_dir" = "/" ] && break
    done

    return 1
}

# Extract PAT from a URL like https://PAT@github.com/owner/repo.git
# Uses sed for bash/zsh portability
_extract_pat_from_url() {
    local url="$1"
    local pat
    # Match: https://TOKEN@github.com/...
    pat=$(echo "$url" | sed -nE 's|^https://([^@]+)@github\.com.*|\1|p')
    if [ -n "$pat" ]; then
        echo "$pat"
        return 0
    fi
    return 1
}

# Extract owner/repo from URL (handles embedded PAT)
# Uses sed for bash/zsh portability
_extract_repo_info() {
    local url="$1"
    local result
    # Match: github.com/OWNER/REPO.git or github.com:OWNER/REPO.git
    result=$(echo "$url" | sed -nE 's|.*github\.com[:/]([^/]+)/([^/.]+)(\.git)?.*|\1 \2|p')
    if [ -n "$result" ]; then
        echo "$result"
        return 0
    fi
    return 1
}

# Get clean URL (without embedded token)
_clean_github_url() {
    local url="$1"
    # Replace https://TOKEN@github.com with https://github.com
    echo "$url" | sed -E 's|https://[^@]+@github\.com|https://github.com|'
}

# Main: Detect GitHub auth from all sources
# Prompts before overwriting existing values (unless GITHUB_AUTH_FORCE=1)
github_auth_detect() {
    local project_root
    project_root=$(_find_project_root)

    # Save existing PAT to detect conflicts
    local existing_pat="$GITHUB_PAT"

    # Priority 1: Environment variables (already set via REPO_ORIGIN_*)
    if [ -n "$REPO_ORIGIN_PAT" ] && [ -n "$REPO_ORIGIN_URL" ]; then
        _github_auth_log "Found env vars: REPO_ORIGIN_PAT, REPO_ORIGIN_URL"

        local new_pat="$REPO_ORIGIN_PAT"
        local new_url=$(_clean_github_url "$REPO_ORIGIN_URL")

        # Check if GITHUB_PAT already set and different
        if [ -n "$existing_pat" ] && [ "$existing_pat" != "$new_pat" ]; then
            _github_auth_warn "GITHUB_PAT already set with different value"
            _github_auth_show_token_diff "Current" "$existing_pat" "New (env)" "$new_pat"
            if ! _github_auth_confirm "Overwrite GITHUB_PAT?"; then
                _github_auth_log "Keeping existing GITHUB_PAT"
                new_pat="$existing_pat"
            fi
        fi

        export GITHUB_PAT="$new_pat"
        export GITHUB_REPO_URL="$new_url"

        local repo_info
        repo_info=$(_extract_repo_info "$REPO_ORIGIN_URL")
        if [ -n "$repo_info" ]; then
            export GITHUB_REPO_OWNER="${repo_info%% *}"
            export GITHUB_REPO_NAME="${repo_info##* }"
        fi
        return 0
    fi

    # Priority 2: .env.local file
    if [ -n "$project_root" ] && [ -f "$project_root/.env.local" ]; then
        _github_auth_log "Loading from: $project_root/.env.local"

        # Source with validation (from load-env.sh logic)
        if grep -qE '\$\(|`|;[^=]|&&|\|\|' "$project_root/.env.local"; then
            _github_auth_error ".env.local contains suspicious patterns, skipping"
        else
            # Read values without exporting yet
            local env_pat env_url
            env_pat=$(grep -E '^REPO_ORIGIN_PAT=' "$project_root/.env.local" | cut -d= -f2- | tr -d '"' | tr -d "'")
            env_url=$(grep -E '^REPO_ORIGIN_URL=' "$project_root/.env.local" | cut -d= -f2- | tr -d '"' | tr -d "'")

            # Fall back to legacy variable name
            if [ -z "$env_pat" ]; then
                env_pat=$(grep -E '^GITHUB_PAT=' "$project_root/.env.local" | cut -d= -f2- | tr -d '"' | tr -d "'")
            fi

            # Check for PAT conflict
            if [ -n "$env_pat" ]; then
                if [ -n "$existing_pat" ] && [ "$existing_pat" != "$env_pat" ]; then
                    _github_auth_warn "GITHUB_PAT already set with different value"
                    _github_auth_show_token_diff "Current" "$existing_pat" "New (.env.local)" "$env_pat"
                    if ! _github_auth_confirm "Overwrite GITHUB_PAT?"; then
                        _github_auth_log "Keeping existing GITHUB_PAT"
                    else
                        export GITHUB_PAT="$env_pat"
                    fi
                else
                    export GITHUB_PAT="$env_pat"
                fi
            fi

            # Set URL and repo info
            if [ -n "$env_url" ]; then
                export GITHUB_REPO_URL=$(_clean_github_url "$env_url")
                local repo_info
                repo_info=$(_extract_repo_info "$env_url")
                if [ -n "$repo_info" ]; then
                    export GITHUB_REPO_OWNER="${repo_info%% *}"
                    export GITHUB_REPO_NAME="${repo_info##* }"
                fi
            fi
        fi
    fi

    # Priority 3: Git remote URL (extract embedded PAT if present)
    if [ -z "$GITHUB_PAT" ] || [ -z "$GITHUB_REPO_URL" ]; then
        local remote_url
        remote_url=$(git remote get-url origin 2>/dev/null)

        if [ -n "$remote_url" ]; then
            # Try to extract PAT from URL
            if [ -z "$GITHUB_PAT" ]; then
                local url_pat
                url_pat=$(_extract_pat_from_url "$remote_url")
                if [ -n "$url_pat" ]; then
                    _github_auth_log "Extracted PAT from git remote URL"
                    export GITHUB_PAT="$url_pat"
                fi
            fi

            # Get clean URL and repo info
            if [ -z "$GITHUB_REPO_URL" ]; then
                export GITHUB_REPO_URL=$(_clean_github_url "$remote_url")
            fi

            if [ -z "$GITHUB_REPO_OWNER" ] || [ -z "$GITHUB_REPO_NAME" ]; then
                local repo_info
                repo_info=$(_extract_repo_info "$remote_url")
                if [ -n "$repo_info" ]; then
                    export GITHUB_REPO_OWNER="${repo_info%% *}"
                    export GITHUB_REPO_NAME="${repo_info##* }"
                fi
            fi
        fi
    fi

    # Validate we have minimum needed info
    if [ -z "$GITHUB_PAT" ]; then
        _github_auth_error "No GitHub PAT found!"
        _github_auth_error "Set REPO_ORIGIN_PAT in .env.local or environment"
        return 1
    fi

    if [ -z "$GITHUB_REPO_URL" ]; then
        _github_auth_warn "No GitHub URL found (will use git remote for operations)"
    fi

    return 0
}

# Sync gh CLI with our PAT
# Prompts before overwriting existing gh token (unless GITHUB_AUTH_FORCE=1)
github_auth_sync() {
    # Skip if NO_SYNC is set
    if [ "${GITHUB_AUTH_NO_SYNC:-0}" = "1" ]; then
        _github_auth_log "Skipping gh CLI sync (GITHUB_AUTH_NO_SYNC=1)"
        return 0
    fi

    if [ -z "$GITHUB_PAT" ]; then
        _github_auth_error "No GITHUB_PAT set, cannot sync gh CLI"
        return 1
    fi

    # Check if gh is installed
    if ! command -v gh &>/dev/null; then
        _github_auth_warn "gh CLI not installed, skipping sync"
        return 0
    fi

    # Check current gh auth
    local current_gh_token
    current_gh_token=$(gh auth token 2>/dev/null || echo "")

    # Only sync if different (avoid unnecessary writes)
    if [ "$current_gh_token" = "$GITHUB_PAT" ]; then
        _github_auth_log "gh CLI already synced"
        return 0
    fi

    # Prompt if gh already has a different token
    if [ -n "$current_gh_token" ]; then
        _github_auth_warn "gh CLI has different token"
        _github_auth_show_token_diff "gh CLI" "$current_gh_token" "GITHUB_PAT" "$GITHUB_PAT"
        if ! _github_auth_confirm "Overwrite gh CLI token?"; then
            _github_auth_log "Keeping existing gh CLI token"
            return 0
        fi
    fi

    _github_auth_log "Syncing gh CLI authentication..."
    if echo "$GITHUB_PAT" | gh auth login --with-token 2>/dev/null; then
        _github_auth_success "gh CLI synced successfully"
        return 0
    else
        _github_auth_error "Failed to sync gh CLI"
        return 1
    fi
}

# Show current auth status
github_auth_status() {
    echo "=== GitHub Auth Status ==="
    echo ""

    echo "Environment Variables:"
    [ -n "$GITHUB_PAT" ] && echo "  GITHUB_PAT: $(_github_auth_mask_token "$GITHUB_PAT")" || echo "  GITHUB_PAT: (not set)"
    [ -n "$GITHUB_REPO_URL" ] && echo "  GITHUB_REPO_URL: $GITHUB_REPO_URL" || echo "  GITHUB_REPO_URL: (not set)"
    [ -n "$GITHUB_REPO_OWNER" ] && echo "  GITHUB_REPO_OWNER: $GITHUB_REPO_OWNER" || echo "  GITHUB_REPO_OWNER: (not set)"
    [ -n "$GITHUB_REPO_NAME" ] && echo "  GITHUB_REPO_NAME: $GITHUB_REPO_NAME" || echo "  GITHUB_REPO_NAME: (not set)"
    echo ""

    echo "Git Remote:"
    git remote get-url origin 2>/dev/null | sed -E 's|https://[^@]+@|https://***@|' || echo "  (no remote)"
    echo ""

    echo "gh CLI:"
    gh auth status 2>&1 | head -5 || echo "  (not authenticated)"
    echo ""

    # Check for token mismatch (compare full tokens, not just prefix)
    local gh_token
    gh_token=$(gh auth token 2>/dev/null || echo "")
    if [ -n "$GITHUB_PAT" ] && [ -n "$gh_token" ]; then
        if [ "$GITHUB_PAT" != "$gh_token" ]; then
            echo -e "${YELLOW}WARNING: Token mismatch detected!${NC}"
            echo "  GITHUB_PAT: $(_github_auth_mask_token "$GITHUB_PAT")"
            echo "  gh CLI:     $(_github_auth_mask_token "$gh_token")"
            echo ""
            echo "Run 'github_auth_sync' to fix this"
        else
            echo -e "${GREEN}✓ Tokens are in sync${NC}"
        fi
    fi
}

# Full setup: detect + sync
github_auth_setup() {
    _github_auth_log "Setting up GitHub authentication..."

    if github_auth_detect; then
        github_auth_sync
        _github_auth_success "GitHub auth ready: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
        return 0
    else
        return 1
    fi
}

# Auto-run detection when sourced (but not sync - that's explicit)
# Only run if being sourced (not if being executed directly)
# Support both bash and zsh
if [[ -n "$ZSH_VERSION" ]]; then
    # zsh: check ZSH_EVAL_CONTEXT for sourced file
    [[ "$ZSH_EVAL_CONTEXT" == *:file* ]] && github_auth_detect
elif [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # bash: compare BASH_SOURCE with $0
    github_auth_detect
fi
