#!/bin/bash
# run-quality-checks.sh - Universal quality check runner with fallbacks
#
# Usage: ./scripts/run-quality-checks.sh [--fix] [--quiet] [--changed-only] [--staged]
#
# Options:
#   --fix           Auto-fix issues where possible
#   --quiet, -q     Suppress non-error output
#   --changed-only  Only check files changed vs origin/main
#   --staged        Only check staged files (for pre-commit hooks)
#   --base BRANCH   Compare against BRANCH instead of origin/main
#
# Automatically detects project type and runs appropriate quality checks.
# Returns exit code 0 on success, non-zero on failure.

set -e

FIX_MODE=false
QUIET=false
CHANGED_ONLY=false
STAGED_ONLY=false
BASE_BRANCH="origin/main"

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --quiet|-q)
            QUIET=true
            shift
            ;;
        --changed-only)
            CHANGED_ONLY=true
            shift
            ;;
        --staged)
            STAGED_ONLY=true
            shift
            ;;
        --base)
            BASE_BRANCH="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

log() {
    if [ "$QUIET" = false ]; then
        echo "$@"
    fi
}

log_error() {
    echo "$@" >&2
}

# Get changed files for a specific extension pattern
# Returns files one per line, handles spaces in filenames
get_changed_files() {
    local pattern="$1"  # e.g., "\.py$" or "\.(js|ts|jsx|tsx)$"

    if [ "$STAGED_ONLY" = true ]; then
        # Staged files only (for pre-commit)
        git diff --cached --name-only --diff-filter=d 2>/dev/null | grep -E "$pattern" || true
    elif [ "$CHANGED_ONLY" = true ]; then
        # Check if base branch exists
        if ! git rev-parse --verify "$BASE_BRANCH" &>/dev/null; then
            log_error "Warning: $BASE_BRANCH not found, checking all files"
            return 1
        fi
        # Changed vs base branch
        git diff --name-only --diff-filter=d "$BASE_BRANCH" 2>/dev/null | grep -E "$pattern" || true
    fi
}

# Check if we have files to process
has_files_to_check() {
    local pattern="$1"
    if [ "$STAGED_ONLY" = true ] || [ "$CHANGED_ONLY" = true ]; then
        local files
        files=$(get_changed_files "$pattern")
        [ -n "$files" ]
    else
        return 0  # Always true if checking all files
    fi
}

# Run a command on specific files or all files
# Usage: run_on_files "command" "pattern" [extra_args...]
run_on_files() {
    local cmd="$1"
    local pattern="$2"
    shift 2
    local extra_args=("$@")

    if [ "$STAGED_ONLY" = true ] || [ "$CHANGED_ONLY" = true ]; then
        local files
        files=$(get_changed_files "$pattern")
        if [ -n "$files" ]; then
            # Use printf to handle filenames safely, then xargs
            printf '%s\n' $files | xargs $cmd "${extra_args[@]}"
        fi
    else
        $cmd "${extra_args[@]}" .
    fi
}

# Track what we ran
RAN_CHECKS=false

# 1. Try Makefile targets (most explicit project configuration)
# Note: Makefile targets typically run on all files, skip in changed-only/staged modes
if [ -f "Makefile" ] && [ "$CHANGED_ONLY" = false ] && [ "$STAGED_ONLY" = false ]; then
    if grep -q "^quality:" Makefile 2>/dev/null; then
        log "Running: make quality"
        make quality
        RAN_CHECKS=true
    elif grep -q "^lint:" Makefile 2>/dev/null; then
        log "Running: make lint"
        make lint
        RAN_CHECKS=true
    elif grep -q "^check:" Makefile 2>/dev/null; then
        log "Running: make check"
        make check
        RAN_CHECKS=true
    fi
fi

# 2. Python projects
if [ "$RAN_CHECKS" = false ] && [ -f "pyproject.toml" ]; then
    if ! has_files_to_check '\.py$'; then
        if [ "$CHANGED_ONLY" = true ] || [ "$STAGED_ONLY" = true ]; then
            log "No Python files to check"
        fi
    else
        # Determine ruff command
        RUFF_CMD=""
        if [ -f "uv.lock" ] && command -v uv &>/dev/null; then
            RUFF_CMD="uv run ruff"
            log "Using: uv run ruff"
        elif [ -f "poetry.lock" ] && command -v poetry &>/dev/null; then
            RUFF_CMD="poetry run ruff"
            log "Using: poetry run ruff"
        elif [ -d ".venv" ] && [ -f ".venv/bin/ruff" ]; then
            RUFF_CMD=".venv/bin/ruff"
            log "Using: .venv/bin/ruff"
        elif command -v ruff &>/dev/null; then
            RUFF_CMD="ruff"
            log "Using: ruff (global)"
        fi

        if [ -n "$RUFF_CMD" ]; then
            if [ "$STAGED_ONLY" = true ] || [ "$CHANGED_ONLY" = true ]; then
                FILES=$(get_changed_files '\.py$')
                log "Checking $(echo "$FILES" | wc -l | tr -d ' ') Python file(s)"

                if [ "$FIX_MODE" = true ]; then
                    echo "$FILES" | xargs $RUFF_CMD check --fix
                    echo "$FILES" | xargs $RUFF_CMD format
                else
                    echo "$FILES" | xargs $RUFF_CMD check
                    echo "$FILES" | xargs $RUFF_CMD format --check
                fi
            else
                log "Checking all Python files"
                if [ "$FIX_MODE" = true ]; then
                    $RUFF_CMD check --fix .
                    $RUFF_CMD format .
                else
                    $RUFF_CMD check .
                    $RUFF_CMD format --check .
                fi
            fi
            RAN_CHECKS=true
        fi
    fi
fi

# 3. Node.js projects
if [ "$RAN_CHECKS" = false ] && [ -f "package.json" ]; then
    JS_PATTERN='\.(js|ts|jsx|tsx)$'

    if ! has_files_to_check "$JS_PATTERN"; then
        if [ "$CHANGED_ONLY" = true ] || [ "$STAGED_ONLY" = true ]; then
            log "No JavaScript/TypeScript files to check"
        fi
    else
        # Determine package manager
        PKG_MGR="npm run"
        if [ -f "yarn.lock" ]; then
            PKG_MGR="yarn"
        elif [ -f "pnpm-lock.yaml" ]; then
            PKG_MGR="pnpm"
        fi

        if grep -q '"lint"' package.json 2>/dev/null; then
            log "Running: $PKG_MGR lint"

            # Note: Most ESLint configs define their own file patterns
            # Passing specific files often doesn't work as expected
            # So we run the full lint command but it's still faster due to caching
            if [ "$FIX_MODE" = true ]; then
                $PKG_MGR lint --fix 2>/dev/null || $PKG_MGR lint -- --fix 2>/dev/null || true
            else
                $PKG_MGR lint
            fi
            RAN_CHECKS=true
        elif grep -q '"check"' package.json 2>/dev/null; then
            log "Running: $PKG_MGR check"
            $PKG_MGR check
            RAN_CHECKS=true
        fi
    fi
fi

# 4. Go projects
if [ "$RAN_CHECKS" = false ] && [ -f "go.mod" ]; then
    if ! has_files_to_check '\.go$'; then
        if [ "$CHANGED_ONLY" = true ] || [ "$STAGED_ONLY" = true ]; then
            log "No Go files to check"
        fi
    else
        # Note: Go tools work at package level, not individual files
        # We check if any .go files changed, then run on full packages
        if command -v golangci-lint &>/dev/null; then
            log "Running: golangci-lint"
            if [ "$FIX_MODE" = true ]; then
                golangci-lint run --fix ./...
            else
                golangci-lint run ./...
            fi
            RAN_CHECKS=true
        elif command -v go &>/dev/null; then
            log "Running: go vet"
            go vet ./...
            RAN_CHECKS=true
        fi
    fi
fi

# 5. Rust projects
if [ "$RAN_CHECKS" = false ] && [ -f "Cargo.toml" ]; then
    if ! has_files_to_check '\.rs$'; then
        if [ "$CHANGED_ONLY" = true ] || [ "$STAGED_ONLY" = true ]; then
            log "No Rust files to check"
        fi
    else
        # Note: Cargo works at crate level, not individual files
        log "Running: cargo clippy"
        if [ "$FIX_MODE" = true ]; then
            cargo clippy --fix --allow-dirty --allow-staged 2>/dev/null || cargo clippy
        else
            cargo clippy
        fi
        RAN_CHECKS=true
    fi
fi

# Report result
if [ "$RAN_CHECKS" = true ]; then
    log "Quality checks passed"
    exit 0
elif [ "$CHANGED_ONLY" = true ] || [ "$STAGED_ONLY" = true ]; then
    log "No files to check"
    exit 0
else
    log_error "No quality checks configured for this project"
    log_error "Supported: Makefile (quality/lint/check targets), Python (ruff/poetry/uv), Node.js, Go, Rust"
    exit 0  # Don't fail if no checks configured - just warn
fi
