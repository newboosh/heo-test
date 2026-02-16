# Test Plugin

Run the comprehensive heo plugin test suite to verify that agents, commands, skills, and hooks are properly installed and working.

## Usage

```text
/test-plugin                     # Full test suite
/test-plugin --only hooks        # Test only hooks
/test-plugin --only structure    # Test only plugin structure
/test-plugin --dry-run           # Show what would run without executing
/test-plugin --skip-scaffold     # Skip project scaffolding (already have a project)
```

## Instructions

Run the plugin test suite script located in the plugin root directory:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/test-plugin-full.sh" $ARGUMENTS
```

The script will:
1. **Scaffold** a minimal Python/Flask project (unless `--skip-scaffold` is passed)
2. **Validate plugin structure** — checks that agents/, commands/, skills/, hooks/ exist with valid files
3. **Test hooks** — verifies hook syntax, imports, and functional behavior (e.g., git safety blocks)
4. **Test agents** — smoke-tests each agent via `claude -p` prompts
5. **Test commands** — smoke-tests each slash command via `claude -p` prompts
6. **Test skills** — smoke-tests each skill via `claude -p` prompts
7. **Integration tests** — verifies Claude can see and use plugin components

### Running from a project directory

If running from a project where the plugin is installed (not from the plugin root), the script auto-detects the plugin location via `CLAUDE_PLUGIN_ROOT`. You can also specify it explicitly:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/test-plugin-full.sh" --plugin-dir "${CLAUDE_PLUGIN_ROOT}" $ARGUMENTS
```

### Quick validation (no Claude CLI needed)

For a fast structural check without invoking `claude -p`:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/test-plugin-full.sh" --only structure --skip-scaffold
bash "${CLAUDE_PLUGIN_ROOT}/test-plugin-full.sh" --only hooks --skip-scaffold
```

### Test report

Results are written to `test-report.json` in the current directory. Use `--report <file>` to change the output path.

## Arguments

```
$ARGUMENTS:
  (none)              → Full test suite (all phases)
  --only <category>   → Run one category: agents|commands|skills|hooks|structure|integration
  --skip-scaffold     → Skip project scaffolding
  --skip-agents       → Skip agent tests
  --skip-commands     → Skip command tests
  --skip-skills       → Skip skill tests
  --skip-hooks        → Skip hook tests
  --dry-run           → Print what would run without executing
  --verbose           → Show full claude output for each test
  --cleanup           → Remove scaffold files after testing
  --timeout <secs>    → Default timeout per test (default: 120)
  --report <file>     → Write JSON report to file
```
