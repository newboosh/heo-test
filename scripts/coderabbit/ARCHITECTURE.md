# CodeRabbit Loop Architecture

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WORKTREE CONTEXT                                │
│  ┌─────────────────┐                                                        │
│  │ 05--coderabbit  │ ◄── Current worktree owns branches with "05--" prefix  │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BRANCH OWNERSHIP                                  │   │
│  │  Primary: 05--coderabbitloop                                        │   │
│  │  Owned:   05--* (any branch with same prefix)                       │   │
│  │  File:    .coderabbit-branches.json                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Main Loop Flow

```text
                              ┌──────────────────┐
                              │  /coderabbit-loop │
                              │   (slash command) │
                              └────────┬─────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────┐
                    │      ORCHESTRATOR ENTRY          │
                    │      orchestrator.py             │
                    └──────────────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │  CHECK RATE     │    │  CHECK EXIT     │    │  GET OWNED      │
    │  LIMITS         │    │  SIGNALS        │    │  BRANCHES       │
    │                 │    │                 │    │                 │
    │ check_rate_     │    │ check_exit_     │    │ branch_         │
    │ limits.py       │    │ signals.py      │    │ tracker.py      │
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                      │                      │
             │  < 500 remaining?    │  @claude-code stop?  │
             │                      │                      │
             ▼                      ▼                      ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     GATE CHECK                                   │
    │  If rate limited → PAUSE                                        │
    │  If exit signal  → STOP                                         │
    │  Otherwise       → CONTINUE                                     │
    └─────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │     FOR EACH OWNED PR           │
                    │     (up to MAX_ITERATIONS)      │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │    CHECK PR STATUS     │
                         │    check_pr_status.py  │
                         └────────────┬───────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
  │   CONFLICTS?    │      │   REVIEWING?    │      │   COMMENTS?     │
  │                 │      │                 │      │                 │
  │ mergeable ==    │      │ CodeRabbit      │      │ unresolved      │
  │ CONFLICTING     │      │ still working   │      │ threads > 0     │
  └────────┬────────┘      └────────┬────────┘      └────────┬────────┘
           │                        │                        │
           ▼                        ▼                        ▼
  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
  │ CONFLICT        │      │ WAITING         │      │ FETCH           │
  │ RESOLVER        │      │ STATE           │      │ COMMENTS        │
  │                 │      │                 │      │                 │
  │ conflict_       │      │ Return and      │      │ fetch_          │
  │ resolver.py     │      │ poll later      │      │ comments.py     │
  └────────┬────────┘      └─────────────────┘      └────────┬────────┘
           │                                                  │
           ▼                                                  ▼
  ┌─────────────────┐                              ┌─────────────────┐
  │ Analyze:        │                              │ Parse:          │
  │ - ours/theirs   │                              │ - Inline        │
  │ - base          │                              │ - General       │
  │ - context       │                              │ - Suggestions   │
  │                 │                              │ - Severity      │
  │ Resolve:        │                              │ - Rule #        │
  │ - Current prio  │                              └────────┬────────┘
  │ - Include both  │                                       │
  │ - Flag review   │                                       │
  └────────┬────────┘                                       │
           │                                                │
           └───────────────────────┬────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      RETURN TO CLAUDE CODE   │
                    │                              │
                    │  Structured JSON output:     │
                    │  - PR states                 │
                    │  - Comments to fix           │
                    │  - Suggested changes         │
                    │  - Next action               │
                    └──────────────────┬───────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────┐
                    │      CLAUDE CODE APPLIES     │
                    │      FIXES                   │
                    │                              │
                    │  (External - not in loop)    │
                    └──────────────────┬───────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────┐
                    │      COMMIT & PUSH           │
                    └──────────────────┬───────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────┐
                    │      POST AUDIT LOG          │
                    │      post_audit_log.py       │
                    └──────────────────┬───────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────┐
                    │      WAIT FOR CODERABBIT     │
                    │      check_cr_response.py    │
                    └──────────────────┬───────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
      ┌───────────┐           ┌───────────┐            ┌───────────┐
      │ APPROVED  │           │ REJECTED  │            │ PENDING   │
      └─────┬─────┘           └─────┬─────┘            └─────┬─────┘
            │                       │                        │
            ▼                       ▼                        ▼
      ┌───────────┐           ┌───────────┐            ┌───────────┐
      │ PR CLEAN  │           │ LOOP BACK │            │ WAIT MORE │
      │ Exit loop │           │ iteration++│            │ Poll again│
      └───────────┘           └───────────┘            └───────────┘
```

## State Machine

```text
                                    ┌─────────┐
                                    │  START  │
                                    └────┬────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │       READY         │
                              │  (Initial state)    │
                              └──────────┬──────────┘
                                         │
         ┌───────────────┬───────────────┼───────────────┬───────────────┐
         │               │               │               │               │
         ▼               ▼               ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐   ┌───────────┐   ┌──────────┐    ┌─────────┐
    │ FIXING  │    │ CONFLICTS│   │  WAITING  │   │RATE_LIMIT│    │ STOPPED │
    │         │    │          │   │           │   │          │    │         │
    │Comments │    │ Merge    │   │ CodeRabbit│   │ API quota│    │ User    │
    │to fix   │    │ needed   │   │ reviewing │   │ low      │    │ request │
    └────┬────┘    └────┬─────┘   └─────┬─────┘   └────┬─────┘    └────┬────┘
         │              │               │              │               │
         │              │               │              │               │
         ▼              ▼               ▼              ▼               ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                         ITERATION CHECK                             │
    │                    iteration < MAX_ITERATIONS?                      │
    └──────────────────────────────┬──────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
             ┌───────────┐  ┌───────────┐  ┌───────────┐
             │   CLEAN   │  │ MAX_ITER  │  │  CLOSED   │
             │           │  │           │  │           │
             │ No issues │  │ Escalate  │  │ PR closed │
             │ await     │  │ to human  │  │ no merge  │
             │ merge     │  │           │  │           │
             └─────┬─────┘  └───────────┘  └───────────┘
                   │
                   │ Poll for merge status
                   ▼
             ┌───────────┐
             │  MERGED   │◄─── SUCCESS EXIT!
             │           │
             │ CodeRabbit│     Only exit code 0
             │ merged PR │     when PR is merged
             └─────┬─────┘
                   │
                   ▼
          ┌───────────────┐
          │ POST SUMMARY  │
          │post_final_    │
          │summary.py     │
          └───────────────┘
```

**Key Point:** The loop does NOT exit just because comments are resolved.
It continues polling until CodeRabbit actually merges the PR.

## Component Interactions

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORCHESTRATOR                                      │
│                          orchestrator.py                                     │
│                                                                              │
│  Coordinates all components, manages state, returns structured output       │
└───────┬─────────────┬─────────────┬─────────────┬─────────────┬────────────┘
        │             │             │             │             │
        ▼             ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│  CONFIG   │  │  UTILS    │  │  BRANCH   │  │  COMMENT  │  │  CONFLICT │
│           │  │           │  │  TRACKER  │  │  TRACKER  │  │  RESOLVER │
│config.py  │  │utils.py   │  │branch_    │  │comment_   │  │conflict_  │
│           │  │           │  │tracker.py │  │tracker.py │  │resolver.py│
├───────────┤  ├───────────┤  ├───────────┤  ├───────────┤  ├───────────┤
│MAX_ITER=8 │  │gh_api()   │  │get_owned_ │  │record()   │  │analyze()  │
│POLL=30s   │  │gh_api_    │  │branches() │  │analyze()  │  │resolve()  │
│THRESHOLD  │  │graphql()  │  │is_owned() │  │suggest()  │  │apply()    │
│=500       │  │eprint()   │  │register() │  │reset()    │  │cite()     │
└───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
                    │
                    ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                      GITHUB API                               │
        │                                                               │
        │  GraphQL: reviewThreads, comments, pullRequest status        │
        │  REST: rate_limit, pr comment, pr view                       │
        └───────────────────────────────────────────────────────────────┘
```

## File Structure

```text
scripts/coderabbit/
│
├── __init__.py
├── config.py              ◄── Configuration constants & overrides
├── utils.py               ◄── GitHub API helpers, git utilities
├── smart_resolver.py      ◄── Auto-resolve non-security comments
├── check_pr_status.py     ◄── Comprehensive PR health check
│
├── loop/
│   ├── __init__.py
│   ├── orchestrator.py    ◄── MAIN ENTRY POINT - coordinates everything
│   ├── branch_tracker.py  ◄── Worktree branch ownership
│   ├── fetch_comments.py  ◄── Parse CodeRabbit comments & suggestions
│   ├── check_cr_response.py   ◄── Detect approval/rejection
│   ├── check_rate_limits.py   ◄── GitHub API quota monitoring
│   ├── check_exit_signals.py  ◄── User stop/pause detection
│   ├── conflict_resolver.py   ◄── Intelligent merge resolution
│   ├── comment_tracker.py     ◄── Pattern analysis across PRs
│   ├── post_reply.py          ◄── Reply to review threads
│   ├── post_audit_log.py      ◄── Log actions to PR
│   └── post_final_summary.py  ◄── End-of-loop summary
│
├── tests/
│   ├── __init__.py
│   └── test_coderabbit.py ◄── Unit tests (24 tests)
│
├── ARCHITECTURE.md        ◄── This file
└── IMPLEMENTATION_PLAN.md ◄── Implementation details
```

## Data Flow

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GitHub PR     │     │   Orchestrator  │     │   Claude Code   │
│                 │     │                 │     │                 │
│  - Comments     │────▶│  - Fetch        │────▶│  - Read output  │
│  - Status       │     │  - Parse        │     │  - Apply fixes  │
│  - Conflicts    │     │  - Analyze      │     │  - Commit       │
│                 │◀────│  - Output JSON  │◀────│  - Push         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TRACKING FILES                          │
│                                                                 │
│  .coderabbit-tracker.json    Pattern analysis, PR counts       │
│  .coderabbit-branches.json   Registered branch ownership       │
│  .coderabbit-config.json     User config overrides (optional)  │
└─────────────────────────────────────────────────────────────────┘
```

## Exit Codes

```text
┌──────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR EXIT CODES                     │
├────────┬──────────────────────┬──────────────────────────────────┤
│  Code  │  Meaning             │  Claude Code Action              │
├────────┼──────────────────────┼──────────────────────────────────┤
│   0    │  DONE (MERGED)       │  PR merged by CodeRabbit! Exit   │
│  10    │  APPLY_FIXES         │  Read comments, apply fixes      │
│  11    │  RESOLVE_CONFLICTS   │  Handle merge conflicts          │
│  12    │  WAIT                │  Waiting for CodeRabbit review   │
│  13    │  AWAIT_MERGE         │  PR clean, wait for CR to merge  │
│  14    │  PAUSE               │  Wait for rate limit reset       │
│  15    │  STOP                │  User requested stop             │
│  16    │  ESCALATE            │  Max iterations, need human      │
│  17    │  ERROR               │  Investigate failure             │
│  18    │  CLOSED              │  PR closed without merge         │
└────────┴──────────────────────┴──────────────────────────────────┘
```

**Important:** The loop only exits successfully (code 0) when CodeRabbit
merges the PR. A "clean" PR (no comments) still waits for merge.

## Merge Conflict Resolution Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONFLICT DETECTED                                    │
│                    PR mergeable == "CONFLICTING"                            │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │    FETCH CONFLICT DETAILS      │
                    │                                │
                    │  git show :1:file (base)       │
                    │  git show :2:file (ours)       │
                    │  git show :3:file (theirs)     │
                    └───────────────┬────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────────┐
                    │    ANALYZE CONTEXT             │
                    │                                │
                    │  - Lines added/removed         │
                    │  - Overlapping changes?        │
                    │  - Complementary changes?      │
                    └───────────────┬────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │  LOCK FILE?    │   │  COMPLEMENTARY │   │  OVERLAPPING   │
     │                │   │                │   │                │
     │ package-lock   │   │ Non-overlapping│   │ Same lines     │
     │ yarn.lock etc  │   │ additions      │   │ modified       │
     └───────┬────────┘   └───────┬────────┘   └───────┬────────┘
             │                    │                    │
             ▼                    ▼                    ▼
     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │ Keep ours,     │   │ INCLUDE BOTH   │   │ CURRENT BRANCH │
     │ regenerate     │   │                │   │ PRIORITY       │
     │ after          │   │ Merge both     │   │                │
     │                │   │ additions      │   │ Keep ours,     │
     │ needs_review:  │   │                │   │ discard theirs │
     │ false          │   │ needs_review:  │   │                │
     └───────┬────────┘   │ true           │   │ needs_review:  │
             │            └───────┬────────┘   │ true           │
             │                    │            └───────┬────────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────────┐
                    │    GENERATE CITATION           │
                    │                                │
                    │  "Conflict resolved by..."     │
                    │  "Kept: Current (abc123)"      │
                    │  "Discarded: Incoming (def456)"│
                    │  "FLAGGED FOR REVIEW"          │
                    └───────────────┬────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────────┐
                    │    COMMIT WITH CITATION        │
                    │                                │
                    │  Commit message includes:      │
                    │  - Resolution strategy         │
                    │  - Source commits              │
                    │  - Review flag                 │
                    └────────────────────────────────┘
```

## Pattern Analysis Cycle

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMMENT TRACKER CYCLE                                │
│                                                                              │
│  Runs every 12 PRs to identify recurring issues                             │
└─────────────────────────────────────────────────────────────────────────────┘

     PR 1        PR 2        PR 3       ...       PR 12
       │           │           │                    │
       ▼           ▼           ▼                    ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐         ┌─────────┐
  │ record  │ │ record  │ │ record  │   ...   │ record  │
  │ comment │ │ comment │ │ comment │         │ comment │
  └────┬────┘ └────┬────┘ └────┬────┘         └────┬────┘
       │           │           │                    │
       └───────────┴───────────┴────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ ANALYSIS DUE?   │
                    │ pr_count >= 12  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────────────────────┐
                    │          ANALYZE                │
                    │                                 │
                    │  - Count by rule number         │
                    │  - Count by file                │
                    │  - Count by severity            │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │          SUGGEST                │
                    │                                 │
                    │  "Rule #5 violated 5 times      │
                    │   → add pre-commit hook"        │
                    │                                 │
                    │  "file.py has 8 comments        │
                    │   → consider refactoring"       │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │          RESET                  │
                    │                                 │
                    │  Clear comments, reset counter  │
                    │  Start new 12-PR cycle          │
                    └─────────────────────────────────┘
```
