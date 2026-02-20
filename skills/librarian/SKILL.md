---
name: librarian
description: Documentation management commands for auditing, scanning, and finding files.
argument-hint: <command> [args]
model: sonnet
allowed-tools: Read, Grep, Glob, Bash, Edit
---

# Librarian Commands

Execute librarian system commands for documentation and file management.

## Available Commands

### /librarian audit
Launch comprehensive documentation audit.

**Usage:** `/librarian audit [scope]`

**Scope options:**
- `full` - All directories (default)
- `app` - Only app/ directory
- `tests` - Only tests/ directory
- `docs` - Only docs/ directory

**What it does:**
1. Launches librarian agent
2. Analyzes file organization
3. Checks test coverage mapping
4. Identifies documentation gaps
5. Generates prioritized recommendations

**Output:** Detailed audit report with metrics and action plan

---

### /librarian scan
Quick scan of project structure and metrics.

**Usage:** `/librarian scan`

**What it does:**
```bash
# Count files by type
echo "=== File Counts ==="
find app -name "*.py" -type f | wc -l
find tests -name "*.py" -type f | wc -l
find docs -name "*.md" -type f | wc -l

# Check for common issues
echo "=== Potential Issues ==="
grep -rl "TODO\|FIXME" app/ | wc -l
grep -rL '"""' app/*.py 2>/dev/null | wc -l
```

**Output:** Quick metrics summary

---

### /librarian find <query>
Find files related to a concept or feature.

**Usage:** `/librarian find "authentication"`

**What it does:**
1. Searches file names for query
2. Searches file contents for query
3. Searches git history for query
4. Returns ranked results with context

**Output:** List of relevant files with relevance indicators

---

### /librarian place <description>
Get file placement recommendation.

**Usage:** `/librarian place "new utility for date formatting"`

**What it does:**
1. Analyzes description
2. Applies FILE_ORGANIZATION_STANDARDS
3. Checks for similar existing files
4. Returns recommended path with rationale

**Output:** Recommended file path and reasoning

---

### /librarian stale [days]
Find potentially stale documentation.

**Usage:** `/librarian stale 90`

**What it does:**
```bash
# Find docs not modified in N days
find docs -name "*.md" -mtime +90 -type f

# Compare doc dates to related code
# (shows docs older than their related code)
```

**Output:** List of potentially outdated files

---

### /librarian coverage
Show test-to-source mapping.

**Usage:** `/librarian coverage`

**What it does:**
1. Lists all app/ modules
2. Lists all test files
3. Shows which modules have tests
4. Highlights gaps

**Output:** Coverage matrix with gap identification

---

### /librarian orphans
Find orphaned files (not imported/referenced).

**Usage:** `/librarian orphans`

**What it does:**
1. Scans all Python files
2. Builds import graph
3. Identifies files never imported
4. Excludes entry points and tests

**Output:** List of potentially orphaned files

---

### /librarian status
Show librarian system status.

**Usage:** `/librarian status`

**Output:**
```
=== Librarian Status ===
Last audit: [date or "never"]
Files tracked: X
Test coverage: X%
Documentation files: X
Known issues: X

Quick actions:
- /librarian scan - Quick metrics
- /librarian audit - Full audit
- /librarian stale - Find outdated docs
```

## Implementation Notes

When user types `/librarian <command>`:

1. **audit** → Launch librarian agent with Task tool
2. **scan** → Run quick bash commands inline
3. **find** → Use Grep/Glob for search
4. **place** → Apply decision tree from standards
5. **stale** → Run find with mtime
6. **coverage** → Compare app/ to tests/
7. **orphans** → Build and analyze import graph
8. **status** → Show cached metrics or run quick scan

## Examples

```bash
# Run full audit
/librarian audit

# Quick health check
/librarian scan

# Find auth-related files
/librarian find "oauth"

# Where should this go?
/librarian place "celery task for email notifications"

# What docs need updating?
/librarian stale 60

# What modules lack tests?
/librarian coverage
```
