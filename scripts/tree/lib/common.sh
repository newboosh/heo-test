#!/bin/bash
#
# Script: lib/common.sh
# Purpose: Common utilities for tree worktree system (colors, output, TTY detection)
# Created: 2026-01-28
# Description: Shared output functions and interactive mode detection

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Unicode characters - use literal UTF-8 for bash 3.2 compatibility
# ($'\u2713' and $'\U0001F333' syntax requires bash 4.0+)
CHECK='✓'
CROSS='✗'
WARN='⚠'
TREE='🌳'

# Output functions
print_header() {
    echo -e "\n${TREE} ${BOLD}$1${NC}\n"
}

print_success() {
    echo -e "${GREEN}${CHECK}${NC} $1"
}

print_error() {
    echo -e "${RED}${CROSS}${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}${WARN}${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# TTY detection functions

# Check if stdin is a terminal
is_tty() {
    [ -t 0 ]
}

# Check if stdout is a terminal
is_tty_output() {
    [ -t 1 ]
}

# Check if we're in interactive mode
# Interactive = stdin is TTY AND stdout is TTY AND not in CI AND not forced non-interactive
is_interactive() {
    # Check config override first
    if [ -n "${TREE_FORCE_INTERACTIVE:-}" ]; then
        return 0
    fi

    if [ -n "${TREE_NON_INTERACTIVE:-}" ] || [ -n "${CI:-}" ]; then
        return 1
    fi

    # Check TTY config from worktree-config.json via config.sh
    if type get_config_bool &>/dev/null; then
        if get_config_bool "tty.force_non_interactive" "false"; then
            return 1
        fi
        if get_config_bool "tty.force_interactive" "false"; then
            return 0
        fi
    fi

    [ -t 0 ] && [ -t 1 ]
}

# Prompt for confirmation with non-interactive fallback
# Usage: confirm_prompt "Proceed with action?" "n"
# First arg: prompt text
# Second arg: default answer for non-interactive mode (y/n), defaults to "n"
confirm_prompt() {
    local prompt="${1:-Continue?}"
    local default="${2:-n}"

    if ! is_interactive; then
        # Non-interactive mode - use default
        if [ "$default" = "y" ] || [ "$default" = "Y" ]; then
            return 0
        fi
        return 1
    fi

    # Interactive mode - prompt user
    local response
    read -p "$prompt [y/N] " -n 1 -r response
    echo  # Move to new line

    [[ $response =~ ^[Yy]$ ]]
}

# Prompt for confirmation with default yes
# Usage: confirm_prompt_yes "Proceed with action?"
confirm_prompt_yes() {
    local prompt="${1:-Continue?}"

    if ! is_interactive; then
        return 0  # Default yes in non-interactive
    fi

    local response
    read -p "$prompt [Y/n] " -n 1 -r response
    echo

    [[ ! $response =~ ^[Nn]$ ]]
}

# Read a line of input with non-interactive fallback
# Usage: read_input "Enter value:" "default_value"
read_input() {
    local prompt="${1:-Enter value:}"
    local default="${2:-}"

    if ! is_interactive; then
        echo "$default"
        return 0
    fi

    local response
    if [ -n "$default" ]; then
        read -p "$prompt [$default] " response
        echo "${response:-$default}"
    else
        read -p "$prompt " response
        echo "$response"
    fi
}

# Display verbose output only when TREE_VERBOSE is set
verbose() {
    if [ "${TREE_VERBOSE:-false}" = "true" ]; then
        echo "[VERBOSE] $*"
    fi
}

# Display debug output only when TREE_DEBUG is set
debug() {
    if [ "${TREE_DEBUG:-false}" = "true" ]; then
        echo "[DEBUG] $*" >&2
    fi
}
