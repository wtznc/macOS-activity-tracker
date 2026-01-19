"""Configuration management for Activity Tracker."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG = {
    "idle_threshold": 300,  # 5 minutes
    "fast_mode": False,
    "verbose_logging": True,
    "include_window_titles": True,
    "sync_endpoint": "",
    "sync_auth_token": "",  # nosec B105 - Bearer token for sync authentication
    "sync_interval": 3600,  # 1 hour
    "data_retention_days": 30,
    "auto_sync": False,
    "save_interval": 60,  # 1 minute
    "app_blacklist": [],
    "window_title_blacklist": [],
    "privacy_mode": False,
}


class Config:
    """Configuration manager for Activity Tracker."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Custom configuration directory path
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use standard macOS application support directory
            self.config_dir = (
                Path.home()
                / "Library"
                / "Application Support"
                / "ActivityTracker"
                / "config"
            )

        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file: {e}")
                print("Using default configuration.")

        return DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value

    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update multiple configuration values.

        Args:
            config_dict: Dictionary of configuration updates
        """
        self._config.update(config_dict)

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = DEFAULT_CONFIG.copy()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    # Convenience properties for common settings
    @property
    def idle_threshold(self) -> int:
        """Get idle threshold in seconds."""
        return self.get("idle_threshold", 300)

    @idle_threshold.setter
    def idle_threshold(self, value: int) -> None:
        """Set idle threshold in seconds."""
        self.set("idle_threshold", value)

    @property
    def fast_mode(self) -> bool:
        """Get fast mode setting."""
        return self.get("fast_mode", False)

    @fast_mode.setter
    def fast_mode(self, value: bool) -> None:
        """Set fast mode setting."""
        self.set("fast_mode", value)

    @property
    def verbose_logging(self) -> bool:
        """Get verbose logging setting."""
        return self.get("verbose_logging", True)

    @verbose_logging.setter
    def verbose_logging(self, value: bool) -> None:
        """Set verbose logging setting."""
        self.set("verbose_logging", value)

    @property
    def sync_endpoint(self) -> str:
        """Get sync endpoint URL."""
        return self.get("sync_endpoint", "")

    @sync_endpoint.setter
    def sync_endpoint(self, value: str) -> None:
        """Set sync endpoint URL."""
        self.set("sync_endpoint", value)

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        data_dir = self.get("data_dir")
        if data_dir:
            return Path(data_dir)
        return (
            Path.home() / "Library" / "Application Support" / "ActivityTracker" / "data"
        )


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables.

    Returns:
        Configuration dictionary from environment
    """
    env_config: Dict[str, Any] = {}

    # Map environment variables to config keys
    env_mappings = {
        "ACTIVITY_TRACKER_DATA_DIR": "data_dir",
        "ACTIVITY_TRACKER_ENDPOINT": "sync_endpoint",
        "ACTIVITY_TRACKER_AUTH_TOKEN": "sync_auth_token",  # nosec B105
        "ACTIVITY_TRACKER_IDLE_THRESHOLD": "idle_threshold",
        "ACTIVITY_TRACKER_FAST_MODE": "fast_mode",
        "ACTIVITY_TRACKER_VERBOSE": "verbose_logging",
        "ACTIVITY_TRACKER_INTERVAL": "save_interval",
        "ACTIVITY_TRACKER_SYNC_INTERVAL": "sync_interval",
    }

    for env_var, config_key in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # Type conversion based on default values
            if config_key in [
                "idle_threshold",
                "save_interval",
                "sync_interval",
                "data_retention_days",
            ]:
                try:
                    env_config[config_key] = int(value)
                except ValueError:
                    print(f"Warning: Invalid integer value for {env_var}: {value}")
            elif config_key in [
                "fast_mode",
                "verbose_logging",
                "auto_sync",
                "privacy_mode",
            ]:
                env_config[config_key] = value.lower() in ("true", "1", "yes", "on")
            else:
                env_config[config_key] = value

    return env_config


def get_default_data_dir() -> Path:
    """Get the default data directory for the current user.

    Returns:
        Path to default data directory
    """
    return Path.home() / "Library" / "Application Support" / "ActivityTracker" / "data"


def ensure_data_dir(data_dir: Path) -> None:
    """Ensure data directory exists.

    Args:
        data_dir: Path to data directory
    """
    data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
        # Apply environment variable overrides
        env_config = load_config_from_env()
        if env_config:
            _global_config.update(env_config)
    return _global_config


def reload_config() -> Config:
    """Reload configuration from file.

    Returns:
        Reloaded Config instance
    """
    global _global_config
    _global_config = None
    return get_config()
