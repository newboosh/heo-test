# Scenario 03: Worktree-Based Parallel Development

## Features Exercised

- Commands: `/tree stage`, `/tree list`, `/tree build`, `/tree sync`,
  `/tree status`, `/tree refresh`, `/tree restore`, `/branch`,
  `/catalog build`
- Skills: tree (worktree-management), worktree-management, catalog
- Hooks: pre-cross-worktree-warning (auto)

## Prerequisites

Scenario 02 completed (sprint planned, features identified).

## Prompts

### Prompt 03-A: Stage Features

```text
I want to develop these features in parallel using worktrees:

1. User authentication (JWT login/register)
2. Task CRUD (create, read, update, delete tasks)
3. Workspace management (multi-tenant isolation)

Stage these for worktree creation.
```

**What Should Happen:**
- Claude invokes `/tree stage "User authentication - JWT login and register"`
  three times (once per feature), or uses a batch syntax.
- Each feature is added to the staging list.
- `/tree list` shows all three staged features.

**Checkpoint:** `/tree list` output shows 3 staged features with descriptions.

---

### Prompt 03-B: Build Worktrees

```text
Build worktrees for all staged features.
```

**What Should Happen:**
- Claude invokes `/tree build`.
- Three worktrees are created, each on its own branch:
  - e.g., `feat/user-authentication`
  - e.g., `feat/task-crud`
  - e.g., `feat/workspace-management`
- Each worktree has its own working directory.
- CLAUDE.md in each worktree is updated with task context.
- The staging list is cleared after successful build.

**Checkpoint:** `git worktree list` shows 3 worktrees plus the main one.
Each has a PURPOSE.md describing its task.

---

### Prompt 03-C: Check Worktree Status

```text
/tree status
```

**What Should Happen:**
- Shows all active worktrees with their branch names, purposes, and status
  (clean/dirty).
- Indicates which worktree you're currently in.

**Checkpoint:** Status output lists all worktrees with accurate state.

---

### Prompt 03-D: Work in a Worktree

```text
Switch to the authentication worktree and check its status.
```

**What Should Happen:**
- Claude identifies the auth worktree path and provides navigation guidance.
- If already in a worktree, `/tree status` shows current context.
- The CLAUDE.md in the auth worktree scopes work to authentication only.

**Checkpoint:** Working in the auth worktree. CLAUDE.md shows auth task.

---

### Prompt 03-E: Sync Worktree

```text
Sync this worktree with the latest changes from the base branch.
```

**What Should Happen:**
- Claude invokes `/tree sync`.
- Fetches latest from the base branch and rebases/merges.
- Reports any conflicts (there shouldn't be any yet since no one has merged).

**Checkpoint:** Worktree is up to date. No conflicts reported.

---

### Prompt 03-F: Rebuild Catalog After Changes

```text
I've added some files in this worktree. Rebuild the catalog.
```

**What Should Happen:**
- Claude invokes `/catalog build`.
- Re-scans the project and updates catalog.yaml with new files.

**Checkpoint:** catalog.yaml reflects current file state.

---

### Prompt 03-G: Cross-Worktree Warning (Hook Test)

```text
Open the file src/taskhive/app.py from the main worktree and add a comment.
```

**What Should Happen:**
- If editing a file that belongs to a different worktree, the
  pre-cross-worktree-warning hook fires.
- Claude receives a warning that it's editing outside its worktree scope.

**Checkpoint:** Warning message appears about cross-worktree editing.

---

### Prompt 03-H: Branch Helper

```text
/branch
```

**What Should Happen:**
- Shows the current branch name and provides branch management utilities.

**Checkpoint:** Branch name displayed matches the worktree's feature branch.

---

### Prompt 03-I: Refresh Commands

```text
/tree refresh
```

**What Should Happen:**
- Checks that all slash commands are available and properly loaded.
- Reports any commands that failed to load.

**Checkpoint:** All commands show as available.

---

### Prompt 03-J: Restore Terminals

```text
/tree restore
```

**What Should Happen:**
- Restores terminal sessions for all existing worktrees.
- Useful after a reboot or terminal crash.

**Checkpoint:** Terminal sessions restored (or reported as already active).
