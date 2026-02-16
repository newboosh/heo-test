#!/bin/bash

# Worktree Scope Detection System
# Automatically detects and manages file boundaries for worktrees

# Fix #6: Conditional set -e (only when executed directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    set -e
fi

# ==============================================================================
# Configuration
# ==============================================================================

# Dynamic workspace root detection
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Scope detection patterns
# Maps keywords in feature descriptions to file patterns
declare -A SCOPE_PATTERNS=(
    # Email/Communication
    ["email"]="modules/email_integration/**"
    ["gmail"]="modules/email_integration/gmail*.py"
    ["oauth"]="modules/email_integration/*oauth*.py"
    ["smtp"]="modules/email_integration/smtp*.py"

    # Document Generation
    ["document"]="modules/document_generation/**"
    ["docx"]="modules/document_generation/**"
    ["template"]="modules/document_generation/templates/**"
    ["resume"]="modules/document_generation/*resume*.py"
    ["cover"]="modules/document_generation/*cover*.py"

    # Database
    ["database"]="modules/database/**"
    ["schema"]="modules/database/schema*.py"
    ["migration"]="modules/database/migrations/**"
    ["model"]="modules/database/models*.py"

    # API/Web
    ["api"]="modules/api/**"
    ["endpoint"]="modules/api/endpoints/**"
    ["route"]="modules/api/routes/**"
    ["webhook"]="modules/webhooks/**"

    # Frontend/Dashboard
    ["dashboard"]="frontend_templates/**"
    ["frontend"]="frontend_templates/**"
    ["ui"]="frontend_templates/**"
    ["template"]="frontend_templates/**"

    # AI/ML
    ["ai"]="modules/ai_job_description_analysis/**"
    ["gemini"]="modules/ai_job_description_analysis/**"
    ["llm"]="modules/ai_job_description_analysis/**"

    # Scraping
    ["scraping"]="modules/scraping/**"
    ["scrape"]="modules/scraping/**"
    ["spider"]="modules/scraping/**"

    # Storage
    ["storage"]="modules/storage/**"
    ["s3"]="modules/storage/cloud/**"
    ["gcs"]="modules/storage/cloud/**"

    # Testing
    ["test"]="tests/**"
    ["pytest"]="tests/**"

    # Documentation
    ["doc"]="docs/**"
    ["documentation"]="docs/**"
    ["readme"]="*.md"
)

# ==============================================================================
# Configuration Loading
# ==============================================================================

# Load scope patterns from worktree-config.json if available
# Merges with hardcoded defaults (config takes precedence)
load_scope_patterns_from_config() {
    local config_file="${TREE_CONFIG_FILE:-$WORKSPACE_ROOT/worktree-config.json}"

    # Skip if config file doesn't exist or jq isn't available
    if [ ! -f "$config_file" ]; then
        return 0
    fi

    if ! command -v jq &>/dev/null; then
        # Try Python fallback
        if command -v python3 &>/dev/null; then
            local config_patterns
            config_patterns=$(python3 - "$config_file" 2>/dev/null << 'PYLOAD'
import json
import sys

config_file = sys.argv[1]
try:
    with open(config_file) as f:
        data = json.load(f)

    scope_patterns = data.get('scope_patterns', {})
    for keyword, patterns in scope_patterns.items():
        # Output in format: keyword<TAB>pattern (first pattern if array)
        if isinstance(patterns, list) and patterns:
            print(f"{keyword}\t{patterns[0]}")
        elif isinstance(patterns, str):
            print(f"{keyword}\t{patterns}")
except:
    pass
PYLOAD
)
            # Parse and update SCOPE_PATTERNS (use tab delimiter for safe parsing)
            while IFS=$'\t' read -r keyword pattern; do
                if [ -n "$keyword" ] && [ -n "$pattern" ]; then
                    SCOPE_PATTERNS["$keyword"]="$pattern"
                fi
            done <<< "$config_patterns"
        fi
        return 0
    fi

    # Use jq to extract scope_patterns (use tab delimiter for safe parsing)
    # Handle both string and array values for patterns
    local patterns_json
    patterns_json=$(jq -r '.scope_patterns // {} | to_entries[] | "\(.key)\t\(.value | (if type=="array" then .[0] else . end))"' "$config_file" 2>/dev/null)

    # Update SCOPE_PATTERNS with config values (use tab delimiter)
    while IFS=$'\t' read -r keyword pattern; do
        if [ -n "$keyword" ] && [ -n "$pattern" ]; then
            SCOPE_PATTERNS["$keyword"]="$pattern"
        fi
    done <<< "$patterns_json"
}

# Call to load config patterns (only if bash 4+ for associative arrays)
if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
    load_scope_patterns_from_config
fi

# ==============================================================================
# Utility Functions
# ==============================================================================

# Fix #8: JSON validation function
validate_scope_json() {
    local json_file="$1"

    if [ ! -f "$json_file" ]; then
        echo "Error: JSON file does not exist: $json_file" >&2
        return 1
    fi

    # Fix #3: Use sys.argv instead of environment variable for safer path handling
    # Use Python to validate JSON structure
    python3 - "$json_file" << 'PYVALIDATE'
import json
import sys

if len(sys.argv) < 2:
    print("Error: JSON file path required", file=sys.stderr)
    sys.exit(1)

json_file = sys.argv[1]
required_keys = ['worktree', 'description', 'scope']
required_scope_keys = ['include', 'exclude']

try:
    with open(json_file) as f:
        data = json.load(f)

    # Check required top-level keys
    for key in required_keys:
        if key not in data:
            print(f"Missing required key: {key}", file=sys.stderr)
            sys.exit(1)

    # Check scope structure
    if 'scope' not in data or not isinstance(data['scope'], dict):
        print("'scope' must be an object", file=sys.stderr)
        sys.exit(1)

    for key in required_scope_keys:
        if key not in data['scope']:
            print(f"Missing required scope key: {key}", file=sys.stderr)
            sys.exit(1)

    # Validate arrays
    if not isinstance(data['scope']['include'], list):
        print("'include' must be an array", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data['scope']['exclude'], list):
        print("'exclude' must be an array", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)
except FileNotFoundError:
    print(f"File not found: {json_file}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Validation error: {e}", file=sys.stderr)
    sys.exit(1)
PYVALIDATE

    return $?
}

# ==============================================================================
# Scope Detection Functions
# ==============================================================================

# Detect scope from feature description
#
# Args:
#   $1 - Feature description (e.g., "Email OAuth refresh tokens")
#   $2 - Worktree name
#   $3 - Enforcement level (optional: "soft" or "hard", default: "hard" for features)
# Returns:
#   JSON scope manifest on stdout
detect_scope_from_description() {
    local description="$1"
    local worktree_name="$2"
    local enforcement="${3:-hard}"  # Default to hard for feature worktrees

    # CRITICAL FIX #6: Validate enforcement parameter
    if [[ "$enforcement" != "soft" && "$enforcement" != "hard" ]]; then
        echo "Error: enforcement must be 'soft' or 'hard', got: $enforcement" >&2
        return 1
    fi

    # Convert to lowercase for matching
    local desc_lower=$(echo "$description" | tr '[:upper:]' '[:lower:]')

    # Collect matched patterns
    local patterns=()

    # Fix #1: Use grep -qF to escape special characters in keywords
    for keyword in "${!SCOPE_PATTERNS[@]}"; do
        if echo "$desc_lower" | grep -qF "$keyword"; then
            patterns+=("${SCOPE_PATTERNS[$keyword]}")
        fi
    done

    # If no patterns matched, try to infer from worktree name
    if [ ${#patterns[@]} -eq 0 ]; then
        patterns=$(infer_from_worktree_name "$worktree_name")
    fi

    # Generate JSON with enforcement level
    generate_scope_json "$worktree_name" "$description" "$enforcement" "${patterns[@]}"
}

# Infer scope from worktree directory name
#
# Args:
#   $1 - Worktree name (e.g., "email-integration")
# Returns:
#   Array of patterns
infer_from_worktree_name() {
    local worktree_name="$1"
    local patterns=()

    # Extract first meaningful word from name
    local primary_word=$(echo "$worktree_name" | sed 's/[-_]/ /g' | awk '{print $1}' | tr '[:upper:]' '[:lower:]')

    # Check if primary word matches a known pattern
    if [ -n "${SCOPE_PATTERNS[$primary_word]}" ]; then
        patterns+=("${SCOPE_PATTERNS[$primary_word]}")
    else
        # Default: create module-specific scope
        local module_name=$(echo "$worktree_name" | sed 's/-/_/g')
        patterns+=("modules/${module_name}/**")
        patterns+=("tests/test_${module_name}*.py")
    fi

    echo "${patterns[@]}"
}

# Generate scope JSON manifest
#
# Args:
#   $1 - Worktree name
#   $2 - Description
#   $3 - Enforcement level (soft or hard)
#   $@ - Patterns (remaining args)
generate_scope_json() {
    local worktree_name="$1"
    local description="$2"
    local enforcement="$3"
    shift 3
    local patterns=("$@")

    # Fix #2: Escape special characters in description for JSON
    local escaped_description=$(echo "$description" | sed 's/\\/\\\\/g; s/"/\\"/g; s/'"$(printf '\t')"'/\\t/g' | tr '\n' ' ')

    # Start JSON
    echo '{'
    echo "  \"worktree\": \"$worktree_name\","
    echo "  \"description\": \"$escaped_description\","
    echo '  "scope": {'
    echo '    "include": ['

    # Add patterns
    local first=true
    for pattern in "${patterns[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        echo -n "      \"$pattern\""
    done

    # Fix #7: Better test/doc patterns for multiple common test directory structures
    if [ ${#patterns[@]} -gt 0 ]; then
        echo ","
    fi
    
    # Generate comprehensive test file patterns
    local test_basename="${worktree_name//-/_}"
    echo "      \"tests/test_*${test_basename}*.py\","
    echo "      \"tests/**/test_*${test_basename}*.py\","
    echo "      \"test/test_*${test_basename}*.py\","
    echo "      \"test/**/test_*${test_basename}*.py\","
    echo "      \"tests/unit/test_*${test_basename}*.py\","
    echo "      \"tests/integration/test_*${test_basename}*.py\","
    echo "      \"docs/*${worktree_name}*.md\""
    echo ''
    echo '    ],'
    echo '    "exclude": ['
    echo '      "**/__pycache__/**",'
    echo '      "**/*.pyc",'
    echo '      ".git/**",'
    echo '      "**/.DS_Store"'
    echo '    ]'
    echo '  },'
    echo "  \"enforcement\": \"$enforcement\","
    echo "  \"created\": \"$(date -Iseconds)\","
    echo '  "out_of_scope_policy": "warn"'
    echo '}'
}

# ==============================================================================
# Librarian Scope Calculation
# ==============================================================================

# Calculate librarian scope (inverse of all feature scopes)
#
# The librarian uses SOFT enforcement: warnings only, never blocks commits
# Feature worktrees use HARD enforcement: blocks commits outside scope
#
# Args:
#   $@ - Paths to all feature scope JSON files
# Returns:
#   JSON scope manifest for librarian (always soft enforcement)
calculate_librarian_scope() {
    local scope_files=("$@")

    # CRITICAL FIX #7: Check Python 3 availability before invocation
    if ! command -v python3 &> /dev/null; then
        echo "Error: python3 required but not found in PATH" >&2
        echo "Install Python 3 to use worktree scope detection" >&2
        return 1
    fi

    # Fix #5: Pass all files to a single Python process instead of looping
    # Collect all feature patterns in one Python invocation
    local all_patterns=()

    if [ ${#scope_files[@]} -gt 0 ]; then
        # Single Python call to extract all patterns using sys.argv
        local patterns=$(python3 - "${scope_files[@]}" << 'PYSCOPE'
import json
import sys

scope_files = sys.argv[1:]

all_patterns = []
for scope_file in scope_files:
    try:
        with open(scope_file) as f:
            data = json.load(f)
            for pattern in data['scope']['include']:
                if pattern not in all_patterns:
                    all_patterns.append(pattern)
    except Exception as e:
        print(f'Error reading {scope_file}: {e}', file=sys.stderr)
        continue

for pattern in all_patterns:
    print(pattern)
PYSCOPE
)

        while IFS= read -r pattern; do
            [ -n "$pattern" ] && all_patterns+=("$pattern")
        done <<< "$patterns"
    fi

    # Generate librarian scope
    echo '{'
    echo '  "worktree": "librarian",'
    echo '  "description": "Documentation, tooling, and project organization",'
    echo '  "scope": {'
    echo '    "include": ['
    echo '      "docs/**",'
    echo '      ".claude/**",'
    echo '      "tools/**",'
    echo '      "tasks/**",'
    echo '      "*.md",'
    echo '      "*.txt",'
    echo '      "*.toml",'
    echo '      "*.yaml",'
    echo '      "*.json",'
    echo '      ".github/**",'
    echo '      "scripts/**"'
    echo '    ],'
    echo '    "exclude": ['

    # Add all feature patterns as exclusions
    local first=true
    for pattern in "${all_patterns[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        echo -n "      \"$pattern\""
    done

    echo ','
    echo '      "**/__pycache__/**",'
    echo '      "**/*.pyc",'
    echo '      ".git/**"'
    echo '    ]'
    echo '  },'
    echo '  "enforcement": "soft",'
    echo "  \"created\": \"$(date -Iseconds)\","
    echo '  "type": "librarian",'
    echo '  "out_of_scope_policy": "warn"'
    echo '}'
}

# ==============================================================================
# Scope Validation
# ==============================================================================

# Check if a file matches scope patterns
#
# Args:
#   $1 - File path
#   $2 - Scope JSON file path
# Returns:
#   0 if matches, 1 if not
file_matches_scope() {
    local file_path="$1"
    local scope_json="$2"

    if [ ! -f "$scope_json" ]; then
        # No scope file = full access
        return 0
    fi

    # Use Python for glob matching with environment variables
    export FILE_PATH_TO_CHECK="$file_path"
    export SCOPE_JSON_FILE="$scope_json"
    python3 << 'PYMATCH'
import json
import fnmatch
import sys
import os

file_path = os.environ.get('FILE_PATH_TO_CHECK')
scope_file = os.environ.get('SCOPE_JSON_FILE')

try:
    with open(scope_file) as f:
        scope = json.load(f)

    # Check excludes first
    for pattern in scope['scope'].get('exclude', []):
        if fnmatch.fnmatch(file_path, pattern):
            sys.exit(1)  # Excluded

    # Check includes
    for pattern in scope['scope'].get('include', []):
        if fnmatch.fnmatch(file_path, pattern):
            sys.exit(0)  # Included

    # Not in scope
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYMATCH

    return $?
}

# ==============================================================================
# Conflict Detection
# ==============================================================================

# Detect scope conflicts across worktrees
#
# Args:
#   $@ - Paths to all scope JSON files
# Returns:
#   List of conflicting files
detect_scope_conflicts() {
    local scope_files=("$@")

    # Fix #4: Check if scope_files array is empty
    if [ ${#scope_files[@]} -eq 0 ]; then
        echo "No conflicts detected"
        return 0
    fi

    # Fix #3: Replace fragile heredoc with proper argv passing to Python
    # Build argument list for Python sys.argv
    python3 - "${scope_files[@]}" << 'PYCONFLICT'
import json
import sys
from collections import defaultdict

# Fix #3: Use sys.argv instead of fragile string formatting
scope_files = sys.argv[1:]

# Build file -> worktrees mapping
file_owners = defaultdict(list)

for scope_file in scope_files:
    try:
        with open(scope_file) as f:
            scope = json.load(f)

        worktree = scope['worktree']

        # For each include pattern, note which worktree owns it
        for pattern in scope['scope'].get('include', []):
            file_owners[pattern].append(worktree)
    except Exception as e:
        print(f"Error reading {scope_file}: {e}", file=sys.stderr)
        continue

# Find conflicts (patterns owned by multiple worktrees)
conflicts = {pattern: owners for pattern, owners in file_owners.items() if len(owners) > 1}

if conflicts:
    print("CONFLICTS DETECTED:")
    for pattern, owners in conflicts.items():
        print(f"  Pattern: {pattern}")
        print(f"    Owned by: {', '.join(owners)}")
    sys.exit(1)
else:
    print("No conflicts detected")
    sys.exit(0)
PYCONFLICT
}

# ==============================================================================
# Export Functions
# ==============================================================================

# Export functions for use in other scripts
export -f detect_scope_from_description
export -f infer_from_worktree_name
export -f generate_scope_json
export -f calculate_librarian_scope
export -f file_matches_scope
export -f detect_scope_conflicts
export -f validate_scope_json

