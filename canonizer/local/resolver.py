"""Resolution functions for local .canonizer/ registry.

These functions convert schema and transform references to local file paths,
enabling canonizer to work without requiring a full registry clone or
environment variables.

Reference formats:
- Schema: "iglu:com.google/gmail_email/jsonschema/1-0-0"
- Transform: "email/gmail_to_jmap_lite@1.0.0"
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from canonizer.local.config import (
    CANONIZER_DIR,
    CONFIG_FILENAME,
    CanonizerConfig,
)
from canonizer.config import get_canonizer_home, load_global_config


class ResolutionError(Exception):
    """Error resolving a schema or transform reference."""

    pass


class CanonizerRootNotFoundError(ResolutionError):
    """No .canonizer/ directory found in path hierarchy."""

    pass


class InvalidReferenceError(ResolutionError):
    """Invalid schema or transform reference format."""

    pass


class SchemaNotFoundError(ResolutionError):
    """Schema not found in local registry."""

    pass


class TransformNotFoundError(ResolutionError):
    """Transform not found in local registry."""

    pass


# Regex patterns for reference parsing
IGLU_SCHEMA_PATTERN = re.compile(
    r"^iglu:([a-zA-Z0-9._-]+)/([a-zA-Z0-9_-]+)/jsonschema/(\d+-\d+-\d+)$"
)

TRANSFORM_PATTERN = re.compile(
    r"^([a-zA-Z0-9_/-]+)@(\d+[.\-]\d+[.\-]\d+)$"
)


def find_canonizer_root(start_path: Path | None = None) -> Path:
    """Find the .canonizer/ directory by walking up the directory tree.

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to the .canonizer/ directory

    Raises:
        CanonizerRootNotFoundError: If no .canonizer/ directory is found
    """
    if start_path is None:
        start_path = Path.cwd()

    start_path = start_path.resolve()

    # Walk up the directory tree
    current = start_path
    while current != current.parent:
        canonizer_dir = current / CANONIZER_DIR
        if canonizer_dir.is_dir():
            # Verify it has a config.yaml
            config_path = canonizer_dir / CONFIG_FILENAME
            if config_path.exists():
                return canonizer_dir
        current = current.parent

    # Check root directory too
    canonizer_dir = current / CANONIZER_DIR
    if canonizer_dir.is_dir() and (canonizer_dir / CONFIG_FILENAME).exists():
        return canonizer_dir

    # Only fall back to global config when start_path was not explicitly provided.
    # This keeps unit tests deterministic and ensures that callers can enforce
    # "local project only" semantics by passing a start_path.
    if start_path is None:
        global_home = get_canonizer_home()
        if global_home.is_dir() and (global_home / CONFIG_FILENAME).exists():
            return global_home

    raise CanonizerRootNotFoundError(
        f"No .canonizer/ directory found in {start_path} or any parent directory, "
        f"and no global config found. "
        f"Run 'can init' to create one."
    )


def parse_iglu_ref(schema_ref: str) -> tuple[str, str, str]:
    """Parse an Iglu schema reference into components.

    Args:
        schema_ref: Schema reference in format "iglu:vendor/name/jsonschema/version"

    Returns:
        Tuple of (vendor, name, version)

    Raises:
        InvalidReferenceError: If reference format is invalid
    """
    match = IGLU_SCHEMA_PATTERN.match(schema_ref)
    if not match:
        raise InvalidReferenceError(
            f"Invalid Iglu schema reference: {schema_ref}. "
            f"Expected format: iglu:vendor/name/jsonschema/X-Y-Z"
        )
    return match.group(1), match.group(2), match.group(3)


def parse_transform_ref(transform_ref: str) -> tuple[str, str]:
    """Parse a transform reference into components.

    Args:
        transform_ref: Transform reference in format "category/name@version"

    Returns:
        Tuple of (id, version) where id is "category/name"

    Raises:
        InvalidReferenceError: If reference format is invalid
    """
    match = TRANSFORM_PATTERN.match(transform_ref)
    if not match:
        raise InvalidReferenceError(
            f"Invalid transform reference: {transform_ref}. "
            f"Expected format: category/name@X.Y.Z"
        )
    return match.group(1), match.group(2)


def resolve_schema(
    schema_ref: str,
    canonizer_root: Path | None = None,
    must_exist: bool = True,
) -> Path:
    """Resolve a schema reference to a local file path.

    Args:
        schema_ref: Schema reference (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")
        canonizer_root: Path to .canonizer/ directory (auto-detected if not provided)
        must_exist: If True, raise error if file doesn't exist

    Returns:
        Absolute path to the schema file

    Raises:
        CanonizerRootNotFoundError: If .canonizer/ directory not found
        InvalidReferenceError: If schema reference format is invalid
        SchemaNotFoundError: If schema file doesn't exist (when must_exist=True)

    Example:
        >>> resolve_schema("iglu:com.google/gmail_email/jsonschema/1-0-0")
        Path("/project/.canonizer/registry/schemas/com.google/gmail_email/jsonschema/1-0-0.json")
    """
    registry_root_override = os.environ.get("CANONIZER_REGISTRY_ROOT")
    if canonizer_root is None and registry_root_override:
        registry_path = Path(registry_root_override).expanduser().resolve()
    else:
        if canonizer_root is None:
            canonizer_root = find_canonizer_root()

        # Load config to get registry root
        config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
        registry_path = config.get_registry_path(canonizer_root)

    # Parse reference
    vendor, name, version = parse_iglu_ref(schema_ref)

    # Build path: registry/schemas/vendor/name/jsonschema/version.json
    schema_path = registry_path / "schemas" / vendor / name / "jsonschema" / f"{version}.json"

    if must_exist and not schema_path.exists():
        raise SchemaNotFoundError(
            f"Schema not found: {schema_ref}\n"
            f"Expected at: {schema_path}\n"
            f"Import it with: canonizer import --ref {schema_ref}"
        )

    return schema_path.resolve()


def resolve_transform(
    transform_ref: str,
    canonizer_root: Path | None = None,
    must_exist: bool = True,
) -> Path:
    """Resolve a transform reference to a local meta.yaml path.

    Args:
        transform_ref: Transform reference (e.g., "email/gmail_to_jmap_lite@1.0.0")
        canonizer_root: Path to .canonizer/ directory (auto-detected if not provided)
        must_exist: If True, raise error if file doesn't exist

    Returns:
        Absolute path to the transform spec.meta.yaml file

    Raises:
        CanonizerRootNotFoundError: If .canonizer/ directory not found
        InvalidReferenceError: If transform reference format is invalid
        TransformNotFoundError: If transform files don't exist (when must_exist=True)

    Example:
        >>> resolve_transform("email/gmail_to_jmap_lite@1.0.0")
        Path("/project/.canonizer/registry/transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml")
    """
    registry_root_override = os.environ.get("CANONIZER_REGISTRY_ROOT")
    if canonizer_root is None and registry_root_override:
        registry_path = Path(registry_root_override).expanduser().resolve()
    else:
        if canonizer_root is None:
            canonizer_root = find_canonizer_root()

        # Load config to get registry root
        config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
        registry_path = config.get_registry_path(canonizer_root)

    # Parse reference
    transform_id, version = parse_transform_ref(transform_ref)

    # Build path: registry/transforms/category/name/version/spec.meta.yaml
    transform_path = registry_path / "transforms" / transform_id / version / "spec.meta.yaml"

    if must_exist and not transform_path.exists():
        raise TransformNotFoundError(
            f"Transform not found: {transform_ref}\n"
            f"Expected at: {transform_path}\n"
            f"Import it with: canonizer import --ref {transform_ref}"
        )

    return transform_path.resolve()


def resolve_jsonata(
    transform_ref: str,
    canonizer_root: Path | None = None,
    must_exist: bool = True,
) -> Path:
    """Resolve a transform reference to its JSONata file path.

    Args:
        transform_ref: Transform reference (e.g., "email/gmail_to_jmap_lite@1.0.0")
        canonizer_root: Path to .canonizer/ directory (auto-detected if not provided)
        must_exist: If True, raise error if file doesn't exist

    Returns:
        Absolute path to the transform spec.jsonata file

    Raises:
        CanonizerRootNotFoundError: If .canonizer/ directory not found
        InvalidReferenceError: If transform reference format is invalid
        TransformNotFoundError: If transform files don't exist (when must_exist=True)
    """
    meta_path = resolve_transform(transform_ref, canonizer_root, must_exist=False)
    jsonata_path = meta_path.parent / "spec.jsonata"

    if must_exist and not jsonata_path.exists():
        raise TransformNotFoundError(
            f"Transform JSONata not found: {transform_ref}\n"
            f"Expected at: {jsonata_path}\n"
            f"Import it with: canonizer import --ref {transform_ref}"
        )

    return jsonata_path.resolve()


def schema_ref_to_path(schema_ref: str) -> str:
    """Convert a schema reference to a relative path within the registry.

    Args:
        schema_ref: Schema reference (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")

    Returns:
        Relative path (e.g., "schemas/com.google/gmail_email/jsonschema/1-0-0.json")

    Raises:
        InvalidReferenceError: If schema reference format is invalid
    """
    vendor, name, version = parse_iglu_ref(schema_ref)
    return f"schemas/{vendor}/{name}/jsonschema/{version}.json"


def transform_ref_to_path(transform_ref: str) -> str:
    """Convert a transform reference to a relative path within the registry.

    Args:
        transform_ref: Transform reference (e.g., "email/gmail_to_jmap_lite@1.0.0")

    Returns:
        Relative path (e.g., "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml")

    Raises:
        InvalidReferenceError: If transform reference format is invalid
    """
    transform_id, version = parse_transform_ref(transform_ref)
    return f"transforms/{transform_id}/{version}/spec.meta.yaml"
