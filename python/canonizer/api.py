"""Thin Python wrapper around Node.js canonizer-core.

This module provides the public API for Canonizer:
- canonicalize(raw_document, transform_id) → canonical_dict
- validate_payload(payload, schema_iglu) → (is_valid, errors)
- run_batch(documents, transform_id) → list[dict]

ALL logic is in Node.js. Python only does:
- JSON serialization/deserialization
- Subprocess management
- Error propagation

NO: Schema loading, validation, YAML parsing, JSONata execution
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class TransformError(Exception):
    """Error during transform execution."""

    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr


def _get_canonizer_core_bin() -> str:
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


def _get_registry_root() -> str:
    """Get the registry root directory.

    Resolution order:
    1. CANONIZER_REGISTRY_ROOT environment variable
    2. Current working directory

    Returns:
        Path to registry root
    """
    return os.environ.get("CANONIZER_REGISTRY_ROOT", str(Path.cwd()))


def canonicalize(
    raw_document: dict[str, Any],
    *,
    transform_id: str,
    validate: bool = True,
    registry_root: str | None = None,
) -> dict[str, Any]:
    """Transform raw JSON document to canonical format.

    This calls the Node.js canonizer-core CLI to perform the actual transform.
    All validation and JSONata execution happens in Node.

    Args:
        raw_document: Source JSON document (dict)
        transform_id: Transform to use (e.g., "email/gmail_to_jmap_lite@1.0.0")
        validate: Validate input/output against schemas (default: True)
        registry_root: Path to registry root (default: from env or cwd)

    Returns:
        Canonical JSON document (dict)

    Raises:
        TransformError: If transformation fails

    Example:
        >>> from canonizer import canonicalize
        >>> canonical = canonicalize(
        ...     raw_gmail_message,
        ...     transform_id="email/gmail_to_jmap_lite@1.0.0"
        ... )
    """
    bin_path = _get_canonizer_core_bin()
    registry = registry_root or _get_registry_root()

    args = [bin_path, "run", "--transform", transform_id, "--registry", registry]
    if not validate:
        args.append("--no-validate")

    result = subprocess.run(
        args,
        input=json.dumps(raw_document),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise TransformError(
            f"Transform failed: {transform_id}",
            stderr=result.stderr.strip(),
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise TransformError(
            f"Invalid JSON output from transform: {e}",
            stderr=result.stdout[:500],
        )


def validate_payload(
    payload: dict[str, Any],
    schema_iglu: str,
    *,
    registry_root: str | None = None,
) -> tuple[bool, list[str]]:
    """Validate a payload against a schema.

    This calls the Node.js canonizer-core CLI to perform validation.
    All JSON Schema validation happens in Node using ajv.

    Args:
        payload: JSON payload to validate
        schema_iglu: Iglu URI (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")
        registry_root: Path to registry root (default: from env or cwd)

    Returns:
        Tuple of (is_valid, errors):
        - is_valid: True if payload passes validation
        - errors: List of error messages (empty if valid)

    Example:
        >>> from canonizer import validate_payload
        >>> is_valid, errors = validate_payload(
        ...     gmail_message,
        ...     "iglu:com.google/gmail_email/jsonschema/1-0-0"
        ... )
    """
    bin_path = _get_canonizer_core_bin()
    registry = registry_root or _get_registry_root()

    result = subprocess.run(
        [bin_path, "validate", "--schema", schema_iglu, "--registry", registry],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, []
    else:
        # stderr contains error messages
        errors = [line for line in result.stderr.strip().split("\n") if line]
        return False, errors


def run_batch(
    documents: list[dict[str, Any]],
    *,
    transform_id: str,
    validate: bool = True,
    registry_root: str | None = None,
) -> list[dict[str, Any]]:
    """Transform multiple documents in batch.

    This is a simple loop over canonicalize(). Future versions may
    optimize with batch processing in the Node layer.

    Args:
        documents: List of source JSON documents
        transform_id: Transform to use (e.g., "email/gmail_to_jmap_lite@1.0.0")
        validate: Validate input/output against schemas (default: True)
        registry_root: Path to registry root (default: from env or cwd)

    Returns:
        List of canonical JSON documents

    Example:
        >>> from canonizer import run_batch
        >>> canonicals = run_batch(
        ...     raw_emails,
        ...     transform_id="email/gmail_to_jmap_lite@1.0.0"
        ... )
    """
    return [
        canonicalize(
            doc,
            transform_id=transform_id,
            validate=validate,
            registry_root=registry_root,
        )
        for doc in documents
    ]
