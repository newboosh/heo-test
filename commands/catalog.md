---
description: Build and query the file classification catalog. Helps AI agents navigate the codebase efficiently.
---

# Catalog Command

The catalog system classifies files and tracks dependencies to serve as "GPS for codebases" - AI agents query it instead of reading thousands of files.

## Usage

```bash
/catalog [subcommand] [options]
```

## Subcommands

### `/catalog init`
Initialize catalog in current project. Creates `.claude/catalog/` directory structure and copies default config.

### `/catalog build`
Build complete catalog (classification + dependencies).
- Creates `file_classification.json` with categories and confidence levels
- Creates `module_dependencies.json` with import graph

Options:
- `--incremental` - Only process files changed since last build

### `/catalog query`
Query the catalog indexes.

Options:
- `--category NAME` - List all files in a category (e.g., `--category test`)
- `--file PATH` - Get classification for a specific file
- `--depends-on PATH` - Find all files that import a given file
- `--summary` - Show category counts and statistics

### `/catalog status`
Show catalog health: last build time, file counts, staleness.

## Quick Start

1. **Initialize catalog in your project:**
   ```bash
   /catalog init
   ```

2. **Customize config (optional):**
   Edit `.claude/catalog/config.yaml` to add project-specific categories and patterns.

3. **Build the catalog:**
   ```bash
   /catalog build
   ```

4. **Query for information:**
   ```bash
   /catalog query --category service
   /catalog query --depends-on src/core/auth.py
   ```

## File Locations

| File                 | Location                                            | Git-tracked? |
| -------------------- | --------------------------------------------------- | ------------ |
| Config               | `.claude/catalog/config.yaml`                       | Yes          |
| Classification index | `.claude/catalog/indexes/file_classification.json`  | Yes          |
| Dependencies index   | `.claude/catalog/indexes/module_dependencies.json`  | Yes          |
| Build state cache    | `.claude/cache/catalog-state.json`                  | No           |

## Classification Rule Types

1. **directory** - Match by path pattern (glob)
   ```yaml
   {type: directory, pattern: "**/services/**"}
   ```

2. **filename** - Match by filename pattern
   ```yaml
   {type: filename, pattern: "test_*.py"}
   ```

3. **content** - Match by file content (regex)
   ```yaml
   {type: content, pattern: "React\\.FC|useState", filetypes: [".tsx"]}
   ```

4. **ast_content** - Match by Python AST analysis
   ```yaml
   {type: ast_content, condition: "class_inherits:BaseModel"}
   {type: ast_content, condition: "decorator:app.route"}
   {type: ast_content, condition: "has_main_block"}
   ```

## Example Config

```yaml
classification:
  categories:
    - name: api
      rules:
        - {type: directory, pattern: "src/api/**"}
        - {type: ast_content, condition: "decorator:app.route"}

    - name: model
      rules:
        - {type: ast_content, condition: "class_inherits:BaseModel"}

  priority_order: [test, api, model]
```
