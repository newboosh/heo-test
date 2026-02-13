# CodeRabbit Loop Implementation Plan

## Overview

The CodeRabbit Loop is an automated system that processes CodeRabbit AI review comments on PRs. It is scoped to branches owned by the current worktree, preventing cross-worktree interference.

## Phase 1: Bug Fixes (COMPLETED)

### 1.1 Fix `gh_api` Data Handling
- **File:** `utils.py:86-122`
- **Fix:** Use stdin for JSON body data, add `fields` parameter for form data

### 1.2 Add File Locking for Tracker
- **File:** `comment_tracker.py`
- **Fix:** Added `fcntl.flock()` context manager for thread-safe file access

### 1.3 Add Tracker Size Limits
- **File:** `comment_tracker.py`
- **Fix:** Added `MAX_STORED_COMMENTS = 500` limit with automatic rotation

### 1.4 Improve Approval Detection Heuristics
- **File:** `check_cr_response.py`
- **Fix:** Added weighted scoring, context awareness, negation detection

### 1.5 Make Max Iterations Configurable
- **File:** `config.py` (new), `post_audit_log.py`, `post_final_summary.py`
- **Fix:** Centralized `MAX_ITERATIONS` constant with config overrides

---

## Phase 2: New Components (COMPLETED)

### 2.1 Configuration Module
- **File:** `config.py`
- Centralized constants with override support (.coderabbit-config.json, env vars)

### 2.2 Branch Tracker
- **File:** `loop/branch_tracker.py`
- Tracks which branches belong to this worktree
- Uses `NN--` prefix convention for automatic ownership detection (also supports legacy `NN---`)
- Commands: `list`, `register`, `unregister`, `is-owned`

### 2.3 Conflict Resolver
- **File:** `loop/conflict_resolver.py`
- Intelligent merge conflict resolution
- Strategy: Prioritize current branch, analyze context, include both if complementary
- Flags all automated resolutions for review
- Cites sources of competing changes

### 2.4 Orchestrator
- **File:** `loop/orchestrator.py`
- Main coordination script for the loop
- Outputs structured JSON for Claude Code to consume
- Handles: PR status, comments, conflicts, rate limits, exit signals

---

## Architecture

### Worktree Branch Ownership

```
Worktree: 05--coderabbitloop
├── Primary branch: 05--coderabbitloop (automatic)
├── Additional branches: (registered in .coderabbit-branches.json)
│   └── 05--coderabbitloop-hotfix
└── Prefix match: Any branch starting with "05--" is owned
```

Note: Legacy branches using `NN---` (3 dashes) are also supported.

### Loop Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Slash Command Entry                       │
│                    /coderabbit-loop                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Check Rate Limits                                        │
│     - If low: return pause recommendation                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Check Exit Signals                                       │
│     - @claude-code stop/pause/exit                          │
│     - If found: return stop                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Get Owned Branches                                       │
│     - Primary worktree branch                                │
│     - Registered additional branches                         │
│     - Prefix-matched branches                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. For Each PR from Owned Branches:                         │
│     a. Check PR status (mergeable, comments, reviewing)      │
│     b. If conflicts: analyze and prepare resolution          │
│     c. If comments: fetch with suggested fixes               │
│     d. Track iteration count                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Return Structured Output                                 │
│     - PR states (FIXING, WAITING, CONFLICTS, CLEAN, etc.)   │
│     - Comments with suggested fixes                          │
│     - Next action recommendation                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Claude Code Processes Output                             │
│     - Applies fixes based on comments                        │
│     - Resolves conflicts if needed                           │
│     - Commits and pushes                                     │
│     - Calls back to loop with incremented iteration          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         (Repeat until CLEAN or MAX_ITER)
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All PRs clean | Done |
| 10 | Fixes needed | Apply fixes from comments |
| 11 | Conflicts | Resolve merge conflicts |
| 12 | Waiting | Wait for CodeRabbit response |
| 13 | Rate limited | Pause and wait |
| 14 | Exit signal | Stop (user requested) |
| 15 | Max iterations | Escalate to human |
| 16 | Error | Investigate |

---

## Merge Conflict Resolution Strategy

1. **Prioritize current branch** - Our changes are primary
2. **Analyze context** - Compare ours/theirs/base versions
3. **Include both if complementary** - Non-overlapping additions merged
4. **Flag for review** - All automated resolutions marked
5. **Cite sources** - Commit SHAs of competing changes included

### Auto-Resolve Files

Lock files are auto-resolved by keeping current version:
- `package-lock.json`
- `yarn.lock`
- `poetry.lock`
- `Cargo.lock`
- `go.sum`

---

## Configuration

### Environment Variables

```bash
CODERABBIT_MAX_ITERATIONS=8
CODERABBIT_POLL_INTERVAL_SECONDS=30
CODERABBIT_WAIT_MINUTES=5
CODERABBIT_RATE_LIMIT_THRESHOLD=500
CODERABBIT_CONFLICT_STRATEGY=current_priority
```

### Config File (.coderabbit-config.json)

```json
{
  "MAX_ITERATIONS": 10,
  "CONFLICT_STRATEGY": "include_both",
  "CONFLICT_AUTO_RESOLVE_FILES": ["package-lock.json"]
}
```

---

## Files Created/Modified

### New Files
- `scripts/coderabbit/config.py` - Centralized configuration
- `scripts/coderabbit/loop/branch_tracker.py` - Branch ownership tracking
- `scripts/coderabbit/loop/conflict_resolver.py` - Merge conflict resolution
- `scripts/coderabbit/loop/orchestrator.py` - Main loop coordinator

### Modified Files
- `scripts/coderabbit/utils.py` - Fixed gh_api data handling
- `scripts/coderabbit/loop/comment_tracker.py` - Added locking & size limits
- `scripts/coderabbit/loop/check_cr_response.py` - Improved heuristics
- `scripts/coderabbit/loop/post_audit_log.py` - Configurable max iterations
- `scripts/coderabbit/loop/post_final_summary.py` - Configurable max iterations
- `.gitignore` - Added new tracking files

---

## Usage

### Status Check
```bash
python3 scripts/coderabbit/loop/orchestrator.py --status
```

### Process Current PR
```bash
python3 scripts/coderabbit/loop/orchestrator.py
```

### Process All Owned PRs
```bash
python3 scripts/coderabbit/loop/orchestrator.py --all
```

### JSON Output (for Claude Code)
```bash
python3 scripts/coderabbit/loop/orchestrator.py --json
```

---

## Future: Slash Command Integration

The orchestrator is designed to be called via `/coderabbit-loop` slash command:

```
/coderabbit-loop           # Process current branch PR
/coderabbit-loop --all     # Process all owned PRs
/coderabbit-loop --status  # Show status only
```

---

## Important Notes

1. **CodeRabbit handles merging** - This system does NOT merge PRs
2. **Worktree scoped** - Only processes branches owned by current worktree
3. **CI validates** - Conflict resolutions are flagged for CI review
4. **User control** - @claude-code stop/pause/exit signals respected
