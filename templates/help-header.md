---
description: Show available commands, flags, and usage for the heo plugin
---

# Heo Plugin Help

Show available commands organized by category. If `$ARGUMENTS` is provided, filter to matching commands or categories.

## Instructions

1. If `$ARGUMENTS` is empty, display the **Quick Start** then **Full Reference** below
2. If `$ARGUMENTS` matches a category name (e.g., "tree", "testing", "swarm"), display only that section
3. If `$ARGUMENTS` matches a command name (e.g., "catalog", "sprint-run"), display the detailed entry for that command
4. If `$ARGUMENTS` is "commands" show only the command list. If "skills" show only the skills list

Format output as a clean table. Use backticks for command syntax.

5. If `$ARGUMENTS` is "check" or "--check", run the drift-check script:
   ```bash
   python3 "${PLUGIN_DIR}/scripts/generate-help.py" --check
   ```
   Where `${PLUGIN_DIR}` is the heo plugin's installation path. Report the output to the user.

---

## Quick Start

```text
# Starting a new feature:
/heo:plan Add user preferences page
/heo:tdd app/services/preferences.py

# Working with worktrees:
/heo:tree stage Add user preferences
/heo:tree stage Fix login bug
/heo:tree build

# After finishing work:
/heo:verify pre-pr
/heo:push "feat: add user preferences"

# Running a full sprint:
/heo:sprint-run attended Add export functionality

# Investigating a bug:
/heo:bug "Login fails after password reset"

# Getting a code review:
/heo:code-review
```

---

## Full Reference
