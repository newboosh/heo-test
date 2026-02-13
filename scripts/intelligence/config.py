"""Configuration management for unified intelligence system.

Loads and manages configuration from catalog.yaml or environment.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any

from scripts.intelligence.utils.json_utils import merge_dicts


class IntelligenceConfig:
    """Load and manage intelligence system configuration."""

    def __init__(self, config_path: str = "catalog.yaml"):
        """Initialize configuration from file or defaults.

        Args:
            config_path: Path to catalog.yaml configuration file.
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with sensible defaults.

        Returns:
            Configuration dictionary with all required keys.
        """
        loaded = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f) or {}
            except (yaml.YAMLError, OSError):
                loaded = {}

        # Deep merge with defaults to preserve nested sections
        return merge_dicts(self._get_defaults(), loaded)

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary.
        """
        return {
            "output_dir": ".claude/intelligence",
            "incremental": True,
            "watch_enabled": False,
            "watch_debounce_ms": 100,
            "components": {
                "classifier": {"enabled": True},
                "dependency_graph": {"enabled": True},
                "symbol_index": {"enabled": True},
                "docstring_parser": {"enabled": True}
            },
            "monitoring": {
                "check_memory": True,
                "check_disk": True,
                "check_cpu": True,
                "memory_warn_pct": 75,
                "memory_critical_pct": 85,
                "disk_warn_gb": 5,
                "disk_critical_gb": 1
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation like "monitoring.check_memory").
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        """Get configuration value by bracket notation.

        Args:
            key: Configuration key.

        Returns:
            Configuration value.
        """
        return self.config[key]
