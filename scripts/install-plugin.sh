#!/bin/bash
# ============================================================================
# Heo Plugin Installer
# ============================================================================
# Installs the heo plugin from the private newboosh/heo repo.
#
# Usage:
#   bash install-plugin.sh                    # Interactive install
#   bash install-plugin.sh --key /path/to/key # Use existing deploy key
#   bash install-plugin.sh --pat ghp_xxx      # Use GitHub PAT instead
#   bash install-plugin.sh --dir ~/my-plugin  # Custom install directory
#
# Prerequisites:
#   - git
#   - claude (Claude Code CLI)
#   - ssh (for deploy key auth) OR a GitHub PAT with repo scope
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Defaults
INSTALL_DIR="${HOME}/.heo-plugin"
DEPLOY_KEY=""
GITHUB_PAT=""
REPO="newboosh/heo"
SSH_ALIAS="heo.github.com"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --key)
            if [[ -z "${2:-}" ]] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --key requires a file path${NC}" >&2
                exit 1
            fi
            DEPLOY_KEY="$2"
            shift 2
            ;;
        --pat)
            if [[ -z "${2:-}" ]] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --pat requires a token value${NC}" >&2
                exit 1
            fi
            GITHUB_PAT="$2"
            shift 2
            ;;
        --dir)
            if [[ -z "${2:-}" ]] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --dir requires a directory path${NC}" >&2
                exit 1
            fi
            INSTALL_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: bash install-plugin.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --key <path>    Path to SSH deploy key for newboosh/heo"
            echo "  --pat <token>   GitHub PAT with repo scope (alternative to deploy key)"
            echo "  --dir <path>    Install directory (default: ~/.heo-plugin)"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
step() { echo -e "\n${BLUE}[$1/${TOTAL_STEPS}]${NC} ${BOLD}$2${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

# Setup SSH config alias for the deploy key
# Usage: setup_ssh_config /absolute/path/to/key
setup_ssh_config() {
    local key_path="$1"
    if grep -q "Host ${SSH_ALIAS}" ~/.ssh/config 2>/dev/null; then
        ok "SSH alias '${SSH_ALIAS}' already configured"
    else
        echo -e "  ${CYAN}Adding SSH alias '${SSH_ALIAS}' to ~/.ssh/config${NC}"
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        cat >> ~/.ssh/config << EOF

# Heo plugin deploy key (added by install-plugin.sh)
Host ${SSH_ALIAS}
    HostName github.com
    User git
    IdentityFile ${key_path}
    IdentitiesOnly yes
EOF
        chmod 600 ~/.ssh/config
        ok "SSH config updated"
    fi
}

TOTAL_STEPS=5

# ============================================================================
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║     Heo Plugin Installer         ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"
# ============================================================================

# ---------------------------------------------------------------------------
step 1 "Checking prerequisites"
# ---------------------------------------------------------------------------

# Check git
if command -v git &>/dev/null; then
    ok "git found: $(git --version | head -1)"
else
    fail "git not found. Install git first."
fi

# Check claude
if command -v claude &>/dev/null; then
    ok "claude found: $(claude --version 2>/dev/null || echo 'installed')"
else
    warn "claude (Claude Code) not found in PATH"
    warn "Install from: https://docs.anthropic.com/en/docs/claude-code"
    echo ""
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Check ssh
if command -v ssh &>/dev/null; then
    ok "ssh found"
else
    warn "ssh not found — you'll need a GitHub PAT for auth"
fi

# ---------------------------------------------------------------------------
step 2 "Configuring authentication"
# ---------------------------------------------------------------------------

CLONE_URL=""

if [[ -n "$GITHUB_PAT" ]]; then
    # PAT auth mode
    ok "Using GitHub PAT authentication"
    CLONE_URL="https://${GITHUB_PAT}@github.com/${REPO}.git"

elif [[ -n "$DEPLOY_KEY" ]]; then
    # Deploy key provided via --key
    if [[ ! -f "$DEPLOY_KEY" ]]; then
        fail "Deploy key not found: $DEPLOY_KEY"
    fi
    ok "Using deploy key: $DEPLOY_KEY"

    ABSOLUTE_KEY="$(cd "$(dirname "$DEPLOY_KEY")" && pwd)/$(basename "$DEPLOY_KEY")"
    setup_ssh_config "$ABSOLUTE_KEY"

    CLONE_URL="git@${SSH_ALIAS}:${REPO}.git"

    # Test SSH connection
    echo -e "  ${CYAN}Testing SSH connection...${NC}"
    if ssh -T "git@${SSH_ALIAS}" 2>&1 | grep -qi "successfully authenticated"; then
        ok "SSH authentication successful"
    else
        warn "SSH test inconclusive — clone may still work"
    fi

else
    # Interactive: ask user which auth method
    echo ""
    echo -e "  The ${BOLD}newboosh/heo${NC} repo is ${YELLOW}private${NC}. Choose auth method:"
    echo ""
    echo -e "  ${BOLD}1)${NC} SSH deploy key (recommended)"
    echo -e "     You need the ${CYAN}deploy_heo${NC} private key file"
    echo ""
    echo -e "  ${BOLD}2)${NC} GitHub PAT"
    echo -e "     A personal access token with ${CYAN}repo${NC} scope"
    echo ""
    read -p "  Choose [1/2]: " -n 1 -r AUTH_CHOICE
    echo ""

    case "$AUTH_CHOICE" in
        1)
            echo ""
            read -p "  Path to deploy_heo private key: " DEPLOY_KEY
            DEPLOY_KEY="${DEPLOY_KEY/#\~/$HOME}"  # expand tilde

            if [[ ! -f "$DEPLOY_KEY" ]]; then
                fail "File not found: $DEPLOY_KEY"
            fi

            ABSOLUTE_KEY="$(cd "$(dirname "$DEPLOY_KEY")" && pwd)/$(basename "$DEPLOY_KEY")"
            setup_ssh_config "$ABSOLUTE_KEY"

            CLONE_URL="git@${SSH_ALIAS}:${REPO}.git"
            ;;
        2)
            echo ""
            read -sp "  GitHub PAT: " GITHUB_PAT
            echo ""
            if [[ -z "$GITHUB_PAT" ]]; then
                fail "No PAT provided"
            fi
            CLONE_URL="https://${GITHUB_PAT}@github.com/${REPO}.git"
            ok "Using PAT authentication"
            ;;
        *)
            fail "Invalid choice"
            ;;
    esac
fi

# ---------------------------------------------------------------------------
step 3 "Cloning plugin"
# ---------------------------------------------------------------------------

if [[ -d "$INSTALL_DIR/.claude-plugin" ]]; then
    warn "Plugin already installed at: $INSTALL_DIR"
    read -p "  Update existing installation? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "  ${CYAN}Pulling latest...${NC}"
        git -C "$INSTALL_DIR" pull --ff-only 2>&1 | head -5
        ok "Plugin updated"
    else
        ok "Keeping existing installation"
    fi
else
    echo -e "  ${CYAN}Cloning to: $INSTALL_DIR${NC}"
    if git clone "$CLONE_URL" "$INSTALL_DIR" 2>&1; then
        ok "Plugin cloned successfully"
        # Sanitize: remove PAT from the stored remote URL
        if [[ -n "$GITHUB_PAT" ]]; then
            git -C "$INSTALL_DIR" remote set-url origin "https://github.com/${REPO}.git"
            ok "Remote URL sanitized (PAT removed from .git/config)"
        fi
    else
        fail "Clone failed. Check your auth credentials."
    fi
fi

# Verify plugin structure
if [[ -f "$INSTALL_DIR/.claude-plugin/plugin.json" ]]; then
    VERSION=$(grep '"version"' "$INSTALL_DIR/.claude-plugin/plugin.json" | head -1 | sed 's/.*: *"\(.*\)".*/\1/')
    ok "Plugin verified: heo v${VERSION}"
else
    fail "Plugin structure invalid — missing .claude-plugin/plugin.json"
fi

# ---------------------------------------------------------------------------
step 4 "Setting up shell aliases"
# ---------------------------------------------------------------------------

SHELL_RC=""
if [[ -f "$HOME/.zshrc" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

ALIAS_LINE="source \"${INSTALL_DIR}/scripts/shell-alias.sh\""

if [[ -n "$SHELL_RC" ]]; then
    if grep -qF "shell-alias.sh" "$SHELL_RC" 2>/dev/null; then
        ok "Shell aliases already configured in $(basename "$SHELL_RC")"
    else
        echo ""
        echo -e "  Add aliases to ${BOLD}$(basename "$SHELL_RC")${NC}?"
        echo -e "  This enables: ${CYAN}claude-heo${NC} (ch) and ${CYAN}claude-heo-tree${NC} (cht)"
        echo ""
        read -p "  Add aliases? (Y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "" >> "$SHELL_RC"
            echo "# Heo plugin aliases" >> "$SHELL_RC"
            echo "$ALIAS_LINE" >> "$SHELL_RC"
            ok "Added to $(basename "$SHELL_RC")"
            warn "Run 'source $(basename "$SHELL_RC")' or open a new terminal to activate"
        else
            ok "Skipped. Add manually later:"
            echo -e "    ${CYAN}${ALIAS_LINE}${NC}"
        fi
    fi
else
    warn "No .zshrc or .bashrc found. Add this to your shell config:"
    echo -e "    ${CYAN}${ALIAS_LINE}${NC}"
fi

# ---------------------------------------------------------------------------
step 5 "Verifying installation"
# ---------------------------------------------------------------------------

# Count resources
CMD_COUNT=$(find "$INSTALL_DIR/commands" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
SKILL_COUNT=$(find "$INSTALL_DIR/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
HOOK_COUNT=$(grep -c '"command"' "$INSTALL_DIR/hooks/hooks.json" 2>/dev/null || echo 0)
AGENT_COUNT=$(find "$INSTALL_DIR/agents" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

ok "Commands:  $CMD_COUNT"
ok "Skills:    $SKILL_COUNT"
ok "Hooks:     $HOOK_COUNT"
ok "Agents:    $AGENT_COUNT"

# ============================================================================
echo ""
echo -e "${GREEN}${BOLD}  ✅ Installation complete!${NC}"
echo ""
echo -e "  ${BOLD}Plugin location:${NC} $INSTALL_DIR"
echo ""
echo -e "  ${BOLD}Usage:${NC}"
echo -e "    ${CYAN}claude --add-dir $INSTALL_DIR${NC}         # One-time"
echo -e "    ${CYAN}claude-heo${NC}  or  ${CYAN}ch${NC}                     # With aliases"
echo -e "    ${CYAN}claude-heo -y${NC}                          # Skip permissions"
echo -e "    ${CYAN}claude-heo -p \"fix the login bug\"${NC}      # With prompt"
echo ""
echo -e "  ${BOLD}Update later:${NC}"
echo -e "    ${CYAN}git -C $INSTALL_DIR pull${NC}"
echo ""
# ============================================================================
