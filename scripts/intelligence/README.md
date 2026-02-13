# Unified Code Intelligence System

A comprehensive Python code analysis system that combines file classification, dependency tracking, symbol extraction, and docstring parsing into a single unified framework.

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```bash
# Full build
python scripts/intelligence/cli.py build

# Classification only
python scripts/intelligence/cli.py classify

# Dependency analysis only
python scripts/intelligence/cli.py deps

# System status
python scripts/intelligence/cli.py status

# Query results
python scripts/intelligence/cli.py query --summary
```

## Features

### 📂 File Classification
Categorize files by type, pattern, and content:
- **Directory patterns**: Match files in specific directories (test*, docs)
- **Filename patterns**: Match by filename glob (test_*.py, *.yaml)
- **Content patterns**: Regex matching for file contents (import statements, shebangs)
- **AST patterns**: Python-only semantic analysis (import detection)

**Multi-language Support**:
- Python, TypeScript, JavaScript
- Shell, Dart, SQL, Docker

### 🔗 Dependency Tracking
Extract and visualize import relationships:
- Forward dependencies: "What does this file import?"
- Reverse dependencies: "What files import this?"
- Circular dependency detection
- Internal vs external classification

### 🔍 Symbol Indexing
Extract code structure with AST analysis:
- Functions and methods
- Classes and their methods
- Docstrings and type hints
- Line number tracking
- Scope information

### 📝 Docstring Parsing
Parse Google-style docstrings:
- Summary extraction
- Argument and return value parsing
- Exception documentation
- Example code blocks
- Graceful handling of malformed docs

### 💚 System Monitoring
Track system resource usage:
- Memory usage (warn at 75%, critical at 85%)
- Disk space (warn at 5GB, critical at 1GB)
- CPU usage (informational)
- Real-time health reports

### 📈 Context Window Impact
Estimate LLM context usage:
- Support for Haiku (100k), Sonnet (200k), Opus (200k)
- Token estimation for generated indices
- Model recommendations
- Safe usage warnings

## Configuration

Create `catalog.yaml` in your project root:

```yaml
output_dir: .claude/intelligence
incremental: true

classification_rules:
  directory_patterns:
    test: [test*, *test*, **/test**]
    docs: [docs, doc, documentation]
    config: [.config, etc]
    build: [build, dist, out]

  filename_patterns:
    test: [test_*.py, *_test.py, *.test.ts, *.spec.ts]
    config: [*.yaml, *.yml, *.json, *.toml, .env*]
    build: [Makefile, setup.py, package.json, Cargo.toml]
    docs: [*.md, *.rst, README*, CHANGELOG*]

  content_patterns:
    test: '(import|from)\s+(unittest|pytest|jasmine)'
    docker: 'FROM\s+'
    shell: '^#!/bin/(bash|sh)'

monitoring:
  check_memory: true
  check_disk: true
  memory_warn_pct: 75
  memory_critical_pct: 85
  disk_warn_gb: 5
  disk_critical_gb: 1
```

## Output Format

### index.json Structure
```json
{
  "_schema_version": "1.0.0",
  "files": [
    {
      "file_path": "src/utils.py",
      "category": "source",
      "confidence": "high",
      "language": "python"
    }
  ],
  "symbols": [
    {
      "name": "helper_function",
      "file": "src/utils.py",
      "line": 10,
      "type": "function",
      "docstring": "Helper function description",
      "language": "python"
    }
  ],
  "dependencies": {
    "forward": {
      "src/utils.py": ["src/models.py"]
    },
    "reverse": {
      "src/models.py": ["src/utils.py"]
    }
  },
  "metadata": {
    "total_files": 10,
    "total_symbols": 25,
    "generated_at": "2026-02-03T12:00:00"
  }
}
```

## Commands

### build
Execute full pipeline: classify → dependencies → symbols

```bash
python scripts/intelligence/cli.py build [--config PATH] [--incremental] [--force]
```

**Options**:
- `--config`: Path to catalog.yaml (default: catalog.yaml)
- `--incremental`: Use cached results for unchanged files
- `--force`: Force full rebuild, ignore cache

### classify
Run file classification only

```bash
python scripts/intelligence/cli.py classify [--config PATH]
```

### deps
Run dependency analysis only

```bash
python scripts/intelligence/cli.py deps [--config PATH]
```

### query
Query the generated index

```bash
python scripts/intelligence/cli.py query [--file PATH] [--category NAME] [--summary]
```

**Options**:
- `--file`: Get information about specific file
- `--category`: Find all files in category
- `--summary`: Show statistics only

### status
Check system health

```bash
python scripts/intelligence/cli.py status
```

**Output**:
```
📊 System Health:
  Memory: 42.1% (3.6GB available)
  Disk: 47.3GB free (52% used)
  CPU: 15.2%
```

## Examples

### Classify Python project
```bash
$ python scripts/intelligence/cli.py classify
Classified 142 files
  - source: 45 files
  - test: 28 files
  - config: 8 files
  - docs: 12 files
  - uncategorized: 49 files
```

### Analyze dependencies
```bash
$ python scripts/intelligence/cli.py deps
Analyzed dependencies: 45 files
  - forward graph: 67 edges
  - reverse graph: 67 edges
  - circular dependencies: 0
```

### Check system resources
```bash
$ python scripts/intelligence/cli.py status
📊 System Health:
  Memory: 62.5% (1.3GB available)
  Disk: 127GB free (42% used)
  CPU: 8.3%
```

## Testing

### Run all tests
```bash
python3 -m pytest scripts/intelligence/tests/ -v
```

### Run specific test category
```bash
python3 -m pytest scripts/intelligence/tests/test_classifier.py -v
python3 -m pytest scripts/intelligence/tests/test_integration.py -v
```

### Check coverage
```bash
python3 -m pytest scripts/intelligence/tests/ --cov=scripts.intelligence
```

**Test Statistics**:
- 122 total tests
- 106 unit tests
- 16 integration tests
- >80% coverage per component

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation including:
- Component descriptions
- Data flow diagrams
- DAG orchestration
- Caching strategy
- System monitoring

## Exit Codes

- `0`: Success
- `1`: Configuration error
- `2`: File I/O error
- `3`: Partial success (some components failed)

## Performance

- **Classification**: ~1000 files/second
- **Symbol extraction**: ~100 files/second (with AST parsing)
- **Dependency analysis**: ~500 files/second
- **Incremental builds**: Skip unchanged components (5-10x faster)

## Limitations & Future Work

### Current Limitations
- Python-only dependency analysis (v1.0)
- No semantic similarity indexing yet
- No parallel processing
- Single-threaded execution

### Planned Features (Phase 2+)
- Multi-language dependency tracking (Go, Java, Rust)
- Semantic similarity indexing
- Complexity metrics
- Importance scoring
- Test behavior mapping
- Watch mode with file system events
- Query expansion (symbol search, cross-references)
- Configuration UI

## Troubleshooting

### "Module not found" errors
Ensure you're running from the project root and Python path includes the current directory:
```bash
PYTHONPATH=. python scripts/intelligence/cli.py build
```

### Out of memory on large codebases
Use `--incremental` flag to skip unchanged files:
```bash
python scripts/intelligence/cli.py build --incremental
```

### Cache issues
Clear the cache and force rebuild:
```bash
rm .claude/intelligence/.cache.db
python scripts/intelligence/cli.py build --force
```

## Development

### Project Structure
```
scripts/intelligence/
├── __init__.py
├── cli.py                 # CLI entry point
├── config.py              # Configuration management
├── build.py               # DAG orchestrator
├── cache.py               # Incremental build cache
├── schema.py              # JSON schema versioning
│
├── components/
│   ├── classifier.py      # File classification
│   ├── dependency_graph.py
│   ├── symbol_index.py
│   └── docstring_parser.py
│
├── monitoring/
│   ├── system_monitor.py
│   └── context_estimator.py
│
├── utils/
│   ├── ast_utils.py
│   ├── file_utils.py
│   ├── hash_utils.py
│   └── json_utils.py
│
└── tests/
    ├── test_cache.py
    ├── test_build.py
    ├── test_classifier.py
    ├── test_monitoring.py
    ├── test_utils.py
    └── test_integration.py
```

### Adding New Components

1. Create component module in `components/`
2. Implement class with clear interface
3. Add to BuildGraph dependency chain in `cli.py`
4. Create comprehensive tests in `tests/test_*.py`
5. Update this README with new features

### Contributing

- Follow Google-style docstrings
- Maintain >80% test coverage
- Run `pytest` before committing
- Use descriptive commit messages

## License

Part of the Claude Code Plugin System

## References

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/planning/IMPLEMENTATION_PLAN.md)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
