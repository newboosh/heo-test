"""Configuration loading and validation for the catalog system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import translate as glob_translate
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigError(Exception):
    """Error in catalog configuration."""

    def __init__(
        self,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        error_type: str = "config_invalid",
    ):
        super().__init__(message)
        self.message = message
        self.file = file
        self.line = line
        self.error_type = error_type

    def to_json(self) -> dict[str, Any]:
        """Serialize error to JSON format for machine parsing."""
        result: dict[str, Any] = {
            "error": self.error_type,
            "message": self.message,
        }
        if self.file:
            result["file"] = self.file
        if self.line:
            result["line"] = self.line
        return result

    def __str__(self) -> str:
        parts = [self.message]
        if self.file:
            parts.append(f"file: {self.file}")
        if self.line:
            parts.append(f"line: {self.line}")
        return " | ".join(parts)


@dataclass
class Rule:
    """A classification rule."""

    type: str  # directory, filename, content, ast_content
    pattern: Optional[str] = None
    condition: Optional[str] = None  # for ast_content
    filetypes: Optional[list[str]] = None  # for content patterns


@dataclass
class Category:
    """A classification category."""

    name: str
    rules: list[Rule] = field(default_factory=list)


# Default paths for catalog system
DEFAULT_CONFIG_PATH = ".claude/catalog/config.yaml"
DEFAULT_INDEX_DIR = ".claude/catalog/indexes"
DEFAULT_STATE_PATH = ".claude/cache/catalog-state.json"
TEMPLATE_CONFIG_PATH = "templates/catalog/catalog.yaml.template"


@dataclass
class OutputConfig:
    """Output configuration."""

    index_dir: str = DEFAULT_INDEX_DIR
    classification_file: str = "file_classification.json"
    dependencies_file: str = "module_dependencies.json"


@dataclass
class ClassificationConfig:
    """Classification configuration."""

    categories: list[Category] = field(default_factory=list)
    default_category: str = "uncategorized"
    priority_order: list[str] = field(default_factory=list)


@dataclass
class CatalogConfig:
    """Complete catalog configuration."""

    version: str = "1.0"
    index_dirs: list[str] = field(default_factory=lambda: ["app", "scripts", "src", "lib"])
    doc_dirs: list[str] = field(default_factory=lambda: ["docs"])
    skip_dirs: list[str] = field(
        default_factory=lambda: ["__pycache__", ".git", "node_modules", ".venv", ".trees"]
    )
    max_file_size: int = 1048576  # 1MB
    follow_symlinks: bool = True
    output: OutputConfig = field(default_factory=OutputConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)


def get_default_config() -> CatalogConfig:
    """Return the default catalog configuration."""
    return CatalogConfig()


def _parse_rule(rule_dict: dict[str, Any], config_file: Optional[str] = None) -> Rule:
    """Parse a rule dictionary into a Rule object."""
    rule_type = rule_dict.get("type")
    if rule_type not in ("directory", "filename", "content", "ast_content"):
        raise ConfigError(
            f"Unknown rule type: {rule_type}",
            file=config_file,
            error_type="config_invalid",
        )

    return Rule(
        type=rule_type,
        pattern=rule_dict.get("pattern"),
        condition=rule_dict.get("condition"),
        filetypes=rule_dict.get("filetypes"),
    )


def _parse_category(cat_dict: dict[str, Any], config_file: Optional[str] = None) -> Category:
    """Parse a category dictionary into a Category object."""
    name = cat_dict.get("name", "unnamed")
    rules = []
    for rule_dict in cat_dict.get("rules", []):
        rules.append(_parse_rule(rule_dict, config_file))
    return Category(name=name, rules=rules)


def _parse_output(output_dict: dict[str, Any]) -> OutputConfig:
    """Parse output configuration."""
    return OutputConfig(
        index_dir=output_dict.get("index_dir", DEFAULT_INDEX_DIR),
        classification_file=output_dict.get("classification_file", "file_classification.json"),
        dependencies_file=output_dict.get("dependencies_file", "module_dependencies.json"),
    )


def _parse_classification(
    class_dict: dict[str, Any], config_file: Optional[str] = None
) -> ClassificationConfig:
    """Parse classification configuration."""
    categories = []
    for cat_dict in class_dict.get("categories", []):
        categories.append(_parse_category(cat_dict, config_file))

    return ClassificationConfig(
        categories=categories,
        default_category=class_dict.get("default_category", "uncategorized"),
        priority_order=class_dict.get("priority_order", []),
    )


def _validate_regex(pattern: str, config_file: Optional[str] = None) -> None:
    """Validate a regex pattern."""
    try:
        re.compile(pattern)
    except re.error as e:
        raise ConfigError(
            f"Invalid regex pattern '{pattern}': {e}",
            file=config_file,
            error_type="config_invalid",
        )


def _validate_glob(pattern: str, config_file: Optional[str] = None) -> None:
    """Validate a glob pattern."""
    try:
        # fnmatch.translate converts glob to regex; if it fails, pattern is invalid
        glob_translate(pattern)
    except Exception as e:
        raise ConfigError(
            f"Invalid glob pattern '{pattern}': {e}",
            file=config_file,
            error_type="config_invalid",
        )
    # Additional check for unclosed brackets
    if pattern.count("[") != pattern.count("]"):
        raise ConfigError(
            f"Invalid glob pattern '{pattern}': unclosed bracket",
            file=config_file,
            error_type="config_invalid",
        )


def _validate_ast_condition(condition: str, config_file: Optional[str] = None) -> None:
    """Validate an AST condition string.

    Valid formats:
    - class_inherits:ClassName
    - decorator:decorator_name
    - has_main_block
    """
    # Exact match for has_main_block
    if condition == "has_main_block":
        return

    # Reject bare tokens without colon
    if condition in ("class_inherits", "decorator"):
        raise ConfigError(
            f"Invalid ast_content condition '{condition}': "
            f"must include colon and argument (e.g., '{condition}:ClassName')",
            file=config_file,
            error_type="config_invalid",
        )

    # Validate class_inherits:NAME format
    if condition.startswith("class_inherits:"):
        if len(condition) <= len("class_inherits:"):
            raise ConfigError(
                f"Invalid ast_content condition '{condition}': class_inherits requires a class name",
                file=config_file,
                error_type="config_invalid",
            )
        return

    # Validate decorator:NAME format
    if condition.startswith("decorator:"):
        if len(condition) <= len("decorator:"):
            raise ConfigError(
                f"Invalid ast_content condition '{condition}': decorator requires a decorator name",
                file=config_file,
                error_type="config_invalid",
            )
        return

    # If we get here, it's an invalid condition
    raise ConfigError(
        f"Invalid ast_content condition '{condition}'. "
        f"Must be one of: class_inherits:<name>, decorator:<name>, has_main_block",
        file=config_file,
        error_type="config_invalid",
    )


def validate_config(config: CatalogConfig, config_file: Optional[str] = None) -> None:
    """Validate configuration values.

    Raises:
        ConfigError: If configuration is invalid.
    """
    for category in config.classification.categories:
        for rule in category.rules:
            if rule.type == "content" and rule.pattern:
                _validate_regex(rule.pattern, config_file)
            elif rule.type in ("directory", "filename") and rule.pattern:
                _validate_glob(rule.pattern, config_file)
            elif rule.type == "ast_content":
                if not rule.condition:
                    raise ConfigError(
                        "ast_content rules require a 'condition' (e.g., 'class_inherits:ClassName')",
                        file=config_file,
                        error_type="config_invalid",
                    )
                _validate_ast_condition(rule.condition, config_file)


def load_config(config_path: Path | str) -> CatalogConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the catalog.yaml file.

    Returns:
        CatalogConfig with loaded values merged with defaults.

    Raises:
        ConfigError: If the file exists but contains invalid configuration.
    """
    config_path = Path(config_path)
    config_file = str(config_path)

    # Start with defaults
    defaults = get_default_config()

    if not config_path.exists():
        return defaults

    try:
        content = config_path.read_text()
        if not content.strip():
            return defaults

        data = yaml.safe_load(content)
        if not data:
            return defaults
        if not isinstance(data, dict):
            raise ConfigError(
                "Top-level catalog config must be a mapping",
                file=config_file,
                error_type="config_invalid",
            )

    except yaml.YAMLError as e:
        raise ConfigError(
            f"Invalid YAML: {e}",
            file=config_file,
            error_type="config_invalid",
        )

    # Build config from data, using defaults for missing values
    config = CatalogConfig(
        version=data.get("version", defaults.version),
        index_dirs=data.get("index_dirs", defaults.index_dirs),
        doc_dirs=data.get("doc_dirs", defaults.doc_dirs),
        skip_dirs=data.get("skip_dirs", defaults.skip_dirs),
        max_file_size=data.get("max_file_size", defaults.max_file_size),
        follow_symlinks=data.get("follow_symlinks", defaults.follow_symlinks),
        output=_parse_output(data.get("output", {})),
        classification=_parse_classification(data.get("classification", {}), config_file),
    )

    # Validate the loaded config
    validate_config(config, config_file)

    return config
