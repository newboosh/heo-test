"""File classification component for intelligent categorization.

Classifies files by type and category using rules from catalog.yaml.
Supports:
- Directory patterns
- Filename patterns
- Content regex patterns
- AST patterns (Python only)

Multi-language support: Python, TypeScript, JavaScript, Shell, Dart, SQL, Docker
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yaml

from scripts.intelligence.utils import ast_utils, file_utils


@dataclass
class Classification:
    """File classification result."""

    file_path: str
    """Absolute file path."""

    category: str
    """Primary category (e.g., 'source', 'test', 'config')."""

    confidence: str
    """Confidence level: 'high', 'medium', or 'low'."""

    language: Optional[str] = None
    """Detected language (e.g., 'python', 'typescript')."""

    matched_rule: Optional[str] = None
    """Name of the rule that matched."""

    details: Optional[str] = None
    """Additional details about classification."""


class Classifier:
    """Classify files using configurable rules.

    Rules are loaded from catalog.yaml with sensible defaults if missing.
    """

    # Default rules when none are provided
    DEFAULT_RULES = {
        "directory_patterns": {
            "test": [
                "test*",
                "*test*",
                "**test**",
                "**tests**"
            ],
            "docs": ["docs", "doc", "documentation"],
            "config": [".config", "etc"],
            "build": ["build", "dist", "out"]
        },
        "filename_patterns": {
            "test": [
                "test_*.py",
                "*_test.py",
                "*.test.ts",
                "*.spec.ts",
                "test.js",
                "*_test.go"
            ],
            "config": [
                "*.yaml",
                "*.yml",
                "*.json",
                "*.toml",
                "*.conf",
                ".env*"
            ],
            "build": [
                "Makefile",
                "setup.py",
                "package.json",
                "Cargo.toml",
                "go.mod"
            ],
            "docs": [
                "*.md",
                "*.rst",
                "*.txt",
                "README*",
                "CHANGELOG*"
            ]
        },
        "content_patterns": {
            "test": [r"(import|from)\s+(unittest|pytest|jasmine)"],
            "docker": [r"FROM\s+", r"RUN\s+apt-get"],
            "shell": [r"^#!/bin/bash", r"^#!/bin/sh"]
        },
        "ast_patterns": {
            "test": {
                "python": [
                    "unittest",
                    "pytest",
                    "test_"
                ]
            }
        }
    }

    def __init__(self, config_path: str = "catalog.yaml"):
        """Initialize classifier with configuration.

        Args:
            config_path: Path to catalog.yaml file.
        """
        self.config_path = config_path
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """Load rules from config file or use defaults.

        Returns:
            Classification rules dictionary.
        """
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
                rules = config.get("classification_rules", {})
        else:
            rules = {}

        # Merge with defaults (rules take precedence)
        return {
            **self.DEFAULT_RULES,
            **rules
        }

    def classify_file(self, file_path: str) -> Classification:
        """Classify a single file.

        Args:
            file_path: Path to file to classify.

        Returns:
            Classification result with category and confidence.
        """
        file_path = str(Path(file_path).resolve())

        # Try each classification strategy
        # 1. Directory pattern matching
        result = self._check_directory_patterns(file_path)
        if result:
            return result

        # 2. Filename pattern matching
        result = self._check_filename_patterns(file_path)
        if result:
            return result

        # 3. Content pattern matching
        result = self._check_content_patterns(file_path)
        if result:
            return result

        # 4. AST pattern matching (Python only)
        if file_path.endswith('.py'):
            result = self._check_ast_patterns(file_path)
            if result:
                return result

        # Default: uncategorized
        return Classification(
            file_path=file_path,
            category="uncategorized",
            confidence="low",
            language=self._detect_language(file_path)
        )

    def classify_all(self, root_dir: str) -> List[Classification]:
        """Classify all files in directory tree.

        Args:
            root_dir: Root directory to scan.

        Returns:
            List of Classification results.
        """
        results = []
        for file_path in file_utils.iterate_files(root_dir):
            results.append(self.classify_file(file_path))
        return results

    def _check_directory_patterns(self, file_path: str) -> Optional[Classification]:
        """Check if file path matches directory patterns.

        Args:
            file_path: File path to check.

        Returns:
            Classification if matches, None otherwise.
        """
        relative = str(Path(file_path).relative_to('/'))
        dir_patterns = self.rules.get("directory_patterns", {})

        for category, patterns in dir_patterns.items():
            for pattern in patterns:
                # Check if pattern matches any directory component
                if self._path_matches_pattern(relative, pattern):
                    return Classification(
                        file_path=file_path,
                        category=category,
                        confidence="high",
                        language=self._detect_language(file_path),
                        matched_rule=f"directory:{pattern}"
                    )

        return None

    def _check_filename_patterns(self, file_path: str) -> Optional[Classification]:
        """Check if filename matches patterns.

        Args:
            file_path: File path to check.

        Returns:
            Classification if matches, None otherwise.
        """
        filename = Path(file_path).name
        filename_patterns = self.rules.get("filename_patterns", {})

        for category, patterns in filename_patterns.items():
            for pattern in patterns:
                if self._glob_matches(filename, pattern):
                    return Classification(
                        file_path=file_path,
                        category=category,
                        confidence="high",
                        language=self._detect_language(file_path),
                        matched_rule=f"filename:{pattern}"
                    )

        return None

    def _check_content_patterns(self, file_path: str) -> Optional[Classification]:
        """Check if file content matches regex patterns.

        Args:
            file_path: File path to check.

        Returns:
            Classification if matches, None otherwise.
        """
        content = file_utils.read_file(file_path)
        if not content:
            return None

        content_patterns = self.rules.get("content_patterns", {})

        for category, patterns in content_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    return Classification(
                        file_path=file_path,
                        category=category,
                        confidence="medium",
                        language=self._detect_language(file_path),
                        matched_rule=f"content:{pattern}"
                    )

        return None

    def _check_ast_patterns(self, file_path: str) -> Optional[Classification]:
        """Check AST patterns (Python only).

        Args:
            file_path: Python file path.

        Returns:
            Classification if matches, None otherwise.
        """
        tree = ast_utils.parse_python_file(file_path)
        if not tree:
            return None

        ast_patterns = self.rules.get("ast_patterns", {})

        for category, lang_patterns in ast_patterns.items():
            python_patterns = lang_patterns.get("python", [])
            for pattern in python_patterns:
                # Check for imports matching pattern
                imports = ast_utils.get_imports(tree)
                all_imports = imports.get("import", []) + imports.get("from", [])

                if any(pattern.lower() in imp.lower() for imp in all_imports):
                    return Classification(
                        file_path=file_path,
                        category=category,
                        confidence="medium",
                        language="python",
                        matched_rule=f"ast:{pattern}"
                    )

        return None

    @staticmethod
    def _detect_language(file_path: str) -> Optional[str]:
        """Detect programming language from file extension.

        Args:
            file_path: File path.

        Returns:
            Language name or None if unknown.
        """
        ext_to_lang = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.sh': 'shell',
            '.bash': 'shell',
            '.dart': 'dart',
            '.sql': 'sql',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
        }

        suffix = Path(file_path).suffix.lower()
        return ext_to_lang.get(suffix)

    @staticmethod
    def _path_matches_pattern(path: str, pattern: str) -> bool:
        """Check if path matches directory pattern.

        Args:
            path: File path.
            pattern: Pattern to match (e.g., "test*", "*test*").

        Returns:
            True if matches.
        """
        parts = path.split('/')
        for part in parts:
            if Classifier._glob_matches(part, pattern):
                return True
        return False

    @staticmethod
    def _glob_matches(text: str, pattern: str) -> bool:
        """Check if text matches glob pattern.

        Args:
            text: Text to match.
            pattern: Glob pattern (e.g., "*.py", "test_*").

        Returns:
            True if matches.
        """
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
