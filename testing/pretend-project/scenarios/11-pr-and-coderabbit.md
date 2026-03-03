# Scenario 11: Pull Request and CodeRabbit Workflow

## Features Exercised

- Commands: `/push`, `/pr-status`, `/coderabbit`, `/coderabbitloop`,
  `/coderabbit-status`, `/coderabbit-process`, `/coderabbit-conflicts`
- Agents: git-orchestrator

## Prerequisites

Scenarios 04-06 completed (feature implemented, verified, reviewed).
The auth worktree has committed, clean code ready for a PR.

## Setup

This scenario requires a GitHub repository with CodeRabbit configured.
If testing without GitHub, the prompts still exercise the command parsing
and error handling paths.

## Prompts

### Prompt 11-A: Push and Create PR

```text
The auth feature is complete. Push this branch and create a pull request.

Use /push with a descriptive commit message.
```

**What Should Happen:**
- Claude invokes `/push` which spawns the git-orchestrator agent.
- The agent:
  1. Stages all changes
  2. Creates a commit with a descriptive message
  3. Pushes the feature branch to remote
  4. Creates a PR via GitHub API (gh pr create)
  5. Sets PR title, description, labels
- PR description includes: summary of changes, test results, coverage.

**Checkpoint:** PR created on GitHub. Branch pushed. PR has a descriptive
title and body.

---

### Prompt 11-B: Check PR Status

```text
/pr-status
```

**What Should Happen:**
- Claude invokes `/pr-status` which checks:
  - PR state (open, review requested, changes requested)
  - CI status (checks passing/failing)
  - Reviewer assignments
  - Comment count

**Checkpoint:** PR status displayed with current state.

---

### Prompt 11-C: Request CodeRabbit Review

```text
Request a CodeRabbit review on this PR.

Use /coderabbit.
```

**What Should Happen:**
- Claude invokes `/coderabbit` which:
  - Triggers a CodeRabbit review on the PR
  - Waits for the review to complete
  - Fetches review comments
  - Summarizes findings

**Checkpoint:** CodeRabbit review triggered. Findings displayed.

---

### Prompt 11-D: Check CodeRabbit Status

```text
/coderabbit-status
```

**What Should Happen:**
- Shows the current state of CodeRabbit's review: pending, in progress,
  or completed with summary.

**Checkpoint:** Status accurately reflects CodeRabbit's state.

---

### Prompt 11-E: Process CodeRabbit Comments

```text
Fix all the issues CodeRabbit found and push the fixes.

Use /coderabbit-process.
```

**What Should Happen:**
- Claude invokes `/coderabbit-process` which:
  1. Fetches all CodeRabbit comments
  2. Groups by severity and file
  3. Fixes each issue
  4. Resolves the comment threads
  5. Commits and pushes fixes

**Checkpoint:** All CodeRabbit comments addressed. New commit pushed. Comment
threads resolved.

---

### Prompt 11-F: CodeRabbit Loop

```text
Keep iterating with CodeRabbit until it approves the PR. Fix every issue it
raises.

Use /coderabbitloop --max-iterations 3.
```

**What Should Happen:**
- Claude invokes `/coderabbitloop` which:
  1. Triggers CodeRabbit review
  2. Reads comments
  3. Fixes issues
  4. Pushes fixes
  5. Triggers another review
  6. Repeats until approved or max iterations reached
- Stops when CodeRabbit approves or iteration limit hit.

**Checkpoint:** PR reaches CodeRabbit approval, or loop terminates at max
iterations with remaining issues listed.

---

### Prompt 11-G: Handle Merge Conflicts

```text
The PR has merge conflicts with another branch that was merged first. Resolve
them.

Use /coderabbit-conflicts.
```

**What Should Happen:**
- Claude invokes `/coderabbit-conflicts` which:
  - Identifies conflicting files
  - Merges/rebases from the target branch
  - Resolves conflicts (preferring the feature branch changes where
    appropriate, merging where both changes are needed)
  - Pushes the resolution

**Checkpoint:** Conflicts resolved. PR is mergeable again.
