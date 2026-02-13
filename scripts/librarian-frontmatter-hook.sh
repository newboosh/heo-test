#!/bin/bash
# Librarian Frontmatter Validation Hook
#
# Validates that files have proper YAML frontmatter as expected by the librarian
# Runs on pre-commit to catch missing or invalid metadata before commit
#
# Requirements:
# - Agents: name, description required
# - Skills: name, description required
# - Archived files: archived, reason, related required
# - Codemaps: Last Updated and Entry Points required

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ERRORS=0
WARNINGS=0
CHECKED=0

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_error() {
    echo -e "${RED}✗ ERROR${NC}: $1" >&2
    ERRORS=$((ERRORS + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1" >&2
    WARNINGS=$((WARNINGS + 1))
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Extract YAML frontmatter from file (between first --- and second ---)
extract_frontmatter() {
    local file=$1

    # Check if file starts with ---
    if ! head -1 "$file" | grep -q "^---"; then
        return 1
    fi

    # Extract content between first --- and second ---
    awk 'NR==1 {next} /^---/ {exit} {print}' "$file"
}

# Check if YAML field exists in frontmatter
has_yaml_field() {
    local frontmatter=$1
    local field=$2

    echo "$frontmatter" | grep -q "^${field}:" || return 1
}

# Get YAML field value
get_yaml_field() {
    local frontmatter=$1
    local field=$2

    echo "$frontmatter" | grep "^${field}:" | sed "s/^${field}: *//" | head -1
}

# Validate agent file
validate_agent() {
    local file=$1
    local has_errors=0

    local frontmatter
    frontmatter=$(extract_frontmatter "$file")
    if [ $? -ne 0 ]; then
        print_error "$file: Missing YAML frontmatter (agents must start with ---)"
        return 1
    fi

    # Check required fields
    if ! has_yaml_field "$frontmatter" "name"; then
        print_error "$file: Missing 'name' field in frontmatter"
        has_errors=1
    fi

    if ! has_yaml_field "$frontmatter" "description"; then
        print_error "$file: Missing 'description' field in frontmatter"
        has_errors=1
    fi

    # CRITICAL FIX #4: Validate name format - must start with letter, then alphanumeric/hyphens
    local name
    name=$(get_yaml_field "$frontmatter" "name")
    # Must start with letter, followed by alphanumerics/hyphens, no leading/trailing hyphens
    if [[ ! $name =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]] && [[ ! $name =~ ^[a-z]$ ]]; then
        print_error "$file: Invalid 'name' format. Must start with letter, contain only lowercase letters/numbers/hyphens: $name"
        has_errors=1
    fi

    # Validate description is not empty
    local desc
    desc=$(get_yaml_field "$frontmatter" "description")
    if [ -z "$desc" ] || [ "$desc" = "null" ]; then
        print_error "$file: 'description' field is empty"
        has_errors=1
    fi

    return $has_errors
}

# Validate skill file
validate_skill() {
    local file=$1
    local has_errors=0

    local frontmatter
    frontmatter=$(extract_frontmatter "$file")
    if [ $? -ne 0 ]; then
        print_error "$file: Missing YAML frontmatter (skills must start with ---)"
        return 1
    fi

    # Check required fields
    if ! has_yaml_field "$frontmatter" "name"; then
        print_error "$file: Missing 'name' field in frontmatter"
        has_errors=1
    fi

    if ! has_yaml_field "$frontmatter" "description"; then
        print_error "$file: Missing 'description' field in frontmatter"
        has_errors=1
    fi

    # Validate name format (lowercase, alphanumeric, hyphens, max 64 chars)
    local name
    name=$(get_yaml_field "$frontmatter" "name")
    if [[ ! $name =~ ^[a-z0-9-]+$ ]] || [ ${#name} -gt 64 ]; then
        print_error "$file: Invalid 'name' format. Must be lowercase, max 64 chars: $name"
        has_errors=1
    fi

    # Validate description includes "when" guidance
    local desc
    desc=$(get_yaml_field "$frontmatter" "description")
    if [ -z "$desc" ] || [ "$desc" = "null" ]; then
        print_error "$file: 'description' field is empty"
        has_errors=1
    fi

    if ! echo "$desc" | grep -qi "when\|use\|trigger"; then
        print_warning "$file: 'description' should explain when to use this skill"
    fi

    return $has_errors
}

# Validate archived file
validate_archived() {
    local file=$1
    local has_errors=0

    local frontmatter
    frontmatter=$(extract_frontmatter "$file")
    if [ $? -ne 0 ]; then
        print_error "$file: Missing YAML frontmatter (archived files must start with ---)"
        return 1
    fi

    # Check required fields
    if ! has_yaml_field "$frontmatter" "archived"; then
        print_error "$file: Missing 'archived' field (date when file was archived)"
        has_errors=1
    fi

    if ! has_yaml_field "$frontmatter" "reason"; then
        print_error "$file: Missing 'reason' field (why was file archived)"
        has_errors=1
    fi

    if ! has_yaml_field "$frontmatter" "related"; then
        print_error "$file: Missing 'related' field (link to replacement/current file)"
        has_errors=1
    fi

    # Validate archived date format (YYYY-MM-DD) and actual validity
    local archived_date
    archived_date=$(get_yaml_field "$frontmatter" "archived")
    # Check format first
    if ! [[ $archived_date =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        print_error "$file: Invalid 'archived' date format. Use YYYY-MM-DD: $archived_date"
        has_errors=1
    # Then validate the date is actually valid (no 13th month, 32nd day, etc)
    elif ! date -j -f "%Y-%m-%d" "$archived_date" &>/dev/null; then
        print_error "$file: Invalid 'archived' date (month/day out of range): $archived_date"
        has_errors=1
    fi

    return $has_errors
}

# Validate codemap file
validate_codemap() {
    local file=$1
    local has_errors=0

    # Check for "Last Updated" header
    if ! grep -q "Last Updated:" "$file"; then
        print_error "$file: Codemap missing 'Last Updated:' header"
        has_errors=1
    fi

    # Check for "Entry Points" section
    if ! grep -q "Entry Points:" "$file"; then
        print_error "$file: Codemap missing 'Entry Points:' section"
        has_errors=1
    fi

    return $has_errors
}

# =============================================================================
# MAIN HOOK LOGIC
# =============================================================================

# Get list of staged files
staged_files=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$staged_files" ]; then
    exit 0
fi

print_info "Validating librarian frontmatter..."
echo ""

# Process each staged file
while IFS= read -r file; do
    # Skip if file doesn't exist (e.g., deleted files)
    [ -f "$file" ] || continue

    # Skip non-markdown files
    [[ ! $file =~ \.md$ ]] && continue

    CHECKED=$((CHECKED + 1))

    # Determine file type based on path and validate accordingly
    if [[ $file =~ ^agents/.*\.md$ ]]; then
        print_info "Checking agent: $file"
        validate_agent "$file" || true

    elif [[ $file =~ ^skills/.*/SKILL\.md$ ]]; then
        print_info "Checking skill: $file"
        validate_skill "$file" || true

    elif [[ $file =~ /archived/ ]] || [[ $file =~ -archived\.md$ ]]; then
        print_info "Checking archived file: $file"
        validate_archived "$file" || true

    elif [[ $file =~ codemap ]] || [[ $file =~ CODEMAP ]]; then
        print_info "Checking codemap: $file"
        validate_codemap "$file" || true
    fi

done <<< "$staged_files"

# Summary
echo ""
print_info "Checked $CHECKED files"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Found $ERRORS error(s)${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Also found $WARNINGS warning(s)${NC}"
    fi
    echo ""
    echo "Fix errors before committing:"
    echo "  - Add missing frontmatter fields"
    echo "  - Use lowercase, hyphens for names"
    echo "  - Include clear descriptions explaining when to use"
    exit 1
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Found $WARNINGS warning(s)${NC}"
    echo "Consider addressing these for better documentation:"
    echo "  - Improve descriptions (include 'when' guidance)"
    echo "  - Add optional metadata fields"
    echo ""
    print_success "Warnings are non-blocking, commit proceeding"
    exit 0
fi

print_success "All frontmatter validation passed!"
exit 0
