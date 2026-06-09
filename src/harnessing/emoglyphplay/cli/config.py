"""EmoGlyphPlay CLI Configuration — Configuration management for the CLI.

Handles loading, saving, and validating EmoGlyphPlay configuration
from files and environment variables.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "default_tier": "free",
    "max_workspaces": 5,
    "compression_level": "balanced",
    "default_model": "cloud-medium",
    "daily_budget": 10.0,
    "monthly_budget": 200.0,
    "api_host": "0.0.0.0",
    "api_port": 8000,
    "connectors": {},
}


class CLIConfig:
    """CLI Configuration manager.

    Loads and manages configuration from a JSON file, with
    environment variable overrides and sensible defaults.

    Args:
        config_path: Path to the configuration file. If None, uses
            the default path (~/.emoglyphplay/config.json).
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_dir = Path.home() / ".emoglyphplay"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_path = config_dir / "config.json"
        else:
            self._config_path = Path(config_path)
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        """Load configuration from file if it exists."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._config.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass  # Use defaults on error

    def save(self) -> None:
        """Save current configuration to file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Checks environment variables first (EMOGLYPHPLAY_<KEY>),
        then the config file, then the default.

        Args:
            key: Configuration key.
            default: Default value if not found.

        Returns:
            The configuration value.
        """
        env_key = f"EMOGLYPHPLAY_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        self._config[key] = value

    def as_dict(self) -> dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return dict(self._config)

    @property
    def config_path(self) -> Path:
        """Return the configuration file path."""
        return self._config_path
