#!/bin/bash
# GitHub configuration setup/migration script
#
# This script standardizes GitHub configuration across repos by:
# 1. Detecting existing tokens/URLs from various sources
# 2. Offering to migrate to standard variable names
# 3. Creating/updating .env.local with consistent format
#
# Standard variables:
#   REPO_ORIGIN_URL - Repository URL (https://github.com/owner/repo.git)
#   REPO_ORIGIN_PAT - Personal Access Token for this repo
#
# Usage:
#   ./scripts/github-setup.sh           # Interactive setup
#   ./scripts/github-setup.sh --check   # Just show current config
#   ./scripts/github-setup.sh --fix     # Auto-fix without prompts

set -o pipefail

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' NC=''
fi

log_info() { echo -e "${BLUE}[setup]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[setup]${NC} $*"; }
log_error() { echo -e "${RED}[setup]${NC} $*"; }
log_success() { echo -e "${GREEN}[setup]${NC} $*"; }
log_header() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}\n"; }

# Parse arguments
MODE="interactive"
case "${1:-}" in
    --check) MODE="check" ;;
    --fix) MODE="fix" ;;
    --help|-h)
        echo "Usage: $0 [--check|--fix]"
        echo ""
        echo "Options:"
        echo "  --check  Show current configuration without changes"
        echo "  --fix    Auto-fix configuration without prompts"
        echo "  (none)   Interactive mode - prompt for each change"
        exit 0
        ;;
esac

# Find git root
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$GIT_ROOT" ]; then
    log_error "Not in a git repository"
    exit 1
fi

ENV_FILE="$GIT_ROOT/.env.local"

# Detection results (bash 3.x compatible - using parallel arrays)
TOKEN_SOURCES=()
TOKEN_VARS=()
TOKEN_VALUES=()

URL_SOURCES=()
URL_VARS=()
URL_VALUES=()

#######################################
# Helper Functions
#######################################

add_token() {
    local source="$1" var="$2" value="$3"
    TOKEN_SOURCES+=("$source")
    TOKEN_VARS+=("$var")
    TOKEN_VALUES+=("$value")
}

add_url() {
    local source="$1" var="$2" value="$3"
    URL_SOURCES+=("$source")
    URL_VARS+=("$var")
    URL_VALUES+=("$value")
}

mask_token() {
    local token="$1"
    # Match safer pattern from github-auth.sh
    if [ ${#token} -lt 9 ]; then
        echo "***"
    else
        echo "${token:0:4}...${token: -4}"
    fi
}

#######################################
# Detection Functions
#######################################

detect_from_env_file() {
    local file="$1"
    local source_name="$2"

    [ ! -f "$file" ] && return

    # Token variables to check (supports optional 'export' prefix)
    local var value
    for var in REPO_ORIGIN_PAT GITHUB_PAT GITHUB_TOKEN GH_TOKEN PUBLISH_GITHUB_PAT; do
        value=$(grep -E "^(export[[:space:]]+)?${var}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
        if [ -n "$value" ]; then
            add_token "$source_name" "$var" "$value"
        fi
    done

    # URL variables to check (supports optional 'export' prefix)
    for var in REPO_ORIGIN_URL GITHUB_URL PUBLISH_GITHUB_URL; do
        value=$(grep -E "^(export[[:space:]]+)?${var}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
        if [ -n "$value" ]; then
            add_url "$source_name" "$var" "$value"
        fi
    done
}

detect_from_git_remote() {
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null)
    [ -z "$remote_url" ] && return

    # Extract PAT if embedded in URL
    local embedded_pat
    embedded_pat=$(echo "$remote_url" | sed -nE 's|^https://([^@]+)@github\.com.*|\1|p')
    if [ -n "$embedded_pat" ]; then
        add_token "git-remote" "embedded" "$embedded_pat"
    fi

    # Store clean URL
    local clean_url
    clean_url=$(echo "$remote_url" | sed -E 's|https://[^@]+@github\.com|https://github.com|')
    add_url "git-remote" "origin" "$clean_url"
}

detect_from_gh_cli() {
    command -v gh &>/dev/null || return

    local gh_token
    gh_token=$(gh auth token 2>/dev/null)
    if [ -n "$gh_token" ]; then
        add_token "gh-cli" "keyring" "$gh_token"
    fi
}

detect_from_environment() {
    local var value
    for var in REPO_ORIGIN_PAT GITHUB_PAT GITHUB_TOKEN GH_TOKEN; do
        eval "value=\${$var:-}"
        if [ -n "$value" ]; then
            add_token "env" "$var" "$value"
        fi
    done

    if [ -n "${REPO_ORIGIN_URL:-}" ]; then
        add_url "env" "REPO_ORIGIN_URL" "$REPO_ORIGIN_URL"
    fi
}

#######################################
# Display Functions
#######################################

show_detected_config() {
    log_header "Detected GitHub Configuration"

    echo -e "${BOLD}Tokens found:${NC}"
    if [ ${#TOKEN_VALUES[@]} -eq 0 ]; then
        echo "  (none)"
    else
        local i
        for i in "${!TOKEN_VALUES[@]}"; do
            echo -e "  ${CYAN}${TOKEN_SOURCES[$i]}${NC} / ${YELLOW}${TOKEN_VARS[$i]}${NC}: $(mask_token "${TOKEN_VALUES[$i]}")"
        done
    fi

    echo ""
    echo -e "${BOLD}URLs found:${NC}"
    if [ ${#URL_VALUES[@]} -eq 0 ]; then
        echo "  (none)"
    else
        local i display_url
        for i in "${!URL_VALUES[@]}"; do
            display_url=$(echo "${URL_VALUES[$i]}" | sed -E 's|https://[^@]+@|https://***@|')
            echo -e "  ${CYAN}${URL_SOURCES[$i]}${NC} / ${YELLOW}${URL_VARS[$i]}${NC}: $display_url"
        done
    fi
}

show_recommendations() {
    log_header "Recommendations"

    local issues=0

    # Check for token inconsistency
    local unique_tokens=()
    local i j found
    for i in "${!TOKEN_VALUES[@]}"; do
        found=0
        for j in "${!unique_tokens[@]}"; do
            [ "${unique_tokens[$j]}" = "${TOKEN_VALUES[$i]}" ] && found=1 && break
        done
        [ $found -eq 0 ] && unique_tokens+=("${TOKEN_VALUES[$i]}")
    done

    if [ ${#unique_tokens[@]} -gt 1 ]; then
        log_warn "Multiple different tokens detected (${#unique_tokens[@]} unique)"
        echo "  This can cause auth failures when different tools use different tokens"
        ((issues++))
    fi

    # Check for non-standard variable names
    local has_standard_token=0
    local has_standard_url=0
    for i in "${!TOKEN_VARS[@]}"; do
        [ "${TOKEN_VARS[$i]}" = "REPO_ORIGIN_PAT" ] && has_standard_token=1
    done
    for i in "${!URL_VARS[@]}"; do
        [ "${URL_VARS[$i]}" = "REPO_ORIGIN_URL" ] && has_standard_url=1
    done

    if [ $has_standard_token -eq 0 ] && [ ${#TOKEN_VALUES[@]} -gt 0 ]; then
        log_warn "No REPO_ORIGIN_PAT found (using legacy variable names)"
        echo "  Standard name: REPO_ORIGIN_PAT"
        ((issues++))
    fi

    if [ $has_standard_url -eq 0 ] && [ ${#URL_VALUES[@]} -gt 0 ]; then
        log_warn "No REPO_ORIGIN_URL found"
        echo "  Standard name: REPO_ORIGIN_URL"
        ((issues++))
    fi

    # Check for embedded token in remote
    for i in "${!TOKEN_VARS[@]}"; do
        if [ "${TOKEN_SOURCES[$i]}" = "git-remote" ] && [ "${TOKEN_VARS[$i]}" = "embedded" ]; then
            log_warn "Token embedded in git remote URL"
            echo "  This exposes the token in 'git remote -v' output"
            ((issues++))
        fi
    done

    # Check for missing .env.local
    if [ ! -f "$ENV_FILE" ]; then
        log_warn "No .env.local file found at $GIT_ROOT"
        ((issues++))
    fi

    if [ $issues -eq 0 ]; then
        log_success "Configuration looks good!"
    else
        echo ""
        log_info "Run '$0 --fix' to auto-fix or '$0' for interactive mode"
    fi

    return $issues
}

#######################################
# Fix Functions
#######################################

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    if [ "$MODE" = "fix" ]; then
        return 0  # Auto-yes in fix mode
    fi

    local yn_hint="[y/N]"
    [ "$default" = "y" ] && yn_hint="[Y/n]"

    echo -en "$prompt $yn_hint "
    read -r response

    case "${response:-$default}" in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

select_token() {
    echo ""
    echo "Select which token to use as REPO_ORIGIN_PAT:"

    local i
    for i in "${!TOKEN_VALUES[@]}"; do
        echo "  $((i+1))) ${TOKEN_SOURCES[$i]} / ${TOKEN_VARS[$i]}: $(mask_token "${TOKEN_VALUES[$i]}")"
    done
    echo "  $((${#TOKEN_VALUES[@]}+1))) Enter a new token"

    echo -n "Choice [1]: "
    read -r choice
    choice="${choice:-1}"

    if [ "$choice" = "$((${#TOKEN_VALUES[@]}+1))" ]; then
        echo -n "Enter new token: "
        read -r new_token
        echo "$new_token"
    elif [ "$choice" -ge 1 ] && [ "$choice" -le "${#TOKEN_VALUES[@]}" ]; then
        echo "${TOKEN_VALUES[$((choice-1))]}"
    else
        echo "${TOKEN_VALUES[0]}"
    fi
}

select_url() {
    echo ""
    echo "Select which URL to use as REPO_ORIGIN_URL:"

    local i display_url
    for i in "${!URL_VALUES[@]}"; do
        display_url=$(echo "${URL_VALUES[$i]}" | sed -E 's|https://[^@]+@|https://***@|')
        echo "  $((i+1))) ${URL_SOURCES[$i]} / ${URL_VARS[$i]}: $display_url"
    done
    echo "  $((${#URL_VALUES[@]}+1))) Enter a new URL"

    echo -n "Choice [1]: "
    read -r choice
    choice="${choice:-1}"

    if [ "$choice" = "$((${#URL_VALUES[@]}+1))" ]; then
        echo -n "Enter new URL: "
        read -r new_url
        echo "$new_url"
    elif [ "$choice" -ge 1 ] && [ "$choice" -le "${#URL_VALUES[@]}" ]; then
        # Return clean URL
        echo "${URL_VALUES[$((choice-1))]}" | sed -E 's|https://[^@]+@github\.com|https://github.com|'
    else
        echo "${URL_VALUES[0]}" | sed -E 's|https://[^@]+@github\.com|https://github.com|'
    fi
}

update_env_file() {
    local token="$1"
    local url="$2"

    log_info "Updating $ENV_FILE"

    # Create backup if file exists
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "${ENV_FILE}.backup"
        log_info "Backup created: ${ENV_FILE}.backup"
    fi

    # Read existing content (excluding old GitHub vars, including exported forms)
    local other_content=""
    if [ -f "$ENV_FILE" ]; then
        other_content=$(grep -vE '^(export[[:space:]]+)?(REPO_ORIGIN_PAT|REPO_ORIGIN_URL|GITHUB_PAT|GITHUB_TOKEN|GH_TOKEN|GITHUB_URL)=' "$ENV_FILE" | grep -v '^#.*GitHub' | grep -v '^$' || true)
    fi

    # Write new file
    {
        echo "# GitHub configuration (standardized by github-setup.sh)"
        echo "REPO_ORIGIN_URL=$url"
        echo "REPO_ORIGIN_PAT=$token"
        if [ -n "$other_content" ]; then
            echo ""
            echo "# Other configuration"
            echo "$other_content"
        fi
    } > "$ENV_FILE"

    log_success "Updated $ENV_FILE"
}

sync_gh_cli() {
    local token="$1"

    command -v gh &>/dev/null || return

    local current_gh_token
    current_gh_token=$(gh auth token 2>/dev/null || echo "")

    if [ "$current_gh_token" = "$token" ]; then
        log_info "gh CLI already synced"
        return
    fi

    if prompt_yes_no "Sync gh CLI with this token?"; then
        if echo "$token" | gh auth login --with-token 2>/dev/null; then
            log_success "gh CLI synced"
        else
            log_error "Failed to sync gh CLI"
        fi
    fi
}

clean_git_remote() {
    local current_remote
    current_remote=$(git remote get-url origin 2>/dev/null)

    # Check if remote has embedded token
    if echo "$current_remote" | grep -qE 'https://[^@]+@github\.com'; then
        if prompt_yes_no "Remove embedded token from git remote URL?"; then
            local clean_url
            clean_url=$(echo "$current_remote" | sed -E 's|https://[^@]+@github\.com|https://github.com|')
            git remote set-url origin "$clean_url"
            log_success "Git remote cleaned: $clean_url"
            log_info "Git will now use gh CLI or credential helper for auth"
        fi
    fi
}

#######################################
# Main
#######################################

main() {
    log_header "GitHub Configuration Setup"
    log_info "Repository: $GIT_ROOT"

    # Run detection
    log_info "Detecting existing configuration..."
    detect_from_env_file "$ENV_FILE" ".env.local"
    detect_from_env_file "$GIT_ROOT/.env" ".env"
    detect_from_git_remote
    detect_from_gh_cli
    detect_from_environment

    # Show what we found
    show_detected_config

    # Check mode
    if [ "$MODE" = "check" ]; then
        show_recommendations
        exit $?
    fi

    # Interactive or fix mode
    show_recommendations

    local token url

    if [ ${#TOKEN_VALUES[@]} -eq 0 ]; then
        log_error "No tokens found. Please provide a GitHub PAT."
        echo -n "Enter GitHub PAT: "
        read -r token
        [ -z "$token" ] && exit 1
    else
        if [ "$MODE" = "fix" ]; then
            # Auto-select: prefer REPO_ORIGIN_PAT, then first found
            token=""
            for i in "${!TOKEN_VARS[@]}"; do
                if [ "${TOKEN_VARS[$i]}" = "REPO_ORIGIN_PAT" ]; then
                    token="${TOKEN_VALUES[$i]}"
                    break
                fi
            done
            [ -z "$token" ] && token="${TOKEN_VALUES[0]}"
        else
            token=$(select_token)
        fi
    fi

    if [ ${#URL_VALUES[@]} -eq 0 ]; then
        log_error "No URLs found. Please provide the GitHub repo URL."
        echo -n "Enter GitHub URL (https://github.com/owner/repo.git): "
        read -r url
        [ -z "$url" ] && exit 1
    else
        if [ "$MODE" = "fix" ]; then
            # Auto-select: prefer REPO_ORIGIN_URL, then git remote
            url=""
            for i in "${!URL_VARS[@]}"; do
                if [ "${URL_VARS[$i]}" = "REPO_ORIGIN_URL" ]; then
                    url="${URL_VALUES[$i]}"
                    break
                fi
            done
            [ -z "$url" ] && url="${URL_VALUES[0]}"
            # Clean embedded tokens
            url=$(echo "$url" | sed -E 's|https://[^@]+@github\.com|https://github.com|')
        else
            url=$(select_url)
        fi
    fi

    log_header "Configuration to Apply"
    echo "  REPO_ORIGIN_URL: $url"
    echo "  REPO_ORIGIN_PAT: $(mask_token "$token")"
    echo ""

    if ! prompt_yes_no "Apply this configuration?" "y"; then
        log_info "Aborted"
        exit 0
    fi

    # Apply changes
    update_env_file "$token" "$url"
    sync_gh_cli "$token"
    clean_git_remote

    log_header "Setup Complete"
    log_success "GitHub configuration standardized"
    echo ""
    echo "Standard variables set in .env.local:"
    echo "  REPO_ORIGIN_URL - Repository URL"
    echo "  REPO_ORIGIN_PAT - Personal Access Token"
}

main "$@"
