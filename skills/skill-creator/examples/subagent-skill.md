---
name: find-usage
description: Find all usages of a function, class, or variable across the codebase
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
argument-hint: [symbol-name]
---

# Find Usage

Find all usages of: $ARGUMENTS

## Search Strategy

1. **Direct references**
   - Grep for exact symbol name
   - Check imports

2. **Definition location**
   - Find where symbol is defined
   - Note file and line number

3. **Usage locations**
   - Find all files importing the symbol
   - Find all call sites

4. **Indirect references**
   - Check for aliases
   - Check for re-exports

## Output Format

```
## Definition
file.py:42 - def $ARGUMENTS(...)

## Usages (X found)
1. other_file.py:15 - from module import $ARGUMENTS
2. another.py:88 - result = $ARGUMENTS(arg)
3. test_file.py:23 - assert $ARGUMENTS() == expected
```
