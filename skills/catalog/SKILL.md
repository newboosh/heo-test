---
name: catalog
description: File classification and dependency tracking for AI agents. Build and query the codebase catalog.
argument-hint: <command> [options]
---

# Catalog Commands

File classification and dependency tracking system - "GPS for codebases" that helps AI agents navigate without reading thousands of files.

## Available Commands

### /catalog init

Initialize catalog in current project.

```bash
python -m scripts.catalog.cli init
```

**What it does:**
1. Creates `.claude/catalog/` directory structure
2. Creates `.claude/cache/` for build state
3. Copies config template or creates minimal default
4. Updates `.gitignore` to exclude cache

---

### /catalog build

Build complete catalog (classification + dependencies).

```bash
python -m scripts.catalog.cli build
python -m scripts.catalog.cli build --incremental
```

**Options:**
- `--incremental` - Only rebuild if files changed (uses SHA-256 hashes)
- `--config PATH` - Use custom config file

**What it does:**
1. Scans configured `index_dirs` for all files
2. Classifies each file using pattern rules
3. Analyzes Python imports to build dependency graph
4. Saves indexes to `.claude/catalog/indexes/`

**Output files:**
- `file_classification.json` - Categories, matched rules, confidence
- `module_dependencies.json` - Import graph (imports, imported_by, external)

---

### /catalog classify

Run classification only (no dependency analysis).

```bash
python -m scripts.catalog.cli classify
```

Useful for quick classification without the overhead of dependency analysis.

---

### /catalog deps

Run dependency analysis only.

```bash
python -m scripts.catalog.cli deps
```

Analyzes Python imports without reclassifying files.

---

### /catalog query

Query the catalog indexes.

```bash
python -m scripts.catalog.cli query --file src/auth.py
python -m scripts.catalog.cli query --category test
python -m scripts.catalog.cli query --depends-on src/core/db.py
python -m scripts.catalog.cli query --imports src/api/routes.py
python -m scripts.catalog.cli query --summary
```

**Options:**
- `--file PATH` - Get classification for a specific file
- `--category NAME` - List all files in a category
- `--depends-on PATH` - Find files that import this file (reverse deps)
- `--imports PATH` - Show what a file imports (forward deps)
- `--summary` - Show category counts and statistics

---

### /catalog status

Show catalog health and statistics.

```bash
python -m scripts.catalog.cli status
```

**Shows:**
- Classification index: file count, categories, last generated
- Dependencies index: module count, last generated
- Overall health status

---

## Automatic Rebuilds

The catalog rebuilds automatically via hooks:

1. **Session start** - Fresh indexes when you start Claude Code
2. **Post-commit** - Updates after each git commit (runs in background)

No manual rebuilding needed during normal workflow.

---

## File Locations

| File | Location | Git-tracked? |
|------|----------|--------------|
| Config | `.claude/catalog/config.yaml` | Yes |
| Classification index | `.claude/catalog/indexes/file_classification.json` | Optional (generated) |
| Dependencies index | `.claude/catalog/indexes/module_dependencies.json` | Optional (generated) |
| Build state cache | `.claude/cache/catalog-state.json` | No |

**Legacy fallback:** Also checks `catalog.yaml` in project root if `.claude/catalog/config.yaml` doesn't exist.

---

## Classification Rule Types

### 1. Directory Pattern (glob)
Match files by path pattern.
```yaml
{type: directory, pattern: "**/tests/**"}
{type: directory, pattern: "src/api/**"}
```

### 2. Filename Pattern (glob)
Match by filename.
```yaml
{type: filename, pattern: "test_*.py"}
{type: filename, pattern: "*.spec.ts"}
```

### 3. Content Pattern (regex)
Match by file content.
```yaml
{type: content, pattern: "React\\.FC|useState", filetypes: [".tsx", ".jsx"]}
{type: content, pattern: "@dataclass", filetypes: [".py"]}
```

### 4. AST Content (Python only)
Match by Python AST analysis.
```yaml
# Class inherits from specific base
{type: ast_content, condition: "class_inherits:BaseModel"}
{type: ast_content, condition: "class_inherits:TestCase"}

# Has specific decorator
{type: ast_content, condition: "decorator:app.route"}
{type: ast_content, condition: "decorator:pytest.fixture"}

# Has if __name__ == "__main__" block
{type: ast_content, condition: "has_main_block"}
```

---

## Example Config

```yaml
version: "1.0"

index_dirs: [src, app, scripts, lib]
skip_dirs: [__pycache__, .git, node_modules, .venv, .pytest_cache, .trees]

output:
  index_dir: .claude/catalog/indexes
  classification_file: file_classification.json
  dependencies_file: module_dependencies.json

classification:
  categories:
    - name: test
      rules:
        - {type: directory, pattern: "**/tests/**"}
        - {type: filename, pattern: "test_*.py"}
        - {type: ast_content, condition: "class_inherits:TestCase"}

    - name: api
      rules:
        - {type: directory, pattern: "**/api/**"}
        - {type: ast_content, condition: "decorator:app.route"}

    - name: model
      rules:
        - {type: ast_content, condition: "class_inherits:BaseModel"}
        - {type: content, pattern: "@dataclass", filetypes: [".py"]}

    - name: config
      rules:
        - {type: filename, pattern: "*.yaml"}
        - {type: filename, pattern: "*.toml"}
        - {type: filename, pattern: "*.json"}

  default_category: "uncategorized"
  priority_order: [test, api, model, config]
```

---

## Exit Codes

| Code | Name | Meaning |
|------|------|---------|
| 0 | SUCCESS | Completed successfully |
| 1 | CONFIG_ERROR | Invalid configuration |
| 2 | FILE_SYSTEM_ERROR | File access issues |
| 3 | PARTIAL_SUCCESS | Completed but some files skipped |

---

## Quick Start

```bash
# 1. Initialize catalog
/catalog init

# 2. Edit config (optional)
# Edit .claude/catalog/config.yaml to add project-specific categories

# 3. Build catalog
/catalog build

# 4. Query for information
/catalog query --category test
/catalog query --depends-on src/core/auth.py
/catalog query --summary
```

---

## Integration Notes

**For AI agents:** Query the catalog before exploring unknown codebases:
```bash
/catalog query --summary           # Understand codebase structure
/catalog query --category api      # Find API endpoints
/catalog query --depends-on X      # Understand impact of changes
```

**Dependencies:**
- Required: `pyyaml`

**Installing git post-commit hook:**
```bash
cp hooks/git/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```
