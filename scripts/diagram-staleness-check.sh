#!/bin/bash
# Diagram Staleness Check
#
# Reads docs/DIAGRAM_SOURCES.yaml and checks whether any staged source files
# are associated with diagrams that are NOT also staged. If so, prints a
# non-blocking warning listing which diagrams may need updating.
#
# Usage:
#   As a pre-commit hook:  scripts/diagram-staleness-check.sh
#   Manual check:          scripts/diagram-staleness-check.sh [--all]
#     --all   Compare against last commit instead of staged files
#
# Compatible with bash 3.2+ (macOS default) — no associative arrays.

set -e

# Colors
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

# ─── Locate manifest ─────────────────────────────────────────────────────────

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Not in a git repository." >&2
    exit 0
}

MANIFEST="$REPO_ROOT/docs/DIAGRAM_SOURCES.yaml"

if [ ! -f "$MANIFEST" ]; then
    exit 0  # No manifest, nothing to check
fi

# ─── Determine changed files ─────────────────────────────────────────────────

if [ "$1" = "--all" ]; then
    # Compare working tree against last commit
    CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || true)
else
    # Pre-commit mode: staged files only
    CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
fi

if [ -z "$CHANGED_FILES" ]; then
    exit 0
fi

# ─── Parse manifest (awk, no yq dependency) ──────────────────────────────────
#
# Extracts entries as tab-separated lines:
#   DIAGRAM_FILE<TAB>SECTION<TAB>SOURCE

parse_manifest() {
    awk '
    /^  - diagram_file:/ {
        gsub(/^  - diagram_file: */, "")
        diagram = $0
        section = ""
        next
    }
    /^    section:/ {
        gsub(/^    section: *"?/, "")
        gsub(/"$/, "")
        section = $0
        next
    }
    /^      - / {
        gsub(/^      - */, "")
        source = $0
        print diagram "\t" section "\t" source
    }
    ' "$MANIFEST"
}

PARSED=$(parse_manifest)

# ─── Match changed files against manifest sources ────────────────────────────
#
# Collects hits as lines of:  DIAGRAM_FILE<TAB>SECTION<TAB>CHANGED_SOURCE
# Uses a temp file to avoid subshell variable scoping issues.

HITS_FILE=$(mktemp)
trap "rm -f '$HITS_FILE'" EXIT

while IFS= read -r changed_file; do
    [ -z "$changed_file" ] && continue

    while IFS="$(printf '\t')" read -r diagram_file section source; do
        [ -z "$diagram_file" ] && continue

        # Match: exact path or directory prefix (trailing /)
        matched=false
        if [[ "$source" == *"*"* || "$source" == *"?"* || "$source" == *"["* ]]; then
            case "$changed_file" in
                $source) matched=true ;;
            esac
        else
            case "$source" in
                */) [ "${changed_file#$source}" != "$changed_file" ] && matched=true ;;
                *)  [ "$changed_file" = "$source" ] && matched=true ;;
            esac
        fi
        $matched || continue

        # Skip if the diagram file is also in the commit
        if echo "$CHANGED_FILES" | grep -qxF "$diagram_file"; then
            continue
        fi

        printf '%s\t%s\t%s\n' "$diagram_file" "$section" "$changed_file" >> "$HITS_FILE"
    done <<< "$PARSED"
done <<< "$CHANGED_FILES"

# ─── Deduplicate and report ──────────────────────────────────────────────────

if [ ! -s "$HITS_FILE" ]; then
    exit 0
fi

# Sort and deduplicate
sort -u "$HITS_FILE" > "${HITS_FILE}.sorted"
mv "${HITS_FILE}.sorted" "$HITS_FILE"

echo ""
echo -e "${YELLOW}⚠  STALE DIAGRAM WARNING${NC}"
echo -e "${DIM}───────────────────────────────────────────────────${NC}"
echo ""

# Group output by diagram file
current_diagram=""
while IFS="$(printf '\t')" read -r diagram_file section changed_source; do
    if [ "$diagram_file" != "$current_diagram" ]; then
        # Close previous group
        if [ -n "$current_diagram" ]; then
            echo ""
            echo -e "  ${DIM}Affected diagrams:${NC}"
            # Re-scan for sections belonging to this diagram
            grep "^${current_diagram}	" "$HITS_FILE" | cut -f2 | sort -u | while IFS= read -r s; do
                echo -e "    - ${s}"
            done
            echo ""
            echo -e "${DIM}───────────────────────────────────────────────────${NC}"
            echo ""
        fi

        current_diagram="$diagram_file"
        echo -e "  ${BLUE}${diagram_file}${NC} may need updating"
        echo ""
        echo -e "  ${DIM}Changed sources:${NC}"

        # Print all unique sources for this diagram
        grep "^${diagram_file}	" "$HITS_FILE" | cut -f3 | sort -u | while IFS= read -r src; do
            echo -e "    ${src}"
        done
    fi
done < <(cut -f1 "$HITS_FILE" | sort -u)

# Close final group
if [ -n "$current_diagram" ]; then
    echo ""
    echo -e "  ${DIM}Affected diagrams:${NC}"
    grep "^${current_diagram}	" "$HITS_FILE" | cut -f2 | sort -u | while IFS= read -r s; do
        echo -e "    - ${s}"
    done
    echo ""
    echo -e "${DIM}───────────────────────────────────────────────────${NC}"
fi

echo ""
echo -e "${DIM}To suppress: include the diagram file in your commit.${NC}"
echo -e "${DIM}Manifest:    docs/DIAGRAM_SOURCES.yaml${NC}"
echo ""

# Non-blocking — always exit 0
exit 0
