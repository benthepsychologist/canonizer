import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class CanonizerGlobalConfig:
    """Global configuration for Canonizer."""
    default_registry_path: Optional[str] = None

def get_canonizer_home() -> Path:
    home = os.environ.get("CANONIZER_HOME", "~/.config/canonizer")
    return Path(home).expanduser()

def get_global_config_path() -> Path:
    return get_canonizer_home() / "config.yaml"

def load_global_config() -> CanonizerGlobalConfig:
    path = get_global_config_path()
    if not path.exists():
        # Return empty config if no file exists
        return CanonizerGlobalConfig()
    
    try:
        data = yaml.safe_load(path.read_text()) or {}
        return CanonizerGlobalConfig(**data)
    except Exception:
        # If file is corrupt or invalid, return valid empty default or minimal
        # For now, let's just return empty to avoid crashing tool on bad config
        # unless debug is needed.
        return CanonizerGlobalConfig()
