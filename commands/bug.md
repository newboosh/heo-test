# Bug Investigation

Start a systematic, hypothesis-driven bug investigation.

## Overview

This command invokes the `bug-investigate` skill for non-trivial bugs that resist a quick fix. It enforces problem-definition-first debugging with evidence provenance tracking and a mandatory prevention sweep.

```
/bug <description of the bug or error message>
```

## When to Use

- A fix attempt already failed once
- The bug is intermittent or environment-dependent
- Multiple possible root causes exist
- You need structured investigation context to hand off

**For build/type/lint errors with clear messages, use `/build-fix` instead.**

## Instructions

Delegate to the `bug-investigate` skill:

```
/bug-investigate $ARGUMENTS
```

If no arguments provided, ask the user:
- What is the symptom? (exact error message or unexpected behavior)
- When did it start? (or after which change)
- Can it be reproduced? (exact steps or command)
