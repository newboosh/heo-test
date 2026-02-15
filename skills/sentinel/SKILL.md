---
name: sentinel
description: Surface emerging issues discovered during work — workarounds, mocks, temporary code, disconnected features, deferred bugs, and ideas. Use at end-of-cycle, before gate decisions, or anytime to check what might have been forgotten.
argument-hint: [report|log|check|clear|export-issues]
allowed-tools: Read, Grep, Glob, Bash(*), Write, Edit, Task
---

# Sentinel — Emerging Issues Tracker

You manage the sentinel system that prevents emerging issues from being forgotten during autonomous work cycles.

## Commands

Parse `$ARGUMENTS` to determine which command to run:

| Command | What it does |
|---------|-------------|
| `report` (default) | Run the full sentinel consolidation and produce a report |
| `log <observation>` | Quickly log an explicit observation to `.sentinel/observations.md` |
| `check` | Quick scan — show current counts without full consolidation |
| `clear` | Archive the current report and reset for a new cycle |
| `export-issues` | Export unresolved findings to GitHub issues (strict criteria) |

---

## Command: `report`

**Trigger:** `/sentinel` or `/sentinel report`

Invoke the sentinel agent to produce a consolidated report:

1. **Spawn the sentinel agent** using the Task tool. The agent definition
   is at `agents/sentinel.md` with `tools: Read, Grep, Glob, Bash, Write`.
   Use `subagent_type="general-purpose"` with `model="haiku"` (single source
   of truth for the sentinel model):
   ```
   Task(subagent_type="general-purpose", model="haiku", prompt=<see below>)
   ```

2. **Agent prompt:**
   ```
   You are the Sentinel agent. Read the agent definition at agents/sentinel.md for your full instructions.

   Your task: produce a consolidated Sentinel Report.

   IMPORTANT — Three-Tier Scoping Model:
   - Explicit observations (.sentinel/observations.md): ALWAYS count — the agent deliberately logged these
   - Auto-detected issues (.sentinel/auto-detected.md): Already diff-scoped by the hook — trust the scope tags
   - Git diff analysis (your scan): Only flag NEW code you find in the diff — do NOT flag pre-existing issues

   Steps:
   1. Read .sentinel/observations.md (explicit observations from the primary agent)
   2. Read .sentinel/auto-detected.md (auto-detected issues from the hook)
   3. Run: git diff $(git merge-base HEAD main)..HEAD --stat
   4. For files with significant changes, scan NEW code only for sentinel patterns
   5. Deduplicate findings across all sources
   6. Categorize by severity and type
   7. Write the consolidated report to .sentinel/report.md

   Follow the report format defined in agents/sentinel.md exactly.
   If .sentinel/observations.md or .sentinel/auto-detected.md don't exist or are empty,
   note that in the report but still scan the git diff.
   ```

3. **After the agent returns**, read `.sentinel/report.md` and display the report to the user.

4. **If BLOCKING items exist**, warn:
   ```
   ⚠️  [N] blocking issue(s) found. These should be resolved before shipping.
   ```

---

## Command: `log`

**Trigger:** `/sentinel log <observation text>`

Quickly append an observation to `.sentinel/observations.md`. This is the low-friction capture path.

1. Create `.sentinel/` directory if it doesn't exist
2. Create or verify `.sentinel/observations.md` has a header:
   ```markdown
   # Sentinel Observations

   _Logged by the primary agent during work. Reviewed by sentinel at end-of-cycle._
   ```
3. Append the observation with timestamp:
   ```markdown
   ### [YYYY-MM-DD HH:MM] | During: [current task/branch]
   $ARGUMENTS (everything after "log")
   ```
4. Confirm: `[sentinel] Observation logged.`

**Example usage:**
```
/sentinel log type:workaround severity:important location:auth.py:45 — Using hardcoded JWT for testing. Proper fix: read from env var FLASK_JWT_SECRET
```

Or freeform:
```
/sentinel log Found a race condition in the stream handler when connections drop. Created a retry workaround but the root cause is the missing lock in StreamPool.acquire()
```

---

## Command: `check`

**Trigger:** `/sentinel check`

Quick status without full consolidation:

1. Check if `.sentinel/observations.md` exists → count entries (lines starting with `### `)
2. Check if `.sentinel/auto-detected.md` exists → count entries (lines starting with `- [`)
3. Check if `.sentinel/report.md` exists → show date and summary line
4. Display:
   ```
   [sentinel] Status:
     Observations:  N logged
     Auto-detected: N issues
     Last report:   [date] or "none"
   ```

---

## Command: `clear`

**Trigger:** `/sentinel clear`

Archive and reset for a new cycle:

1. Create `.sentinel/history/` directory if needed
2. If `.sentinel/report.md` exists, move it to `.sentinel/history/report-[YYYY-MM-DD-HHMMSS].md`
3. If `.sentinel/observations.md` exists, move it to `.sentinel/history/observations-[YYYY-MM-DD-HHMMSS].md`
4. If `.sentinel/auto-detected.md` exists, move it to `.sentinel/history/auto-detected-[YYYY-MM-DD-HHMMSS].md`
5. Confirm: `[sentinel] Cycle cleared. Previous report archived to .sentinel/history/`

---

## Command: `export-issues`

**Trigger:** `/sentinel export-issues`

Export unresolved sentinel findings to GitHub issues. This is the **last resort** — most issues should be fixed inline or resolved before the gate. Only findings that genuinely cannot be addressed in the current worktree should ever reach GitHub.

### Philosophy: Fix Inline First

Agentic coding is not human coding. An agent that discovers a problem mid-stream has the file open, the context loaded, and can fix it in seconds. The traditional issue-tracking workflow — file a ticket, context-switch away, rebuild context later — is pure waste when an agent can resolve it now.

**The sentinel escalation ladder:**

```text
1. Fix inline         — Agent fixes it immediately. No issue. Just part of the commit.
2. Local tracking     — .sentinel/report.md captures it. Resolved before the gate.
3. Export to GitHub   — Only if it survives the gate AND meets export criteria.
```

Most findings should never leave step 1. Step 3 is rare.

### Export Criteria

A finding qualifies for GitHub export **only if** it meets one or more of these criteria:

| Criterion | Description | Example |
|-----------|-------------|---------|
| **Cross-scope** | Fix belongs in a different worktree, branch, or module that this agent cannot safely modify | "The auth middleware in worktree-03 has a race condition, but we're in worktree-06" |
| **Human decision required** | The correct fix requires a judgment call that the agent should not make unilaterally | "Should this pattern be a warning or an error? Depends on team policy." |
| **Audit trail** | External visibility is needed for collaborators, compliance, or project tracking | "Security finding that needs documented acknowledgment" |
| **Genuinely deferred** | Real work that is intentionally and correctly out of scope for this sprint/phase | "Performance optimization identified but unrelated to current feature work" |

**What does NOT qualify:**

- Mechanical fixes (missing imports, formatting, simple bugs) — fix inline
- Anything the current agent can resolve without scope creep — fix inline
- Issues that just bounce back to the same agent — fix now
- Pre-existing issues in touched files — not your problem this cycle

### Process

```text
1. Verify .sentinel/report.md exists
   - If not: "No sentinel report found. Run /sentinel report first."

2. Read .sentinel/report.md

3. Filter findings by export criteria:
   - Scan DEFERRED section → likely candidates (genuinely out of scope)
   - Scan BLOCKING section → only if cross-scope (otherwise: fix it!)
   - Scan WORKAROUNDS section → only if cross-scope or human decision needed
   - Skip TEMPORARY/OBSERVATIONS/IDEAS → these are local concerns

4. For each candidate, classify which criterion it meets:
   - Tag: cross-scope | human-decision | audit-trail | deferred

5. Show the candidate list to the user for confirmation:
   "Found N findings that may warrant GitHub issues:

    1. [cross-scope] sentinel: race condition in auth middleware
       → Fix belongs in worktree-03, not here
    2. [human-decision] sentinel: warning vs error for deprecated API usage
       → Team policy decision needed
    3. [deferred] sentinel: O(n²) dedup in append_findings
       → Performance work, out of scope for this feature sprint

    Export all / Select which / Cancel?"

   Use AskUserQuestion with options:
     - "Export all" → create all listed issues
     - "Let me pick" → show each, let user select
     - "Cancel" → abort, nothing exported

6. For each approved finding, create a GitHub issue:

   Title: "sentinel: {description}"

   Body (markdown):
     ## Finding
     {description}

     ## Context
     - **Discovered in:** {branch/worktree}
     - **Location:** `{file:line}`
     - **Severity:** {severity}
     - **Report section:** {BLOCKING|WORKAROUNDS|DEFERRED}

     ## Export Reason
     {criterion}: {explanation of why this can't be fixed inline}

     ## Suggested Action
     {action from the sentinel report}

     ---
     _Exported from `.sentinel/report.md` by `/sentinel export-issues`_
     _Most sentinel findings are resolved inline. This one qualified for export because: {criterion}_

   Labels:
     - sentinel
     - sentinel:{criterion}  (e.g., sentinel:cross-scope, sentinel:deferred)
     - severity:{severity}   (e.g., severity:important, severity:minor)

7. Handle duplicates:
   - Before creating, search: gh issue list --search "sentinel: {description}" --json number,title
   - If found: skip and report "Issue already exists: #{number}"

8. Output summary:
   "[sentinel] Exported N issues to GitHub:
     #{num} sentinel: {title} [criterion]
     ...

   Remaining findings (N) resolved locally or not eligible for export."
```

### What This Replaces

The `/sprint export-issues` command exports **planned backlog tasks** (work you intend to do). `/sentinel export-issues` exports **discovered problems** (work you found but can't do here). They are complementary but serve different purposes.

---

## System Prompt Protocol

When this skill is active in a session, the primary agent should follow the **Sentinel Protocol** — logging observations to `.sentinel/observations.md` whenever it encounters issues outside its current task scope. The triggers are:

- Finding a bug while reading code for context
- Creating a workaround instead of a proper fix
- Writing a mock, stub, or placeholder
- Hardcoding a value that should be configurable
- Thinking of a better approach but taking the faster one
- Noticing something wrong that isn't the current focus
- Building something but not connecting it everywhere needed
- Skipping a test case that should exist
- Declaring work out of scope for the current task

Use `/sentinel log` for quick capture, or write directly to `.sentinel/observations.md`.

---

## Scoping Model

The sentinel system uses a **three-tier scoping model** to prevent pre-existing issues in touched files from blocking shipping of unrelated work:

| Layer | Scope | Rationale |
|-------|-------|-----------|
| Explicit observations (`/sentinel log`) | **Always count** | The agent deliberately noticed and logged it |
| Auto-detected (hook) | **Diff lines only** | Hook only scans added/modified lines, not pre-existing code |
| Git analysis (agent) | **New code only** | Agent only flags functions/routes/files created in this branch |

This means a file with 50 pre-existing TODOs won't trigger 50 findings when you edit one line in it. Only the line you changed (and any new code you wrote) gets flagged.

## Integration Points

| System | How Sentinel Integrates |
|--------|----------------------|
| Gate Decision (Phase 11) | BLOCKING items contribute to `sentinel.pass` signal |
| Retrospective (Phase 13) | Full report feeds into pattern analysis |
| `/tree close` | Run `/sentinel report` before PR creation |
| Sprint feedback | Unresolved items become backlog candidates |
| GitHub Issues | Only via `/sentinel export-issues` — strict criteria, user confirmation required |

## Composition

- **Pattern:** Decorator (wraps work cycle with observation + report)
- **Agent:** `agents/sentinel.md` (haiku, consolidation)
- **Hook:** `hooks/sentinel-detect.py` (diff-scoped auto-detection)
- **Library:** `hooks/lib/sentinel_patterns.py` (shared patterns)
- **Data:** `.sentinel/` directory (observations, auto-detected, report, history)
