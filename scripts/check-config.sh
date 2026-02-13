#!/bin/bash
# Check if required configuration exists for heo plugin features
# Usage: check-config.sh <feature>
# Features: production, github

FEATURE="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Try to load .env.local from project root
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    set -a
    source "$PROJECT_ROOT/.env.local"
    set +a
fi

check_production() {
    local missing=()

    [ -z "$PRODUCTION_DOMAIN" ] && missing+=("PRODUCTION_DOMAIN")
    [ -z "$PRODUCTION_SERVER_IP" ] && missing+=("PRODUCTION_SERVER_IP")

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${YELLOW}[Heo] Production features require configuration${NC}" >&2
        echo "" >&2
        echo "Missing environment variables:" >&2
        for var in "${missing[@]}"; do
            echo "  - $var" >&2
        done
        echo "" >&2
        echo "To configure, create .env.local in your project root:" >&2
        echo "" >&2
        echo "  PRODUCTION_DOMAIN=your-domain.example.com" >&2
        echo "  PRODUCTION_SERVER_IP=123.45.67.89" >&2
        echo "" >&2
        echo "Or copy the template: cp $PLUGIN_DIR/.env.example .env.local" >&2
        echo "" >&2
        return 1
    fi
    return 0
}

check_github() {
    # Check for new variable name first, then legacy
    if [ -z "$REPO_ORIGIN_PAT" ] && [ -z "$GITHUB_PAT" ]; then
        echo -e "${YELLOW}[Heo] GitHub features require configuration${NC}" >&2
        echo "" >&2
        echo "Missing: REPO_ORIGIN_PAT" >&2
        echo "" >&2
        echo "To configure, add to .env.local:" >&2
        echo "" >&2
        echo "  REPO_ORIGIN_URL=https://github.com/username/repo.git" >&2
        echo "  REPO_ORIGIN_PAT=ghp_xxxxxxxxxxxxxxxxxxxx" >&2
        echo "" >&2
        echo "Create a token at: https://github.com/settings/tokens" >&2
        echo "" >&2
        return 1
    fi
    return 0
}

case "$FEATURE" in
    production)
        check_production
        ;;
    github)
        check_github
        ;;
    all)
        check_production
        check_github
        ;;
    *)
        echo "Unknown feature: $FEATURE" >&2
        exit 1
        ;;
esac
