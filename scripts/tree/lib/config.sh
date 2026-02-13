#!/bin/bash
#
# Script: lib/config.sh
# Purpose: Configuration loading and management for tree worktree system
# Created: 2026-01-28
# Description: Loads configuration from worktree-config.json with environment variable overrides

# Configuration file path (set by main router)
TREE_CONFIG_FILE="${TREE_CONFIG_FILE:-}"

# Cached configuration (loaded once)
_TREE_CONFIG_CACHE=""
_TREE_CONFIG_LOADED=false

# Load configuration from JSON file
# Sets _TREE_CONFIG_CACHE with the parsed JSON
# Returns 0 on success, 1 if file not found (defaults will be used)
load_config() {
    if [ "$_TREE_CONFIG_LOADED" = true ]; then
        return 0
    fi

    local config_file="${TREE_CONFIG_FILE:-$WORKSPACE_ROOT/worktree-config.json}"

    if [ ! -f "$config_file" ]; then
        # Config file is optional - use defaults
        _TREE_CONFIG_CACHE="{}"
        _TREE_CONFIG_LOADED=true
        return 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "Warning: jq not installed, using default configuration" >&2
        _TREE_CONFIG_CACHE="{}"
        _TREE_CONFIG_LOADED=true
        return 1
    fi

    _TREE_CONFIG_CACHE=$(cat "$config_file" 2>/dev/null) || {
        _TREE_CONFIG_CACHE="{}"
        _TREE_CONFIG_LOADED=true
        return 1
    }

    _TREE_CONFIG_LOADED=true
    return 0
}

# Get a configuration value with fallback default
# Usage: get_config_value "path.to.key" "default_value"
# Environment variables override config: TREE_CONFIG_PATH_TO_KEY
get_config_value() {
    local key_path="$1"
    local default_value="${2:-}"

    # Check for environment variable override first
    # Convert path.to.key to TREE_CONFIG_PATH_TO_KEY
    local env_var_name="TREE_CONFIG_$(echo "$key_path" | tr '.' '_' | tr '[:lower:]' '[:upper:]')"
    local env_value="${!env_var_name:-}"

    if [ -n "$env_value" ]; then
        echo "$env_value"
        return 0
    fi

    # Ensure config is loaded
    load_config

    if [ -z "$_TREE_CONFIG_CACHE" ] || [ "$_TREE_CONFIG_CACHE" = "{}" ]; then
        echo "$default_value"
        return 0
    fi

    if ! command -v jq &> /dev/null; then
        echo "$default_value"
        return 0
    fi

    # Query the JSON config
    # Convert dot notation to jq path
    local jq_path=".$(echo "$key_path" | sed 's/\././g')"
    local value
    value=$(echo "$_TREE_CONFIG_CACHE" | jq -r "$jq_path // empty" 2>/dev/null)

    if [ -n "$value" ] && [ "$value" != "null" ]; then
        echo "$value"
    else
        echo "$default_value"
    fi
}

# Get a boolean configuration value
# Usage: get_config_bool "path.to.key" "default_value"
# Returns 0 for true, 1 for false
get_config_bool() {
    local value
    value=$(get_config_value "$1" "$2")

    case "$value" in
        true|True|TRUE|yes|Yes|YES|1)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Get a numeric configuration value
# Usage: get_config_number "path.to.key" "default_value"
get_config_number() {
    local value
    value=$(get_config_value "$1" "$2")

    # Validate it's a number
    if [[ "$value" =~ ^[0-9]+$ ]]; then
        echo "$value"
    else
        echo "$2"
    fi
}

# Get an array configuration value as newline-separated values
# Usage: get_config_array "path.to.array"
get_config_array() {
    local key_path="$1"

    load_config

    if [ -z "$_TREE_CONFIG_CACHE" ] || [ "$_TREE_CONFIG_CACHE" = "{}" ]; then
        return 0
    fi

    if ! command -v jq &> /dev/null; then
        return 0
    fi

    local jq_path=".$key_path"
    echo "$_TREE_CONFIG_CACHE" | jq -r "$jq_path[]? // empty" 2>/dev/null
}

# Get scope patterns for a keyword from config
# Usage: get_scope_patterns "email"
get_scope_patterns() {
    local keyword="$1"
    local patterns

    patterns=$(get_config_array "scope_patterns.$keyword")

    if [ -n "$patterns" ]; then
        echo "$patterns"
    fi
}

# Reload configuration (clear cache and reload)
reload_config() {
    _TREE_CONFIG_CACHE=""
    _TREE_CONFIG_LOADED=false
    load_config
}

# Export configuration defaults (for documentation/initialization)
print_default_config() {
    cat << 'EOF'
{
  "worktree_base_dir": ".trees",
  "base_branch": "main",
  "branch_prefix": {
    "feature": "feature/",
    "bugfix": "bugfix/",
    "hotfix": "hotfix/",
    "task": "task/",
    "experimental": "experimental/"
  },
  "naming_convention": "kebab-case",
  "auto_create_prd": true,
  "prd_location": "tasks/",
  "scope_patterns": {
    "email": ["modules/email_integration/**", "**/email*.py"],
    "database": ["modules/database/**", "**/db*.py"],
    "api": ["modules/api/**", "**/api*.py"],
    "dashboard": ["modules/dashboard/**", "**/dashboard*.py"],
    "auth": ["modules/auth/**", "**/auth*.py"],
    "test": ["tests/**"],
    "doc": ["docs/**", "*.md"]
  },
  "behavior": {
    "auto_commit_on_close": true,
    "auto_push_on_close": true,
    "scope_enforcement": "soft",
    "git_lock_timeout": 30,
    "stale_lock_threshold_seconds": 60
  },
  "tty": {
    "force_interactive": false,
    "force_non_interactive": false
  },
  "created_worktrees": {}
}
EOF
}
