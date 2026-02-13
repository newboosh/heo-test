"""Tests for catalog configuration loading and validation."""

import pytest
from pathlib import Path
import tempfile
import yaml

from scripts.catalog.config import (
    CatalogConfig,
    load_config,
    validate_config,
    get_default_config,
    ConfigError,
)


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_get_default_config_returns_valid_config(self):
        """Default config should be valid and usable."""
        config = get_default_config()
        assert isinstance(config, CatalogConfig)
        assert config.version == "1.0"

    def test_default_config_has_required_fields(self):
        """Default config should have all required fields."""
        config = get_default_config()
        assert config.index_dirs is not None
        assert config.skip_dirs is not None
        assert config.output is not None
        assert config.classification is not None

    def test_default_skip_dirs_includes_common_dirs(self):
        """Default skip_dirs should include common directories to exclude."""
        config = get_default_config()
        assert "__pycache__" in config.skip_dirs
        assert ".git" in config.skip_dirs
        assert "node_modules" in config.skip_dirs
        assert ".trees" in config.skip_dirs

    def test_default_max_file_size(self):
        """Default max_file_size should be 1MB."""
        config = get_default_config()
        assert config.max_file_size == 1048576


class TestLoadConfig:
    """Tests for loading configuration from file."""

    def test_load_config_missing_file_returns_defaults(self, tmp_path):
        """Missing config file should return defaults without error."""
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, CatalogConfig)
        assert config.version == "1.0"

    def test_load_config_valid_yaml(self, tmp_path):
        """Valid YAML should load successfully."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["src", "lib"],
            "skip_dirs": [".git"],
        }))
        config = load_config(config_file)
        assert config.index_dirs == ["src", "lib"]

    def test_load_config_merges_with_defaults(self, tmp_path):
        """Partial config should merge with defaults."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["custom"],
        }))
        config = load_config(config_file)
        assert config.index_dirs == ["custom"]
        # Should still have default skip_dirs
        assert "__pycache__" in config.skip_dirs

    def test_load_config_empty_file_returns_defaults(self, tmp_path):
        """Empty config file should return defaults."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text("")
        config = load_config(config_file)
        assert isinstance(config, CatalogConfig)

    def test_load_config_non_mapping_raises_error(self, tmp_path):
        """Non-mapping YAML (list, string) should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        # YAML list instead of mapping
        config_file.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "must be a mapping" in str(exc_info.value)


class TestValidateConfig:
    """Tests for configuration validation."""

    def test_validate_config_valid(self):
        """Valid config should pass validation."""
        config = get_default_config()
        # Should not raise
        validate_config(config)

    def test_validate_config_invalid_regex_raises(self, tmp_path):
        """Invalid regex in rule should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{
                        "type": "content",
                        "pattern": "[invalid(regex",
                    }]
                }]
            }
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "invalid" in str(exc_info.value).lower() or "regex" in str(exc_info.value).lower()

    def test_validate_config_invalid_glob_raises(self, tmp_path):
        """Invalid glob pattern should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{
                        "type": "directory",
                        "pattern": "[invalid",
                    }]
                }]
            }
        }))
        with pytest.raises(ConfigError):
            load_config(config_file)

    def test_validate_config_unknown_rule_type_raises(self, tmp_path):
        """Unknown rule type should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{
                        "type": "unknown_type",
                        "pattern": "something",
                    }]
                }]
            }
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "unknown_type" in str(exc_info.value).lower() or "type" in str(exc_info.value).lower()

    def test_validate_config_valid_ast_condition(self, tmp_path):
        """Valid AST conditions should pass validation."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [
                        {"type": "ast_content", "condition": "class_inherits:BaseModel"},
                        {"type": "ast_content", "condition": "decorator:app.route"},
                        {"type": "ast_content", "condition": "has_main_block"},
                    ]
                }]
            }
        }))
        # Should not raise
        config = load_config(config_file)
        assert len(config.classification.categories[0].rules) == 3

    def test_validate_config_invalid_ast_condition_raises(self, tmp_path):
        """Invalid AST condition should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{
                        "type": "ast_content",
                        "condition": "unknown_condition:something",
                    }]
                }]
            }
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "ast_content" in str(exc_info.value).lower() or "condition" in str(exc_info.value).lower()

    def test_validate_config_ast_condition_missing_argument_raises(self, tmp_path):
        """AST condition with missing argument should raise ConfigError."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{
                        "type": "ast_content",
                        "condition": "class_inherits:",  # Missing class name
                    }]
                }]
            }
        }))
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "class_inherits" in str(exc_info.value)


class TestConfigError:
    """Tests for ConfigError reporting."""

    def test_config_error_has_message(self):
        """ConfigError should have a message."""
        error = ConfigError("test message", file="test.yaml", line=42)
        assert "test message" in str(error)

    def test_config_error_includes_file_info(self):
        """ConfigError should include file info when available."""
        error = ConfigError("bad config", file="catalog.yaml", line=10)
        assert error.file == "catalog.yaml"
        assert error.line == 10

    def test_config_error_to_json(self):
        """ConfigError should serialize to JSON format."""
        error = ConfigError("Invalid regex", file="catalog.yaml", line=42, error_type="config_invalid")
        json_output = error.to_json()
        assert json_output["error"] == "config_invalid"
        assert json_output["message"] == "Invalid regex"
        assert json_output["file"] == "catalog.yaml"
        assert json_output["line"] == 42


class TestCatalogConfig:
    """Tests for CatalogConfig dataclass."""

    def test_config_has_output_paths(self):
        """Config should have output file paths."""
        config = get_default_config()
        assert config.output.index_dir is not None
        assert config.output.classification_file is not None
        assert config.output.dependencies_file is not None

    def test_config_categories_are_ordered(self, tmp_path):
        """Categories should maintain order for priority."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [
                    {"name": "first", "rules": []},
                    {"name": "second", "rules": []},
                    {"name": "third", "rules": []},
                ],
                "priority_order": ["first", "second", "third"],
            }
        }))
        config = load_config(config_file)
        assert config.classification.priority_order == ["first", "second", "third"]

    def test_config_follow_symlinks_default_true(self):
        """follow_symlinks should default to True."""
        config = get_default_config()
        assert config.follow_symlinks is True

    def test_config_follow_symlinks_can_be_disabled(self, tmp_path):
        """follow_symlinks can be set to False."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "follow_symlinks": False,
        }))
        config = load_config(config_file)
        assert config.follow_symlinks is False
