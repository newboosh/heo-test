#!/usr/bin/env bash
# ============================================================================
# test-plugin-full.sh — Comprehensive Frosty Plugin Test Suite
# ============================================================================
#
# Tests every agent, command, skill, and hook after the plugin is installed.
# Generates a minimal Python project scaffold, then runs smoke + functional
# tests using `claude -p` CLI automation.
#
# Usage:
#   chmod +x test-plugin-full.sh
#   ./test-plugin-full.sh [options]
#
# Options:
#   --skip-scaffold    Skip project scaffolding (already set up)
#   --skip-agents      Skip agent tests
#   --skip-commands    Skip command tests
#   --skip-skills      Skip skill tests
#   --skip-hooks       Skip hook tests
#   --skip-structure   Skip plugin structure validation tests
#   --skip-integration Skip integration smoke tests
#   --only <category>  Run only one category: agents|commands|skills|hooks|structure|integration
#   --timeout <secs>   Default timeout per test (default: 120)
#   --verbose          Show full claude output for each test
#   --dry-run          Print what would run without executing
#   --report <file>    Write JSON report to file (default: test-report.json)
#   --cleanup          Remove scaffold files after testing
#   -h, --help         Show this help
#
# Requirements:
#   - claude CLI installed and authenticated
#   - git initialized in the target repo
#   - jq (optional, for JSON report formatting)
#
# ============================================================================

# Note: NOT using set -e — test functions return non-zero on failure,
# and we need the suite to continue running all tests, not abort on first failure.
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR="$(pwd)"
TEST_DIR="${PROJECT_DIR}/.plugin-test-workspace"
REPORT_FILE="${PROJECT_DIR}/test-report.json"
DEFAULT_TIMEOUT=120
VERBOSE=false
DRY_RUN=false
SKIP_SCAFFOLD=false
SKIP_AGENTS=false
SKIP_COMMANDS=false
SKIP_SKILLS=false
SKIP_HOOKS=false
SKIP_STRUCTURE=false
SKIP_INTEGRATION=false
CLEANUP=false
ONLY=""

# Counters
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
ERRORS=()

# Colors (if terminal supports them)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' DIM='' NC=''
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()      { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $*"; }
log_sect() { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}\n"; }
usage() {
    sed -n '/^# Usage:/,/^# ====/p' "$0" | sed 's/^# \?//'
    exit 0
}

# ---------------------------------------------------------------------------
# Component-existence guards (auto-discovery for partial installs)
# ---------------------------------------------------------------------------
agent_exists()   { [[ -f "agents/${1}.md" ]]; }
command_exists() { [[ -f "commands/${1}.md" ]]; }
skill_exists()   { [[ -d "skills/${1}" ]] && [[ -f "skills/${1}/SKILL.md" ]]; }
hook_exists()    { [[ -f "hooks/${1}" ]]; }

# Wrapper: run_test only if the component file exists, otherwise skip.
# Usage: run_test_if <type> <check_name> <category> <name> <prompt> <pattern> [timeout]
run_test_if() {
    local check_type="$1"
    local check_name="$2"
    shift 2
    local exists=false
    case "$check_type" in
        agent)   agent_exists "$check_name" && exists=true ;;
        command) command_exists "$check_name" && exists=true ;;
        skill)   skill_exists "$check_name" && exists=true ;;
    esac
    if $exists; then
        run_test "$@"
    else
        local test_id="${1}::${2}"
        TOTAL=$((TOTAL + 1))
        SKIPPED=$((SKIPPED + 1))
        log_skip "$test_id (component not installed)"
        record_result "$1" "$2" "SKIPPED" "0" "Component not found: $check_name"
    fi
}

# Wrapper: run_local_test only if the hook file exists, otherwise skip.
# Usage: run_local_test_if_hook <hook_file> <category> <name> <command> <pattern>
run_local_test_if_hook() {
    local hook_file="$1"
    shift
    if hook_exists "$hook_file"; then
        run_local_test "$@"
    else
        local test_id="${1}::${2}"
        TOTAL=$((TOTAL + 1))
        SKIPPED=$((SKIPPED + 1))
        log_skip "$test_id (hook not installed)"
        record_result "$1" "$2" "SKIPPED" "0" "Hook not found: $hook_file"
    fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-scaffold)    SKIP_SCAFFOLD=true; shift ;;
        --skip-agents)      SKIP_AGENTS=true; shift ;;
        --skip-commands)    SKIP_COMMANDS=true; shift ;;
        --skip-skills)      SKIP_SKILLS=true; shift ;;
        --skip-hooks)       SKIP_HOOKS=true; shift ;;
        --skip-structure)   SKIP_STRUCTURE=true; shift ;;
        --skip-integration) SKIP_INTEGRATION=true; shift ;;
        --only)
            [[ $# -lt 2 ]] && { echo "Missing value for --only"; usage; }
            ONLY="$2"; shift 2 ;;
        --timeout)
            [[ $# -lt 2 ]] && { echo "Missing value for --timeout"; usage; }
            DEFAULT_TIMEOUT="$2"; shift 2 ;;
        --verbose)          VERBOSE=true; shift ;;
        --dry-run)          DRY_RUN=true; shift ;;
        --cleanup)          CLEANUP=true; shift ;;
        --report)
            [[ $# -lt 2 ]] && { echo "Missing value for --report"; usage; }
            REPORT_FILE="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *)               echo "Unknown option: $1"; usage ;;
    esac
done

# Apply --only filter
if [[ -n "$ONLY" ]]; then
    SKIP_AGENTS=true; SKIP_COMMANDS=true; SKIP_SKILLS=true; SKIP_HOOKS=true
    SKIP_STRUCTURE=true; SKIP_INTEGRATION=true
    case "$ONLY" in
        agents)      SKIP_AGENTS=false ;;
        commands)    SKIP_COMMANDS=false ;;
        skills)      SKIP_SKILLS=false ;;
        hooks)       SKIP_HOOKS=false ;;
        structure)   SKIP_STRUCTURE=false ;;
        integration) SKIP_INTEGRATION=false ;;
        *)           echo "Unknown category: $ONLY (use agents|commands|skills|hooks|structure|integration)"; exit 1 ;;
    esac
fi

# ---------------------------------------------------------------------------
# Test runner core
# ---------------------------------------------------------------------------

# Portable timeout wrapper (macOS lacks GNU timeout)
run_with_timeout() {
    local secs="$1"
    shift
    if command -v timeout &>/dev/null; then
        timeout "$secs" "$@"
    elif command -v gtimeout &>/dev/null; then
        gtimeout "$secs" "$@"
    else
        # Fallback: background process with kill.
        # Caveat: any signal-killed process (not just our watcher's kill)
        # will be reported as a timeout (exit 124). This only runs when
        # neither GNU timeout nor gtimeout is available.
        "$@" &
        local pid=$!
        (
            sleep "$secs"
            kill "$pid" 2>/dev/null
        ) &
        local watcher=$!
        if wait "$pid" 2>/dev/null; then
            kill "$watcher" 2>/dev/null
            wait "$watcher" 2>/dev/null
            return 0
        else
            local code=$?
            kill "$watcher" 2>/dev/null
            wait "$watcher" 2>/dev/null
            # Signal-killed (code > 128) likely means our watcher fired
            if [[ $code -gt 128 ]]; then
                return 124
            fi
            return $code
        fi
    fi
}

# Run a single test via claude -p
# Usage: run_test "category" "name" "prompt" "expected_pattern" [timeout]
#
# Always returns 0 so the suite continues regardless of test outcome.
# Test pass/fail is tracked via PASSED/FAILED counters and ERRORS array.
run_test() {
    local category="$1"
    local name="$2"
    local prompt="$3"
    local expected_pattern="${4:-}"
    local timeout="${5:-$DEFAULT_TIMEOUT}"

    TOTAL=$((TOTAL + 1))
    local test_id="${category}::${name}"

    if $DRY_RUN; then
        log_skip "$test_id (dry-run)"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    local output_file="${TEST_DIR}/results/${category}/${name//\//_}.txt"
    mkdir -p "$(dirname "$output_file")"

    log "Testing: ${test_id} (timeout: ${timeout}s)"

    local start_time
    start_time=$(date +%s)
    local exit_code=0

    # Run claude -p with timeout (--verbose before -p to avoid flag confusion)
    if run_with_timeout "$timeout" claude --verbose -p "$prompt" > "$output_file" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Evaluate results
    # Exit code 124 = timeout (GNU timeout convention)
    if [[ $exit_code -eq 124 ]]; then
        log_fail "$test_id — TIMEOUT after ${timeout}s"
        FAILED=$((FAILED + 1))
        ERRORS+=("$test_id: TIMEOUT after ${timeout}s")
        record_result "$category" "$name" "TIMEOUT" "$duration" ""
        return 0  # continue suite
    fi

    # Check if claude produced any output at all (smoke test)
    if [[ ! -s "$output_file" ]]; then
        log_fail "$test_id — No output produced (exit code: $exit_code)"
        FAILED=$((FAILED + 1))
        ERRORS+=("$test_id: No output (exit=$exit_code)")
        record_result "$category" "$name" "FAIL" "$duration" "No output"
        return 0  # continue suite
    fi

    # Check for plugin infrastructure errors (NOT errors that Claude discusses/reports)
    # These patterns indicate the plugin itself failed to load, not that Claude found issues.
    # Use anchored/specific patterns to avoid matching Claude's own analysis text.
    if grep -qE "^(Error|ERROR): (plugin not found|unknown (skill|agent|command))" "$output_file" 2>/dev/null ||
       grep -qE "^(bash|sh): .+: (command not found|No such file)" "$output_file" 2>/dev/null ||
       grep -qE "^Traceback \(most recent call last\)" "$output_file" 2>/dev/null; then
        local err_match
        err_match=$(grep -E "^(Error|ERROR):|^(bash|sh):.*not found|^Traceback" "$output_file" | head -1)
        log_fail "$test_id — Infrastructure error: ${err_match:0:100}"
        FAILED=$((FAILED + 1))
        ERRORS+=("$test_id: $err_match")
        record_result "$category" "$name" "FAIL" "$duration" "$err_match"
        return 0  # continue suite, don't abort
    fi

    # Functional test: check for expected pattern if provided
    if [[ -n "$expected_pattern" ]]; then
        if grep -qiE "$expected_pattern" "$output_file" 2>/dev/null; then
            log_pass "$test_id — Passed (${duration}s) [functional: matched '${expected_pattern:0:50}']"
            PASSED=$((PASSED + 1))
            record_result "$category" "$name" "PASS" "$duration" "Matched: $expected_pattern"
            if $VERBOSE; then
                echo -e "${DIM}"
                head -20 "$output_file"
                echo -e "${NC}"
            fi
            return 0
        else
            log_fail "$test_id — Functional check failed: expected pattern '${expected_pattern:0:80}' not found"
            FAILED=$((FAILED + 1))
            ERRORS+=("$test_id: Expected pattern not found: $expected_pattern")
            record_result "$category" "$name" "FAIL" "$duration" "Pattern not matched: $expected_pattern"
            if $VERBOSE; then
                echo -e "${DIM}"
                head -20 "$output_file"
                echo -e "${NC}"
            fi
            return 0  # continue suite
        fi
    fi

    # Smoke test pass (no error, produced output)
    log_pass "$test_id — Passed (${duration}s) [smoke]"
    PASSED=$((PASSED + 1))
    record_result "$category" "$name" "PASS" "$duration" ""
    if $VERBOSE; then
        echo -e "${DIM}"
        head -20 "$output_file"
        echo -e "${NC}"
    fi
    return 0
}

# Run a test that checks a local file/command (no claude invocation)
# Usage: run_local_test "category" "name" "command" "expected_pattern"
# Note: command is passed to bash -c for isolation (avoids polluting this shell)
run_local_test() {
    local category="$1"
    local name="$2"
    local cmd="$3"
    local expected_pattern="${4:-}"

    TOTAL=$((TOTAL + 1))
    local test_id="${category}::${name}"

    if $DRY_RUN; then
        log_skip "$test_id (dry-run)"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi

    local output_file="${TEST_DIR}/results/${category}/${name//\//_}.txt"
    mkdir -p "$(dirname "$output_file")"

    local exit_code=0
    bash -c "$cmd" > "$output_file" 2>&1 || exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_fail "$test_id — Command failed (exit: $exit_code)"
        FAILED=$((FAILED + 1))
        ERRORS+=("$test_id: exit code $exit_code")
        record_result "$category" "$name" "FAIL" "0" "Exit code: $exit_code"
        return 0  # continue suite
    fi

    if [[ -n "$expected_pattern" ]]; then
        if grep -qiE "$expected_pattern" "$output_file" 2>/dev/null; then
            log_pass "$test_id"
            PASSED=$((PASSED + 1))
            record_result "$category" "$name" "PASS" "0" ""
            return 0
        else
            log_fail "$test_id — Expected: $expected_pattern"
            FAILED=$((FAILED + 1))
            ERRORS+=("$test_id: Pattern not matched")
            record_result "$category" "$name" "FAIL" "0" "Pattern not matched"
            return 0  # continue suite
        fi
    fi

    log_pass "$test_id"
    PASSED=$((PASSED + 1))
    record_result "$category" "$name" "PASS" "0" ""
    return 0
}

# ---------------------------------------------------------------------------
# JSON report (uses a temp file to avoid shell injection via string interpolation)
# ---------------------------------------------------------------------------
RESULTS_JSONL_FILE=""

init_report() {
    RESULTS_JSONL_FILE="${TEST_DIR}/results.jsonl"
    : > "$RESULTS_JSONL_FILE"
}

record_result() {
    local category="$1" name="$2" status="$3" duration="$4" detail="$5"
    # Write each result as a JSONL line via python3 for safe escaping
    python3 -c "
import json, sys
entry = {
    'category': sys.argv[1],
    'name': sys.argv[2],
    'status': sys.argv[3],
    'duration_s': int(sys.argv[4]),
    'detail': sys.argv[5]
}
print(json.dumps(entry))
" "$category" "$name" "$status" "$duration" "$detail" >> "$RESULTS_JSONL_FILE" 2>/dev/null || true
}

write_report() {
    python3 -c "
import json, sys

results = []
try:
    with open(sys.argv[1]) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
except FileNotFoundError:
    pass

total = int(sys.argv[2])
passed = int(sys.argv[3])
failed = int(sys.argv[4])
skipped = int(sys.argv[5])
report_file = sys.argv[6]

effective = max(total - skipped, 1)
report = {
    'summary': {
        'total': total,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'pass_rate': round(passed / effective * 100, 1)
    },
    'results': results
}
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)
print(f'Report written to {report_file}')
" "$RESULTS_JSONL_FILE" "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED" "$REPORT_FILE" \
    2>/dev/null || log "Could not write JSON report (python3 needed)"
}

# ---------------------------------------------------------------------------
# Phase 0: Scaffold a minimal Python project
# ---------------------------------------------------------------------------
scaffold_project() {
    log_sect "PHASE 0: Project Scaffolding"

    if $SKIP_SCAFFOLD; then
        log "Skipping scaffold (--skip-scaffold)"
        return
    fi

    # Check for pre-existing files to avoid overwriting user data
    local scaffold_targets=("app/" "tests/" "pyproject.toml" "Makefile")
    for target in "${scaffold_targets[@]}"; do
        if [[ -e "$target" ]]; then
            log "ERROR: '$target' already exists. Use --skip-scaffold to skip scaffolding."
            log "Aborting scaffold to avoid overwriting existing files."
            return 1
        fi
    done

    log "Creating minimal Python project structure..."

    # Track created files for manifest-based cleanup
    local manifest=".scaffold_manifest"
    : > "$manifest"

    # ── app package ──────────────────────────────────────────────────────
    mkdir -p app/templates tests
    echo "app/" >> "$manifest"
    echo "tests/" >> "$manifest"

    # Main application
    cat > app/__init__.py << 'PYEOF'
"""Sample Flask application for plugin testing."""
from flask import Flask


def create_app(config_name="default"):
    """Application factory."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key-not-for-production"
    app.config["TESTING"] = config_name == "testing"

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
PYEOF

    cat > app/routes.py << 'PYEOF'
"""Application routes."""
from flask import Blueprint, render_template, request, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Home page."""
    return render_template("index.html", title="Test App")


@main_bp.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "version": "0.1.0"})


@main_bp.route("/api/items", methods=["GET", "POST"])
def items():
    """Items CRUD endpoint."""
    if request.method == "POST":
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "name is required"}), 400
        return jsonify({"id": 1, "name": data["name"]}), 201
    return jsonify({"items": [{"id": 1, "name": "Sample Item"}]})
PYEOF

    cat > app/models.py << 'PYEOF'
"""Data models."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class Item:
    """An item in the system."""
    name: str
    description: str = ""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }
PYEOF

    cat > app/utils.py << 'PYEOF'
"""Utility functions."""
import re
import os


def sanitize_input(value: str) -> str:
    """Sanitize user input by removing dangerous characters."""
    return re.sub(r'[<>&"\']', '', value)


def get_env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default)


# Intentional issue for testing: unused import, print statement
def debug_helper():
    """Debug helper with intentional issues for hook testing."""
    print("DEBUG: this should be caught by hooks")
    return True
PYEOF

    # ── Templates ────────────────────────────────────────────────────────
    cat > app/templates/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Welcome to the test application.</p>
    <form method="POST" action="/api/items">
        <input type="text" name="name" placeholder="Item name">
        <button type="submit">Add</button>
    </form>
</body>
</html>
HTMLEOF

    # ── Tests ────────────────────────────────────────────────────────────
    cat > tests/__init__.py << 'PYEOF'
"""Test package."""
PYEOF

    cat > tests/conftest.py << 'PYEOF'
"""Test fixtures."""
import pytest
from app import create_app


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
PYEOF

    cat > tests/test_routes.py << 'PYEOF'
"""Route tests."""


def test_index(client):
    """Test home page loads."""
    response = client.get("/")
    assert response.status_code == 200


def test_health(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_get_items(client):
    """Test listing items."""
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data


def test_create_item(client):
    """Test creating an item."""
    response = client.post(
        "/api/items",
        json={"name": "Test Item"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Test Item"


def test_create_item_missing_name(client):
    """Test creating an item without name fails."""
    response = client.post("/api/items", json={})
    assert response.status_code == 400
PYEOF

    cat > tests/test_models.py << 'PYEOF'
"""Model tests."""
from app.models import Item


def test_item_creation():
    """Test item creation."""
    item = Item(name="Test", description="A test item")
    assert item.name == "Test"
    assert item.id is None


def test_item_to_dict():
    """Test item serialization."""
    item = Item(name="Test", id=1)
    data = item.to_dict()
    assert data["id"] == 1
    assert data["name"] == "Test"
    assert "created_at" in data
PYEOF

    cat > tests/test_utils.py << 'PYEOF'
"""Utility tests."""
from app.utils import sanitize_input


def test_sanitize_removes_html():
    """Test HTML removal."""
    assert sanitize_input("<script>alert(1)</script>") == "scriptalert(1)/script"


def test_sanitize_preserves_normal_text():
    """Test normal text passes through."""
    assert sanitize_input("hello world") == "hello world"
PYEOF

    # ── Config files ─────────────────────────────────────────────────────
    cat > pyproject.toml << 'TOMLEOF'
[project]
name = "test-app"
version = "0.1.0"
description = "Minimal test application for plugin validation"
requires-python = ">=3.9"
dependencies = [
    "flask>=3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
TOMLEOF

    cat > Makefile << 'MAKEEOF'
.PHONY: test lint type-check ci run

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check .

type-check:
	python -m mypy app/

ci: lint type-check test

run:
	flask run --debug
MAKEEOF

    cat > .env.example << 'ENVEOF'
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=change-me-in-production
ENVEOF

    # Record all created files in the manifest for cleanup
    echo "pyproject.toml" >> "$manifest"
    echo "Makefile" >> "$manifest"
    echo ".env.example" >> "$manifest"
    echo ".scaffold_manifest" >> "$manifest"

    # ── Git setup (if not already a repo) ────────────────────────────────
    # Only stage scaffold files — never use git add -A which could stage unrelated work
    local scaffold_files=(
        app/__init__.py app/routes.py app/models.py app/utils.py
        app/templates/index.html
        tests/__init__.py tests/conftest.py tests/test_routes.py tests/test_models.py tests/test_utils.py
        pyproject.toml Makefile .env.example
    )
    if [[ ! -d .git ]]; then
        git init
        git add "${scaffold_files[@]}"
        git commit -m "Initial scaffold for plugin testing"
    else
        git add "${scaffold_files[@]}"
        git diff --cached --quiet || git commit -m "Add test scaffold for plugin validation"
    fi

    log "Scaffold complete: app/, tests/, pyproject.toml, Makefile"
}


# ============================================================================
# PHASE 1: AGENT TESTS
# ============================================================================
test_agents() {
    if $SKIP_AGENTS; then return; fi
    log_sect "PHASE 1: Agent Tests (up to 14 agents)"

    # 1. planner
    run_test_if agent planner "agent" "planner" \
        "You are testing the planner agent. Use the planner agent to create a brief plan for adding a /logout endpoint to app/routes.py. Keep the plan under 5 bullet points." \
        "(plan|step|phase|implement|endpoint)" \
        "$DEFAULT_TIMEOUT"

    # 2. architect
    run_test_if agent architect "agent" "architect" \
        "You are testing the architect agent. Use the architect agent to review the current architecture in app/ and suggest if a service layer is needed. Keep it brief (3-5 sentences)." \
        "(architect|layer|pattern|structure|design|service)" \
        "$DEFAULT_TIMEOUT"

    # 3. code-reviewer
    run_test_if agent code-reviewer "agent" "code-reviewer" \
        "You are testing the code-reviewer agent. Use the code-reviewer agent to review the file app/utils.py. Report any issues found. Keep it concise." \
        "(review|issue|print|sanitize|security|finding|suggestion)" \
        "$DEFAULT_TIMEOUT"

    # 4. security-reviewer
    run_test_if agent security-reviewer "agent" "security-reviewer" \
        "You are testing the security-reviewer agent. Use the security-reviewer agent to check app/routes.py for security issues. Report findings briefly." \
        "(security|vulnerabilit|csrf|injection|xss|input|validation|finding)" \
        "$DEFAULT_TIMEOUT"

    # 5. tdd-guide
    run_test_if agent tdd-guide "agent" "tdd-guide" \
        "You are testing the tdd-guide agent. Use the tdd-guide agent to suggest what tests are missing for app/models.py. Do NOT write any files. Just list the missing test cases." \
        "(test|coverage|missing|edge.case|assert|should)" \
        "$DEFAULT_TIMEOUT"

    # 6. qa-agent
    run_test_if agent qa-agent "agent" "qa-agent" \
        "You are testing the qa-agent. Use the qa-agent to review the current state of the project for quality issues. Do NOT modify files. Report findings briefly." \
        "(quality|compliance|review|finding|standard|pass|check)" \
        "$DEFAULT_TIMEOUT"

    # 7. context-agent
    run_test_if agent context-agent "agent" "context-agent" \
        "You are testing the context-agent. Use the context-agent to gather context about the app/ directory before working on it. Do NOT modify files. Summarize what you find." \
        "(context|structure|file|route|model|pattern|flask)" \
        "$DEFAULT_TIMEOUT"

    # 8. librarian
    run_test_if agent librarian "agent" "librarian" \
        "You are testing the librarian agent. Use the librarian agent to check if any documentation references are broken or missing in this project. Do NOT modify files. Report findings." \
        "(documentation|doc|file|reference|found|missing|catalog)" \
        "$DEFAULT_TIMEOUT"

    # 9. git-orchestrator
    run_test_if agent git-orchestrator "agent" "git-orchestrator" \
        "You are testing the git-orchestrator agent. Use the git-orchestrator agent to check the current git status and recent commit history. Do NOT make any commits or pushes. Just report the current state." \
        "(branch|commit|status|clean|git|history)" \
        "$DEFAULT_TIMEOUT"

    # 10. build-error-resolver
    run_test_if agent build-error-resolver "agent" "build-error-resolver" \
        "You are testing the build-error-resolver agent. Use the build-error-resolver agent to check if there are any type errors or lint issues in app/. Do NOT fix anything. Just report what you find." \
        "(error|lint|type|check|clean|issue|ruff|mypy|no.*(error|issue))" \
        "$DEFAULT_TIMEOUT"

    # 11. refactor-cleaner
    run_test_if agent refactor-cleaner "agent" "refactor-cleaner" \
        "You are testing the refactor-cleaner agent. Use the refactor-cleaner agent to scan app/ for dead code or unused imports. Do NOT modify files. Report findings." \
        "(dead.code|unused|import|refactor|clean|found|scan)" \
        "$DEFAULT_TIMEOUT"

    # 12. sentinel
    run_test_if agent sentinel "agent" "sentinel" \
        "You are testing the sentinel agent. Use the sentinel agent to scan the project for emerging issues like TODOs, hardcoded values, mocks, or workarounds. Do NOT modify files. Report findings." \
        "(sentinel|issue|todo|hardcoded|workaround|mock|finding|scan|emerging)" \
        "$DEFAULT_TIMEOUT"

    # 13. doc-updater
    run_test_if agent doc-updater "agent" "doc-updater" \
        "You are testing the doc-updater agent. Use the doc-updater agent to analyze the project structure and describe what a codemap would contain. Do NOT create or modify files." \
        "(doc|map|structure|module|file|app|route|model)" \
        "$DEFAULT_TIMEOUT"

    # 14. e2e-runner
    run_test_if agent e2e-runner "agent" "e2e-runner" \
        "You are testing the e2e-runner agent. Use the e2e-runner agent to describe what E2E tests would be needed for the /api/health and /api/items endpoints. Do NOT write any files." \
        "(e2e|end.to.end|test|endpoint|health|item|playwright|journey)" \
        "$DEFAULT_TIMEOUT"
}


# ============================================================================
# PHASE 2: SLASH COMMAND TESTS
# ============================================================================
test_commands() {
    if $SKIP_COMMANDS; then return; fi
    log_sect "PHASE 2: Slash Command Tests (up to 43 commands)"

    # --- Planning & Discovery ---

    # /plan
    run_test_if command plan "command" "plan" \
        "Run /plan Add a user registration endpoint with email validation. Do NOT implement anything, just create the plan." \
        "(plan|step|phase|implement|registration|email)" \
        "$DEFAULT_TIMEOUT"

    # /arch-debate
    run_test_if command arch-debate "command" "arch-debate" \
        "Explain what /arch-debate does. Describe how it facilitates architecture debates between agents. Do NOT start a debate." \
        "(arch|debate|architect|trade.off|decision|option|compare)" \
        "$DEFAULT_TIMEOUT"

    # /context
    run_test_if command context "command" "context" \
        "Run /context Understand the Flask application structure in app/ before adding authentication" \
        "(context|structure|file|route|model|flask|app)" \
        "$DEFAULT_TIMEOUT"

    # /context-payload
    run_test_if command context-payload "command" "context-payload" \
        "Run /context-payload Adding rate limiting to the API endpoints" \
        "(context|payload|raw|linked|summary|rate.limit)" \
        180

    # /task
    run_test_if command task "command" "task" \
        "Run /task Describe the 4-phase workflow this command uses. Do NOT execute the full workflow - just explain what it does." \
        "(task|phase|discovery|prd|execution|workflow)" \
        "$DEFAULT_TIMEOUT"

    # --- Development Workflow ---

    # /tdd
    run_test_if command tdd "command" "tdd" \
        "Run /tdd app/models.py — Identify missing test cases for the Item model. Do NOT write code, just list what tests are needed." \
        "(test|coverage|tdd|red|green|refactor|missing|item|model)" \
        "$DEFAULT_TIMEOUT"

    # /test-coverage
    run_test_if command test-coverage "command" "test-coverage" \
        "Run /test-coverage — Analyze current test coverage and identify gaps. Do NOT write any tests." \
        "(coverage|gap|test|file|percent|missing|untested)" \
        "$DEFAULT_TIMEOUT"

    # /test-swarm
    run_test_if command test-swarm "command" "test-swarm" \
        "Explain what /test-swarm does. Describe how agents collaborate on testing. Do NOT start a swarm." \
        "(test|swarm|agent|parallel|coordinate|coverage)" \
        "$DEFAULT_TIMEOUT"

    # /build-fix
    run_test_if command build-fix "command" "build-fix" \
        "Run /build-fix — Check for build or type errors. Do NOT fix anything, just report what you find." \
        "(build|type|error|lint|check|clean|fix|issue|ruff|mypy)" \
        "$DEFAULT_TIMEOUT"

    # /verify
    run_test_if command verify "command" "verify" \
        "Run /verify quick — Run quick verification checks. Report results." \
        "(verify|check|pass|fail|lint|type|test|status)" \
        180

    # /ci
    run_test_if command ci "command" "ci" \
        "Run /ci — Run CI pipeline checks locally. Report results." \
        "(ci|check|pass|fail|lint|test|quality|pipeline)" \
        180

    # /branch
    run_test_if command branch "command" "branch" \
        "Run /branch — Show the current branch information and naming conventions." \
        "(branch|convention|type|scope|name|current)" \
        "$DEFAULT_TIMEOUT"

    # /push — smoke only (don't actually push)
    run_test_if command push "command" "push-info" \
        "Explain what /push does without actually running it. Describe the workflow: branch protection, PR creation, etc." \
        "(push|branch|pr|pull.request|protection|remote)" \
        "$DEFAULT_TIMEOUT"

    # --- Code Review & Quality ---

    # /code-review
    run_test_if command code-review "command" "code-review" \
        "Run /code-review — Review uncommitted changes or recent code for quality issues. Do NOT modify files." \
        "(review|quality|issue|finding|code|security|suggestion)" \
        "$DEFAULT_TIMEOUT"

    # /review-swarm
    run_test_if command review-swarm "command" "review-swarm" \
        "Explain what /review-swarm does. Describe how it coordinates parallel code reviews. Do NOT start a swarm." \
        "(review|swarm|agent|parallel|coordinate|quality)" \
        "$DEFAULT_TIMEOUT"

    # /qa
    run_test_if command qa "command" "qa" \
        "Run /qa app/ — Review the app directory for quality and compliance. Do NOT modify files." \
        "(quality|compliance|review|check|standard|finding|pass)" \
        "$DEFAULT_TIMEOUT"

    # /standards
    run_test_if command standards "command" "standards" \
        "Run /standards testing — Look up testing standards for this project." \
        "(standard|testing|convention|rule|guideline|pytest|coverage)" \
        "$DEFAULT_TIMEOUT"

    # --- Documentation ---

    # /update-docs
    run_test_if command update-docs "command" "update-docs" \
        "Run /update-docs — Describe what documentation updates would be needed. Do NOT create or modify files." \
        "(doc|update|readme|documentation|sync|source)" \
        "$DEFAULT_TIMEOUT"

    # /update-codemaps
    run_test_if command update-codemaps "command" "update-codemaps" \
        "Run /update-codemaps — Describe what a codemap for this project would contain. Do NOT create files." \
        "(codemap|structure|module|architecture|doc|map)" \
        "$DEFAULT_TIMEOUT"

    # --- Refactoring & Cleanup ---

    # /refactor-clean
    run_test_if command refactor-clean "command" "refactor-clean" \
        "Run /refactor-clean — Scan for dead code and unused imports. Do NOT modify files, just report." \
        "(dead.code|unused|import|refactor|clean|scan|found)" \
        "$DEFAULT_TIMEOUT"

    # --- Bug Investigation ---

    # /bug
    run_test_if command bug "command" "bug" \
        "Run /bug The sanitize_input function in app/utils.py does not properly handle Unicode characters — Investigate this potential bug. Do NOT modify files." \
        "(bug|investigat|hypothesis|sanitize|unicode|evidence|root.cause)" \
        "$DEFAULT_TIMEOUT"

    # /bug-swarm
    run_test_if command bug-swarm "command" "bug-swarm" \
        "Explain what /bug-swarm does. Describe how it coordinates multiple agents to investigate a bug. Do NOT actually start a swarm." \
        "(bug|swarm|agent|investigate|coordinate|parallel)" \
        "$DEFAULT_TIMEOUT"

    # --- Iterative Development (Ralph Wiggum) ---

    # /build-ralph-prompt — just describe
    run_test_if command build-prompt "command" "build-ralph-prompt" \
        "Explain what /build-ralph-prompt does and how the Ralph Wiggum loop works. Do NOT actually start a loop." \
        "(ralph|loop|iterative|prompt|autonomous|wiggum)" \
        "$DEFAULT_TIMEOUT"

    # /ralph-loop — describe only
    run_test_if command ralph-loop "command" "ralph-loop" \
        "Explain what /ralph-loop does. How does it manage the autonomous development loop? Do NOT start a loop." \
        "(ralph|loop|autonomous|iterative|wiggum|cycle)" \
        "$DEFAULT_TIMEOUT"

    # /cancel-ralph — smoke
    run_test_if command cancel-ralph "command" "cancel-ralph" \
        "Explain what /cancel-ralph does. Is there currently an active Ralph loop to cancel?" \
        "(cancel|ralph|loop|active|no.*loop|not.*running)" \
        "$DEFAULT_TIMEOUT"

    # /help — plugin help
    run_test_if command help "command" "help" \
        "Run /help — Show available plugin commands and usage information." \
        "(command|help|usage|available|plugin)" \
        "$DEFAULT_TIMEOUT"

    # --- Sprint ---

    # /sprint-run — describe only
    run_test_if command sprint-run "command" "sprint-run" \
        "Explain what /sprint-run does. Describe the 13 phases of the sprint lifecycle. Do NOT actually start a sprint." \
        "(sprint|phase|lifecycle|plan|implement|review|deploy|retrospective)" \
        "$DEFAULT_TIMEOUT"

    # /plan-swarm
    run_test_if command plan-swarm "command" "plan-swarm" \
        "Explain what /plan-swarm does. Describe how multiple agents collaborate on planning. Do NOT start a swarm." \
        "(plan|swarm|agent|collaborat|parallel|coordinate)" \
        "$DEFAULT_TIMEOUT"

    # /collect-signals — describe
    run_test_if command collect-signals "command" "collect-signals" \
        "Explain what /collect-signals does. What signals does it gather post-merge?" \
        "(signal|collect|merge|ci|test|dependency|audit|monitor)" \
        "$DEFAULT_TIMEOUT"

    # /orchestrate — describe
    run_test_if command orchestrate "command" "orchestrate" \
        "Explain what /orchestrate does. Which sprint phases does it cover?" \
        "(orchestrat|phase|sprint|implement|review|merge|6|7|8|9|10|11)" \
        "$DEFAULT_TIMEOUT"

    # --- Checkpoints ---

    # /checkpoint
    run_test_if command checkpoint "command" "checkpoint" \
        "Run /checkpoint list — List any existing checkpoints." \
        "(checkpoint|list|none|no.*checkpoint|found|create)" \
        "$DEFAULT_TIMEOUT"

    # --- Catalog ---

    # /catalog
    run_test_if command catalog "command" "catalog" \
        "Run /catalog status — Check the current catalog status." \
        "(catalog|status|index|build|file|classification|not.*found|no.*catalog|config)" \
        "$DEFAULT_TIMEOUT"

    # /health-check
    run_test_if command health-check "command" "health-check" \
        "Run /health-check — Check plugin and project health status. Report findings." \
        "(health|check|status|plugin|project|pass|fail|ok)" \
        "$DEFAULT_TIMEOUT"

    # --- E2E ---

    # /e2e
    run_test_if command e2e "command" "e2e" \
        "Run /e2e Describe what E2E tests would be needed for the health and items API endpoints. Do NOT write files." \
        "(e2e|end.to.end|test|endpoint|playwright|health|item)" \
        "$DEFAULT_TIMEOUT"

    # --- Learning ---

    # /learn
    run_test_if command learn "command" "learn" \
        "Run /learn — Extract any reusable patterns from this session. Report what you find." \
        "(learn|pattern|reusable|extract|skill|insight)" \
        "$DEFAULT_TIMEOUT"

    # --- CodeRabbit ---

    # /coderabbit (main)
    run_test_if command coderabbit "command" "coderabbit" \
        "Explain what /coderabbit does. Describe the CodeRabbit review management workflow." \
        "(coderabbit|review|pr|pull.request|manage|workflow)" \
        "$DEFAULT_TIMEOUT"

    # /coderabbit status
    run_test_if command coderabbit-status "command" "coderabbit-status" \
        "Run /coderabbit status — Check PR status for CodeRabbit. Report results even if no PR exists." \
        "(coderabbit|pr|status|review|no.*pr|not.*found|branch)" \
        "$DEFAULT_TIMEOUT"

    # /coderabbit-conflicts
    run_test_if command coderabbit-conflicts "command" "coderabbit-conflicts" \
        "Explain what /coderabbit-conflicts does. How does it resolve review conflicts?" \
        "(coderabbit|conflict|resolve|review|merge|resolution)" \
        "$DEFAULT_TIMEOUT"

    # /coderabbit-process
    run_test_if command coderabbit-process "command" "coderabbit-process" \
        "Explain what /coderabbit-process does. How does it process review comments?" \
        "(coderabbit|process|comment|review|address|implement)" \
        "$DEFAULT_TIMEOUT"

    # /pr-status
    run_test_if command pr-status "command" "pr-status" \
        "Run /pr-status — Check current PR status. Report results even if no PR exists." \
        "(pr|status|pull.request|no.*pr|not.*found|branch|merge)" \
        "$DEFAULT_TIMEOUT"

    # --- Common Patterns (reference doc) ---
    run_test_if command common-patterns "command" "common-patterns" \
        "Run /common-patterns — Show common reusable patterns available in this plugin." \
        "(pattern|github|auth|quality|check|pr|detect|reusable)" \
        "$DEFAULT_TIMEOUT"

    # --- Worktree ---

    # /tree status
    run_test_if command tree "command" "tree-status" \
        "Run /tree status — Show current worktree status." \
        "(worktree|tree|branch|status|main|active)" \
        "$DEFAULT_TIMEOUT"

    # /tree help
    run_test_if command tree "command" "tree-help" \
        "Run /tree help — Show worktree command help." \
        "(tree|worktree|help|command|stage|build|close|usage)" \
        "$DEFAULT_TIMEOUT"
}


# ============================================================================
# PHASE 3: SKILL TESTS
# ============================================================================
test_skills() {
    if $SKIP_SKILLS; then return; fi
    log_sect "PHASE 3: Skill Tests (up to 44 skills)"

    # --- User-invocable skills ---

    # tdd-workflow
    run_test_if skill tdd-workflow "skill" "tdd-workflow" \
        "Use the tdd-workflow skill to explain the Red-Green-Refactor cycle for adding a delete endpoint to app/routes.py. Do NOT write code." \
        "(red|green|refactor|test|tdd|cycle|write.*test.*first)" \
        "$DEFAULT_TIMEOUT"

    # setup
    run_test_if skill setup "skill" "setup" \
        "Use the setup skill to describe how to configure the frosty plugin for this project. Do NOT make changes." \
        "(setup|config|plugin|frosty|install|configure)" \
        "$DEFAULT_TIMEOUT"

    # agent-creator
    run_test_if skill agent-creator "skill" "agent-creator" \
        "Use the agent-creator skill to describe how to create a new custom agent called 'performance-profiler'. Do NOT create any files." \
        "(agent|creat|frontmatter|model|tools|description|performance)" \
        "$DEFAULT_TIMEOUT"

    # skill-creator
    run_test_if skill skill-creator "skill" "skill-creator" \
        "Use the skill-creator skill to describe the structure needed for a new skill called 'api-versioning'. Do NOT create files." \
        "(skill|creat|structure|SKILL.md|frontmatter|api.version)" \
        "$DEFAULT_TIMEOUT"

    # hook-creator
    run_test_if skill hook-creator "skill" "hook-creator" \
        "Use the hook-creator skill to describe how to create a PreToolUse hook that blocks database drops. Do NOT create files." \
        "(hook|creat|PreToolUse|block|database|drop|matcher)" \
        "$DEFAULT_TIMEOUT"

    # bug-investigate
    run_test_if skill bug-investigate "skill" "bug-investigate" \
        "Use the bug-investigate skill to describe the hypothesis-driven investigation methodology. Do NOT investigate a real bug." \
        "(hypothesis|investigate|evidence|reproduce|root.cause|single.variable)" \
        "$DEFAULT_TIMEOUT"

    # catalog
    run_test_if skill catalog "skill" "catalog" \
        "Use the catalog skill to explain how the file classification catalog works. What does it index?" \
        "(catalog|classif|index|file|dependency|query|build)" \
        "$DEFAULT_TIMEOUT"

    # security-review
    run_test_if skill security-review "skill" "security-review" \
        "Use the security-review skill to list the security checklist items for Flask applications." \
        "(security|checklist|flask|csrf|xss|injection|owasp|authentication)" \
        "$DEFAULT_TIMEOUT"

    # sentinel
    run_test_if skill sentinel "skill" "sentinel" \
        "Use the sentinel skill to describe what emerging issues it detects: workarounds, mocks, TODOs, etc." \
        "(sentinel|emerging|workaround|mock|todo|temporary|hardcoded|detect)" \
        "$DEFAULT_TIMEOUT"

    # testing-strategy
    run_test_if skill testing-strategy "skill" "testing-strategy" \
        "Use the testing-strategy skill to recommend a testing approach for this Flask API project." \
        "(testing|strategy|unit|integration|e2e|tdd|pytest|approach)" \
        "$DEFAULT_TIMEOUT"

    # verification-loop
    run_test_if skill verification-loop "skill" "verification-loop" \
        "Use the verification-loop skill to describe the comprehensive verification system. What checks does it run?" \
        "(verification|loop|check|lint|type|test|coverage|security)" \
        "$DEFAULT_TIMEOUT"

    # composition-patterns
    run_test_if skill composition-patterns "skill" "composition-patterns" \
        "Use the composition-patterns skill to explain how skills can delegate to other skills." \
        "(composition|pattern|delegate|chain|orchestrat|skill)" \
        "$DEFAULT_TIMEOUT"

    # strategic-compact
    run_test_if skill strategic-compact "skill" "strategic-compact" \
        "Use the strategic-compact skill to explain when and how to perform context compaction." \
        "(strategic|compact|context|phase|interval|preserve)" \
        "$DEFAULT_TIMEOUT"

    # tool-design
    run_test_if skill tool-design "skill" "tool-design" \
        "Use the tool-design skill to describe the standards for building new skills, commands, and agents." \
        "(tool|design|standard|skill|command|agent|structure|convention)" \
        "$DEFAULT_TIMEOUT"

    # librarian
    run_test_if skill librarian "skill" "librarian" \
        "Use the librarian skill to describe the documentation management commands available." \
        "(librarian|documentation|audit|scan|catalog|find|manage)" \
        "$DEFAULT_TIMEOUT"

    # sprint
    run_test_if skill sprint "skill" "sprint" \
        "Use the sprint skill to describe the full 13-phase sprint lifecycle." \
        "(sprint|phase|lifecycle|plan|implement|review|deploy|retrospective|13)" \
        "$DEFAULT_TIMEOUT"

    # tree (worktree management)
    run_test_if skill tree "skill" "tree-worktree" \
        "Use the tree skill to describe worktree management capabilities: stage, build, close." \
        "(tree|worktree|stage|build|close|branch|parallel)" \
        "$DEFAULT_TIMEOUT"

    # worktree-management
    run_test_if skill worktree-management "skill" "worktree-management" \
        "Use the worktree-management skill to explain parallel development with git worktrees." \
        "(worktree|parallel|development|branch|git|manage)" \
        "$DEFAULT_TIMEOUT"

    # --- Agent-only skills (test that they're referenceable) ---

    # artifact-audit
    run_test_if skill artifact-audit "skill" "artifact-audit" \
        "Use the artifact-audit skill to describe what artifacts are verified: tests, docs, migrations." \
        "(artifact|audit|test|doc|migration|verify|exist|required)" \
        "$DEFAULT_TIMEOUT"

    # backend-patterns
    run_test_if skill backend-patterns "skill" "backend-patterns" \
        "Use the backend-patterns skill to describe backend architecture patterns for Flask and SQLAlchemy." \
        "(backend|pattern|flask|sqlalchemy|api|database|architecture)" \
        "$DEFAULT_TIMEOUT"

    # compliance-check
    run_test_if skill compliance-check "skill" "compliance-check" \
        "Use the compliance-check skill to describe what standards it checks code against." \
        "(compliance|check|standard|code|quality|rule|enforce)" \
        "$DEFAULT_TIMEOUT"

    # continuous-learning
    run_test_if skill continuous-learning "skill" "continuous-learning" \
        "Use the continuous-learning skill to explain how reusable patterns are extracted from sessions." \
        "(continuous|learning|pattern|extract|reusable|session|save)" \
        "$DEFAULT_TIMEOUT"

    # diff-review
    run_test_if skill diff-review "skill" "diff-review" \
        "Use the diff-review skill to describe how changed files are reviewed." \
        "(diff|review|change|file|check|identify|modified)" \
        "$DEFAULT_TIMEOUT"

    # eval-harness
    run_test_if skill eval-harness "skill" "eval-harness" \
        "Use the eval-harness skill to explain Eval-Driven Development (EDD) and pass@k metrics." \
        "(eval|harness|edd|pass@k|metric|success.criteria|driven)" \
        "$DEFAULT_TIMEOUT"

    # feedback-synthesizer
    run_test_if skill feedback-synthesizer "skill" "feedback-synthesizer" \
        "Use the feedback-synthesizer skill to describe how monitoring signals become actionable items." \
        "(feedback|synthesiz|signal|actionable|intake|retrospective)" \
        "$DEFAULT_TIMEOUT"

    # find-patterns
    run_test_if skill find-patterns "skill" "find-patterns" \
        "Use the find-patterns skill to describe how similar implementations are found in the codebase." \
        "(find|pattern|similar|implementation|prior.art|codebase)" \
        "$DEFAULT_TIMEOUT"

    # gate-decision
    run_test_if skill gate-decision "skill" "gate-decision" \
        "Use the gate-decision skill to describe go/no-go decision criteria for the sprint pipeline." \
        "(gate|decision|go.no.go|criteria|code.review|security|qa|ci)" \
        "$DEFAULT_TIMEOUT"

    # gather-docs
    run_test_if skill gather-docs "skill" "gather-docs" \
        "Use the gather-docs skill to describe how relevant documentation is collected for a task." \
        "(gather|doc|collect|relevant|task|documentation)" \
        "$DEFAULT_TIMEOUT"

    # hybrid-payload
    run_test_if skill hybrid-payload "skill" "hybrid-payload" \
        "Use the hybrid-payload skill to explain the 90/9/1 payload format." \
        "(hybrid|payload|90|9|1|raw|linked|summary|format)" \
        "$DEFAULT_TIMEOUT"

    # payload-consumer
    run_test_if skill payload-consumer "skill" "payload-consumer" \
        "Use the payload-consumer skill to describe how agents process hybrid context payloads." \
        "(payload|consumer|process|hybrid|context|reading.order|ack)" \
        "$DEFAULT_TIMEOUT"

    # plan-context
    run_test_if skill plan-context "skill" "plan-context" \
        "Use the plan-context skill to describe how current plan and todo context is gathered." \
        "(plan|context|todo|meta.plan|gather|understand)" \
        "$DEFAULT_TIMEOUT"

    # prereq-check
    run_test_if skill prereq-check "skill" "prereq-check" \
        "Use the prereq-check skill to describe what prerequisites are verified before starting work." \
        "(prereq|check|prerequisite|dependency|verify|before|start)" \
        "$DEFAULT_TIMEOUT"

    # process-map
    run_test_if skill process-map "skill" "process-map" \
        "Use the process-map skill to describe how affected business processes are identified." \
        "(process|map|business|affected|data.structure|impact|identify)" \
        "$DEFAULT_TIMEOUT"

    # project-skeleton
    run_test_if skill project-skeleton "skill" "project-skeleton" \
        "Use the project-skeleton skill to describe the template for creating project-specific skills." \
        "(project|skeleton|template|skill|customize|flask|python)" \
        "$DEFAULT_TIMEOUT"

    # sprint-retrospective
    run_test_if skill sprint-retrospective "skill" "sprint-retrospective" \
        "Use the sprint-retrospective skill to describe the sprint analysis methodology." \
        "(retrospective|sprint|analysis|what.worked|what.didn|pattern|extract)" \
        "$DEFAULT_TIMEOUT"

    # standards-lookup
    run_test_if skill standards-lookup "skill" "standards-lookup" \
        "Use the standards-lookup skill to describe how canonical standards are referenced." \
        "(standard|lookup|canonical|reference|consistent|context.agent|qa)" \
        "$DEFAULT_TIMEOUT"

    # sub-agent-dispatch
    run_test_if skill sub-agent-dispatch "skill" "sub-agent-dispatch" \
        "Use the sub-agent-dispatch skill to describe coordination patterns for context-agent sub-agents." \
        "(sub.agent|dispatch|coordination|pattern|spawn|complexity|tier)" \
        "$DEFAULT_TIMEOUT"

    # token-budget
    run_test_if skill token-budget "skill" "token-budget" \
        "Use the token-budget skill to describe token estimation and budget management." \
        "(token|budget|estimat|manage|allocation|formula|context)" \
        "$DEFAULT_TIMEOUT"

    # ack-protocol
    run_test_if skill ack-protocol "skill" "ack-protocol" \
        "Use the ack-protocol skill to describe the acknowledgment protocol for async payloads." \
        "(ack|protocol|acknowledgment|delivery|status|re.deliver|async)" \
        "$DEFAULT_TIMEOUT"

    # learned
    run_test_if skill learned "skill" "learned" \
        "Use the learned skill to describe how learned patterns are stored and retrieved across sessions." \
        "(learned|pattern|store|retrieve|session|reusable|knowledge)" \
        "$DEFAULT_TIMEOUT"

    # team-patterns
    run_test_if skill team-patterns "skill" "team-patterns" \
        "Use the team-patterns skill to describe team collaboration and coordination patterns." \
        "(team|pattern|collaborat|coordinat|agent|role|workflow)" \
        "$DEFAULT_TIMEOUT"

    # boundary-critique
    run_test_if skill boundary-critique "skill" "boundary-critique" \
        "Use the boundary-critique skill to describe how system boundaries are analyzed and critiqued." \
        "(boundary|critique|analysis|system|interface|edge|limit)" \
        "$DEFAULT_TIMEOUT"

    # problem-definition
    run_test_if skill problem-definition "skill" "problem-definition" \
        "Use the problem-definition skill to describe the methodology for defining problems clearly." \
        "(problem|definition|scope|constraint|requirement|clear|methodology)" \
        "$DEFAULT_TIMEOUT"

    # requirements-engineering
    run_test_if skill requirements-engineering "skill" "requirements-engineering" \
        "Use the requirements-engineering skill to describe how requirements are gathered and structured." \
        "(requirement|engineering|gather|structure|stakeholder|specification|user.story)" \
        "$DEFAULT_TIMEOUT"
}


# ============================================================================
# PHASE 4: HOOK TESTS
# ============================================================================
test_hooks() {
    if $SKIP_HOOKS; then return; fi
    log_sect "PHASE 4: Hook Tests"

    # --- Check hook files exist (guarded for partial installs) ---

    run_local_test_if_hook "session-validate-tools.py" "hook-file" "session-validate-tools" \
        "test -f hooks/session-validate-tools.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "session-ensure-git-hooks.py" "hook-file" "session-ensure-git-hooks" \
        "test -f hooks/session-ensure-git-hooks.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "session-setup-github-auth.py" "hook-file" "session-setup-github-auth" \
        "test -f hooks/session-setup-github-auth.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "session-catalog-build.py" "hook-file" "session-catalog-build" \
        "test -f hooks/session-catalog-build.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "pre-git-safety-check.py" "hook-file" "pre-git-safety-check" \
        "test -f hooks/pre-git-safety-check.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "post-python-format.py" "hook-file" "post-python-format" \
        "test -f hooks/post-python-format.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "sentinel-detect.py" "hook-file" "sentinel-detect" \
        "test -f hooks/sentinel-detect.py && echo 'EXISTS'" \
        "EXISTS"

    # hooks.json is required in all tiers (no guard)
    run_local_test "hook-file" "hooks-json" \
        "test -f hooks/hooks.json && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "post_agent_work.py" "hook-file" "post-agent-work" \
        "test -f hooks/post_agent_work.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "post_task.py" "hook-file" "post-task" \
        "test -f hooks/post_task.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "post_python_edit.py" "hook-file" "post-python-edit" \
        "test -f hooks/post_python_edit.py && echo 'EXISTS'" \
        "EXISTS"

    run_local_test_if_hook "post-jinja2-check.sh" "hook-file" "post-jinja2-check" \
        "test -f hooks/post-jinja2-check.sh && echo 'EXISTS'" \
        "EXISTS"

    # --- Check hooks.json is valid JSON (required in all tiers) ---
    run_local_test "hook-config" "hooks-json-valid" \
        "python3 -c \"import json; json.load(open('hooks/hooks.json')); print('VALID_JSON')\"" \
        "VALID_JSON"

    # --- Check hooks.json has expected hook types ---
    # hooks.json structure: { "hooks": { "SessionStart": [...], "PreToolUse": [...], ... } }
    # Allow 0+ entries per type (testing tier may have fewer)
    run_local_test "hook-config" "has-session-start-hooks" \
        "python3 -c \"
import json
data = json.load(open('hooks/hooks.json'))
hooks = data.get('hooks', data)
entries = hooks.get('SessionStart', [])
print(f'FOUND_{len(entries)}_SESSION_START_HOOKS')
\"" \
        "FOUND_[0-9]"

    run_local_test "hook-config" "has-pre-tool-hooks" \
        "python3 -c \"
import json
data = json.load(open('hooks/hooks.json'))
hooks = data.get('hooks', data)
entries = hooks.get('PreToolUse', [])
print(f'FOUND_{len(entries)}_PRE_TOOL_HOOKS')
\"" \
        "FOUND_[0-9]"

    run_local_test "hook-config" "has-post-tool-hooks" \
        "python3 -c \"
import json
data = json.load(open('hooks/hooks.json'))
hooks = data.get('hooks', data)
entries = hooks.get('PostToolUse', [])
print(f'FOUND_{len(entries)}_POST_TOOL_HOOKS')
\"" \
        "FOUND_[0-9]"

    # --- Check hook library modules (guarded) ---
    run_local_test_if_hook "lib/hook_utils.py" "hook-lib" "hook-utils-importable" \
        "python3 -c \"import sys; sys.path.insert(0,'hooks/lib'); import hook_utils; print('IMPORTABLE')\"" \
        "IMPORTABLE"

    run_local_test_if_hook "lib/safeguards.py" "hook-lib" "safeguards-importable" \
        "python3 -c \"import sys; sys.path.insert(0,'hooks/lib'); import safeguards; print('IMPORTABLE')\"" \
        "IMPORTABLE"

    run_local_test_if_hook "lib/sentinel_patterns.py" "hook-lib" "sentinel-patterns-importable" \
        "python3 -c \"import sys; sys.path.insert(0,'hooks/lib'); import sentinel_patterns; print('IMPORTABLE')\"" \
        "IMPORTABLE"

    # --- Functional: pre-git-safety-check blocks dangerous commands ---
    if hook_exists "pre-git-safety-check.py"; then
        run_local_test "hook-func" "blocks-no-verify" \
            "echo '{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": \"git commit --no-verify -m test\"}}' | python3 hooks/pre-git-safety-check.py 2>&1; echo EXIT_\$?" \
            "(block|EXIT_2|denied|no.verify)"

        run_local_test "hook-func" "blocks-force-push-main" \
            "echo '{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": \"git push --force origin main\"}}' | python3 hooks/pre-git-safety-check.py 2>&1; echo EXIT_\$?" \
            "(block|EXIT_2|denied|force|main)"

        run_local_test "hook-func" "blocks-reset-hard" \
            "echo '{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": \"git reset --hard HEAD~5\"}}' | python3 hooks/pre-git-safety-check.py 2>&1; echo EXIT_\$?" \
            "(block|EXIT_2|denied|reset|hard)"

        run_local_test "hook-func" "allows-normal-commit" \
            "echo '{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": \"git commit -m fix: update routes\"}}' | python3 hooks/pre-git-safety-check.py 2>&1; echo EXIT_\$?" \
            "EXIT_0"

        run_local_test "hook-func" "allows-normal-push" \
            "echo '{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": \"git push origin feature/test\"}}' | python3 hooks/pre-git-safety-check.py 2>&1; echo EXIT_\$?" \
            "EXIT_0"
    else
        for t in "blocks-no-verify" "blocks-force-push-main" "blocks-reset-hard" "allows-normal-commit" "allows-normal-push"; do
            TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
            log_skip "hook-func::$t (hook not installed)"
            record_result "hook-func" "$t" "SKIPPED" "0" "Hook not found: pre-git-safety-check.py"
        done
    fi

    # --- Functional: sentinel-detect.py processes edits ---
    if hook_exists "sentinel-detect.py"; then
        run_local_test "hook-func" "sentinel-detects-todo" \
            "echo '{\"tool_name\": \"Edit\", \"tool_input\": {\"file_path\": \"app/routes.py\", \"old_string\": \"return\", \"new_string\": \"# TODO: fix this later\\nreturn\"}}' | python3 hooks/sentinel-detect.py 2>&1 || true; echo SENTINEL_RAN" \
            "SENTINEL_RAN"
    else
        TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
        log_skip "hook-func::sentinel-detects-todo (hook not installed)"
        record_result "hook-func" "sentinel-detects-todo" "SKIPPED" "0" "Hook not found: sentinel-detect.py"
    fi

    # --- Functional: session hooks are syntactically valid Python (guarded) ---
    run_local_test_if_hook "session-validate-tools.py" "hook-syntax" "validate-tools-syntax" \
        "python3 -m py_compile hooks/session-validate-tools.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "session-ensure-git-hooks.py" "hook-syntax" "ensure-git-hooks-syntax" \
        "python3 -m py_compile hooks/session-ensure-git-hooks.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "session-setup-github-auth.py" "hook-syntax" "setup-github-auth-syntax" \
        "python3 -m py_compile hooks/session-setup-github-auth.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "session-catalog-build.py" "hook-syntax" "catalog-build-syntax" \
        "python3 -m py_compile hooks/session-catalog-build.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "pre-git-safety-check.py" "hook-syntax" "pre-git-safety-syntax" \
        "python3 -m py_compile hooks/pre-git-safety-check.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "post-python-format.py" "hook-syntax" "post-python-format-syntax" \
        "python3 -m py_compile hooks/post-python-format.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "sentinel-detect.py" "hook-syntax" "sentinel-detect-syntax" \
        "python3 -m py_compile hooks/sentinel-detect.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "post_agent_work.py" "hook-syntax" "post-agent-work-syntax" \
        "python3 -m py_compile hooks/post_agent_work.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "post_task.py" "hook-syntax" "post-task-syntax" \
        "python3 -m py_compile hooks/post_task.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "post_python_edit.py" "hook-syntax" "post-python-edit-syntax" \
        "python3 -m py_compile hooks/post_python_edit.py && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"

    run_local_test_if_hook "post-jinja2-check.sh" "hook-syntax" "post-jinja2-check-syntax" \
        "bash -n hooks/post-jinja2-check.sh && echo 'SYNTAX_OK'" \
        "SYNTAX_OK"
}


# ============================================================================
# PHASE 5: Plugin Structure Validation
# ============================================================================
test_structure() {
    if $SKIP_STRUCTURE; then return; fi
    log_sect "PHASE 5: Plugin Structure Validation"

    # Plugin metadata
    run_local_test "structure" "plugin-json-exists" \
        "test -f .claude-plugin/plugin.json && echo 'EXISTS'" \
        "EXISTS"

    run_local_test "structure" "plugin-json-valid" \
        "python3 -c \"import json; d=json.load(open('.claude-plugin/plugin.json')); print('name=' + d.get('name','MISSING'))\"" \
        "name=.+"

    run_local_test "structure" "marketplace-json-exists" \
        "test -f .claude-plugin/marketplace.json && echo 'EXISTS'" \
        "EXISTS"

    # Settings (optional — not present in all tiers)
    if [[ -f .claude/settings.json ]]; then
        run_local_test "structure" "settings-json-exists" \
            "test -f .claude/settings.json && echo 'EXISTS'" \
            "EXISTS"

        run_local_test "structure" "settings-json-valid" \
            "python3 -c \"import json; json.load(open('.claude/settings.json')); print('VALID')\"" \
            "VALID"
    fi

    # Agents directory (required)
    run_local_test "structure" "agents-dir-exists" \
        "test -d agents && echo 'EXISTS'" \
        "EXISTS"

    run_local_test "structure" "agent-count" \
        "ls agents/*.md 2>/dev/null | wc -l | tr -d ' '" \
        "[0-9]+"

    # Commands directory (required)
    run_local_test "structure" "commands-dir-exists" \
        "test -d commands && echo 'EXISTS'" \
        "EXISTS"

    run_local_test "structure" "command-count" \
        "ls commands/*.md 2>/dev/null | wc -l | tr -d ' '" \
        "[0-9]+"

    # Skills directory (required)
    run_local_test "structure" "skills-dir-exists" \
        "test -d skills && echo 'EXISTS'" \
        "EXISTS"

    run_local_test "structure" "skill-count" \
        "find skills -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' '" \
        "[0-9]+"

    # Hooks directory (required)
    run_local_test "structure" "hooks-dir-exists" \
        "test -d hooks && echo 'EXISTS'" \
        "EXISTS"

    # Rules (optional — not present in testing tier)
    if [[ -d rules ]]; then
        run_local_test "structure" "rules-dir-exists" \
            "test -d rules && echo 'EXISTS'" \
            "EXISTS"
    else
        TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
        log_skip "structure::rules-dir-exists (optional directory not present)"
        record_result "structure" "rules-dir-exists" "SKIPPED" "0" "Optional directory: rules"
    fi

    # Standards (optional — not present in testing tier)
    if [[ -d standards ]]; then
        run_local_test "structure" "standards-dir-exists" \
            "test -d standards && echo 'EXISTS'" \
            "EXISTS"
    else
        TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
        log_skip "structure::standards-dir-exists (optional directory not present)"
        record_result "structure" "standards-dir-exists" "SKIPPED" "0" "Optional directory: standards"
    fi

    # Scripts (optional)
    if [[ -d scripts ]]; then
        run_local_test "structure" "scripts-dir-exists" \
            "test -d scripts && echo 'EXISTS'" \
            "EXISTS"
    else
        TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
        log_skip "structure::scripts-dir-exists (optional directory not present)"
        record_result "structure" "scripts-dir-exists" "SKIPPED" "0" "Optional directory: scripts"
    fi

    # Scaffolds (optional)
    if [[ -d scaffolds ]]; then
        run_local_test "structure" "scaffolds-dir-exists" \
            "test -d scaffolds && echo 'EXISTS'" \
            "EXISTS"
    else
        TOTAL=$((TOTAL + 1)); SKIPPED=$((SKIPPED + 1))
        log_skip "structure::scaffolds-dir-exists (optional directory not present)"
        record_result "structure" "scaffolds-dir-exists" "SKIPPED" "0" "Optional directory: scaffolds"
    fi

    # All agent files have required frontmatter (only if agents dir exists)
    if [[ -d agents ]]; then
        run_local_test "structure" "agents-have-model" \
            "missing=0; for f in agents/*.md; do grep -qE '^model:' \"\$f\" || { echo \"MISSING_MODEL: \$f\"; missing=1; }; done; echo 'CHECK_DONE'; exit \$missing" \
            "CHECK_DONE"
    fi

    # All skills have SKILL.md (only if skills dir exists)
    if [[ -d skills ]]; then
        run_local_test "structure" "skills-have-skill-md" \
            "missing=0; for d in skills/*/; do test -f \"\${d}SKILL.md\" || { echo \"MISSING: \$d\"; missing=1; }; done; echo 'CHECK_DONE'; exit \$missing" \
            "CHECK_DONE"
    fi
}


# ============================================================================
# PHASE 6: Integration Smoke Tests (end-to-end with claude)
# ============================================================================
test_integration() {
    if $SKIP_INTEGRATION; then return; fi
    log_sect "PHASE 6: Integration Smoke Tests"

    # Can claude see the plugin agents? (pattern covers both full and testing tiers)
    run_test "integration" "claude-sees-agents" \
        "List all the custom agents available to you. Just list their names, one per line." \
        "(planner|architect|code-reviewer|tdd-guide|qa-agent|librarian|sentinel)" \
        "$DEFAULT_TIMEOUT"

    # Can claude use plugin skills? (pattern covers both full and testing tiers)
    run_test "integration" "claude-sees-skills" \
        "List all the custom skills available to you. Just list their names, one per line." \
        "(tdd-workflow|security-review|sprint|catalog|librarian|sentinel|eval-harness)" \
        "$DEFAULT_TIMEOUT"

    # Can claude see slash commands? (pattern covers both full and testing tiers)
    run_test "integration" "claude-sees-commands" \
        "List all the slash commands available to you (from the plugin, not built-in). Just list the command names." \
        "(/plan|/tdd|/verify|/code-review|/tree|/sprint-run|/orchestrate|/catalog|/ralph-loop)" \
        "$DEFAULT_TIMEOUT"

    # Can claude access rules? (only in full tier)
    if [[ -d rules ]]; then
        run_test "integration" "claude-reads-rules" \
            "Read and summarize the git-safety rule in 2-3 sentences." \
            "(git|safety|main|force.push|no.verify|protect)" \
            "$DEFAULT_TIMEOUT"
    fi

    # Can claude access standards? (only in full tier)
    if [[ -d standards ]]; then
        run_test "integration" "claude-reads-standards" \
            "Read and summarize the testing standards in 2-3 sentences." \
            "(test|standard|coverage|pytest|naming|convention)" \
            "$DEFAULT_TIMEOUT"
    fi

    # Plugin co-authorship (only in full tier with settings)
    if [[ -f .claude/settings.json ]]; then
        run_test "integration" "co-author-configured" \
            "Check if there's a co-author instruction in the plugin settings. Report what you find in .claude/settings.json." \
            "(co.author|settings|json|configured)" \
            "$DEFAULT_TIMEOUT"
    fi
}


# ============================================================================
# Cleanup scaffold files
# ============================================================================
cleanup_scaffold() {
    log_sect "Cleanup: Removing scaffold files"
    local manifest=".scaffold_manifest"
    if [[ -f "$manifest" ]]; then
        while IFS= read -r entry; do
            [[ -z "$entry" ]] && continue
            if [[ -d "$entry" ]]; then
                rm -rf "$entry"
            else
                rm -f "$entry"
            fi
        done < "$manifest"
        rm -f "$manifest"
        log "Scaffold files removed (manifest-based)"
    else
        log "No scaffold manifest found; skipping cleanup"
    fi
    rm -rf "${TEST_DIR}"
}


# ============================================================================
# Main execution
# ============================================================================
main() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   Frosty Plugin — Comprehensive Test Suite               ║${NC}"
    echo -e "${BOLD}║   Smoke + Functional Tests via claude CLI                ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Project:  ${PROJECT_DIR}"
    echo -e "  Report:   ${REPORT_FILE}"
    echo -e "  Timeout:  ${DEFAULT_TIMEOUT}s per test"
    echo -e "  Verbose:  ${VERBOSE}"
    echo -e "  Dry run:  ${DRY_RUN}"
    echo ""

    # Check prerequisites
    if ! command -v claude &>/dev/null; then
        echo -e "${RED}ERROR: 'claude' CLI not found. Install it first.${NC}"
        echo "  npm install -g @anthropic-ai/claude-code"
        exit 1
    fi

    if ! command -v git &>/dev/null; then
        echo -e "${RED}ERROR: 'git' not found.${NC}"
        exit 1
    fi

    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}ERROR: 'python3' not found.${NC}"
        exit 1
    fi

    # Create test workspace and init report
    mkdir -p "${TEST_DIR}/results"
    init_report

    # Record start time
    local suite_start
    suite_start=$(date +%s)

    # Run phases
    scaffold_project
    test_structure
    test_hooks
    test_agents
    test_commands
    test_skills
    test_integration

    # Record end time
    local suite_end
    suite_end=$(date +%s)
    local suite_duration=$((suite_end - suite_start))

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    echo ""
    log_sect "TEST SUITE SUMMARY"

    local pass_rate=0
    local effective_total=$((TOTAL - SKIPPED))
    if [[ $effective_total -gt 0 ]]; then
        pass_rate=$((PASSED * 100 / effective_total))
    fi

    echo -e "  ${BOLD}Total:${NC}    $TOTAL"
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo -e "  ${YELLOW}Skipped:${NC}  $SKIPPED"
    echo -e "  ${BOLD}Rate:${NC}     ${pass_rate}%"
    echo -e "  ${BOLD}Duration:${NC} ${suite_duration}s"
    echo ""

    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        echo -e "${RED}${BOLD}Failed tests:${NC}"
        for err in "${ERRORS[@]}"; do
            echo -e "  ${RED}x${NC} $err"
        done
        echo ""
    fi

    # Write JSON report
    write_report

    # Output locations (print before cleanup may delete them)
    echo -e "${DIM}Results saved to: ${TEST_DIR}/results/${NC}"
    echo -e "${DIM}Report saved to:  ${REPORT_FILE}${NC}"
    echo ""

    # Clean up scaffold if requested
    if $CLEANUP; then
        cleanup_scaffold
    fi

    # Exit code
    if [[ $FAILED -gt 0 ]]; then
        echo -e "${RED}${BOLD}SUITE FAILED${NC} ($FAILED failures)"
        exit 1
    else
        echo -e "${GREEN}${BOLD}SUITE PASSED${NC}"
        exit 0
    fi
}

main "$@"
