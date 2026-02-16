# Loop Pattern Example

This example shows the `coderabbitloop` agent iterating until PR is clean.

## Structure

```
┌─────────────────────────────────────────┐
│ INITIALIZE                              │
│ - Set MAX_ITERATIONS = 8                │
│ - Identify PR from current branch       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ CHECK EXIT CONDITIONS          ◄────────┼──┐
│ - Clean? → Exit success                 │  │
│ - Max iterations? → Exit with summary   │  │
│ - Stop signal? → Exit immediately       │  │
└─────────────────┬───────────────────────┘  │
                  │ (work needed)             │
                  ▼                           │
┌─────────────────────────────────────────┐  │
│ WORK STEP                               │  │
│ - /coderabbit --no-resolve              │  │
│ - Fixes applied, pushed                 │  │
└─────────────────┬───────────────────────┘  │
                  │                           │
                  ▼                           │
┌─────────────────────────────────────────┐  │
│ WAIT                                    │  │
│ - Sleep 2 minutes                       │  │
│ - Check for CodeRabbit response         │  │
│ - Max 5 attempts (10 min total)         │  │
└─────────────────┬───────────────────────┘  │
                  │                           │
                  └───────────────────────────┘
```

## Implementation

```markdown
## Configuration

- **MAX_ITERATIONS**: 8
- **WAIT_INTERVAL**: 120 seconds
- **MAX_WAIT_ATTEMPTS**: 5

## Loop

### 1. Pre-flight
Check exit signals and rate limits.

### 2. Check Status
` ` `bash
python3 scripts/coderabbit/check_pr_status.py --pr $PR_NUMBER --json
` ` `

Categorize:
- **CLEAN** → Exit to merge phase
- **WORK** → Continue to step 3
- **REVIEWING** → Wait and retry

### 3. Process
` ` `
/coderabbit $PR_NUMBER --no-resolve --iteration $N
` ` `

### 4. Wait
` ` `bash
for attempt in 1 2 3 4 5; do
    sleep 120
    response=$(check_cr_response.py --pr $PR_NUMBER)
    case "$response" in
        "approved") break ;;
        "rejected") break ;;
        "pending")  continue ;;
    esac
done
` ` `

### 5. Loop or Exit
- If approved/clean → merge
- If rejected → back to step 1
- If max iterations → exit with summary
```

## Key Design Decisions

1. **Bounded iterations**: Never run forever (max 8)
2. **Graceful exit signals**: Can be stopped externally
3. **Rate limit awareness**: Pause if hitting API limits
4. **Clear state transitions**: Each iteration has defined outcome
5. **Audit trail**: Log each iteration's actions
