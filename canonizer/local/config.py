"""Configuration models for local .canonizer/ directory.

The config.yaml file defines how canonizer resolves schemas and transforms.
For now, only local mode is supported. Remote mode will be added in a follow-up spec.

Example config.yaml:
```yaml
registry:
  mode: local
  root: .canonizer/registry
```
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class RegistryMode(str, Enum):
    """Registry resolution mode."""

    LOCAL = "local"
    # REMOTE = "remote"  # Deferred to remote-registry spec


class RegistryConfig(BaseModel):
    """Registry configuration section."""

    mode: RegistryMode = Field(
        default=RegistryMode.LOCAL,
        description="Registry resolution mode (local only for now)",
    )
    root: str = Field(
        default="registry",
        description="Path to local registry directory (relative to .canonizer/)",
    )
    # Future fields for remote mode:
    # remote_url: Optional[str] = None
    # channel: str = "stable"

    @field_validator("root")
    @classmethod
    def validate_root_path(cls, v: str) -> str:
        """Ensure root path doesn't escape .canonizer/ directory."""
        if v.startswith("/") or ".." in v:
            raise ValueError("Registry root must be a relative path without '..'")
        return v


class CanonizerConfig(BaseModel):
    """Root configuration model for .canonizer/config.yaml."""

    registry: RegistryConfig = Field(
        default_factory=RegistryConfig,
        description="Registry configuration",
    )

    @classmethod
    def load(cls, config_path: Path) -> CanonizerConfig:
        """Load configuration from a YAML file.

        Args:
            config_path: Path to config.yaml file

        Returns:
            Parsed CanonizerConfig

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        return cls.model_validate(data)

    @classmethod
    def default(cls) -> CanonizerConfig:
        """Create default configuration."""
        return cls()

    def save(self, config_path: Path) -> None:
        """Save configuration to a YAML file.

        Args:
            config_path: Path to write config.yaml
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump(mode="json")

        with open(config_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get_registry_path(self, canonizer_root: Path) -> Path:
        """Get the absolute path to the registry directory.

        Args:
            canonizer_root: Path to .canonizer/ directory

        Returns:
            Absolute path to registry directory
        """
        return (canonizer_root / self.registry.root).resolve()


# Constants for file names
CONFIG_FILENAME = "config.yaml"
LOCK_FILENAME = "lock.json"
CANONIZER_DIR = ".canonizer"
REGISTRY_DIR = "registry"
SCHEMAS_DIR = "schemas"
TRANSFORMS_DIR = "transforms"
