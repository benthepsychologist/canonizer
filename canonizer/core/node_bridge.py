"""Bridge to Node.js canonizer-core binary."""

import os
import shutil
from pathlib import Path


def get_canonizer_core_bin() -> str:
    """Resolve path to canonizer-core binary.

    Resolution order:
    1. CANONIZER_CORE_BIN environment variable (explicit override)
    2. Repo-local dev path: packages/canonizer-core/bin/canonizer-core
    3. System PATH

    Returns:
        Path to canonizer-core binary

    Raises:
        RuntimeError: If canonizer-core cannot be found
    """
    # 1. Check environment variable
    env_bin = os.environ.get("CANONIZER_CORE_BIN")
    if env_bin:
        if os.path.exists(env_bin):
            return env_bin
        raise RuntimeError(f"CANONIZER_CORE_BIN path does not exist: {env_bin}")

    # 2. Check for repo-local dev path
    # Walk up from this file to find repo root
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        repo_bin = parent / "packages" / "canonizer-core" / "bin" / "canonizer-core"
        if repo_bin.exists():
            return str(repo_bin)

    # 3. Check PATH
    if shutil.which("canonizer-core"):
        return "canonizer-core"

    raise RuntimeError(
        "canonizer-core not found. Either:\n"
        "  - Run 'npm install && npm run build' in packages/canonizer-core/\n"
        "  - Set CANONIZER_CORE_BIN environment variable\n"
        "  - Install canonizer-core globally"
    )


def get_registry_root() -> str:
    """Get the registry root directory.

    Resolution order:
    1. CANONIZER_REGISTRY_ROOT environment variable
    2. Current working directory

    Returns:
        Path to registry root
    """
    return os.environ.get("CANONIZER_REGISTRY_ROOT", str(Path.cwd()))
