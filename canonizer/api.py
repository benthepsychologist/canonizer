"""Pure JSON transformation API for Canonizer.

This module provides a clean, programmatic interface for:
1. Validating JSON documents against schemas (source OR canonical)
2. Transforming raw JSON to canonical formats using JSONata transforms

Core principles:
- validate_payload(payload, schema_iglu) → (is_valid, errors)
- canonicalize(payload, transform_id) → canonical_dict
- execute(params) → dict (CallableResult for lorchestra integration)

NO orchestration logic - no events, no BigQuery, no job patterns.
"""

import os
from pathlib import Path
from typing import Any

from canonizer.callable.result import CallableResult
from canonizer.core.runtime import TransformRuntime
from canonizer.core.validator import SchemaValidator, ValidationError, load_schema_from_iglu_uri
from canonizer.local.config import CONFIG_FILENAME, CanonizerConfig
from canonizer.local.resolver import (
    CanonizerRootNotFoundError,
    find_canonizer_root,
    resolve_schema,
    resolve_transform,
)

# ============================================================================
# Registry Root Resolution
# ============================================================================


def _try_find_canonizer_root() -> Path | None:
    """Try to find .canonizer/ directory, return None if not found."""
    try:
        return find_canonizer_root()
    except CanonizerRootNotFoundError:
        return None


def get_registry_root() -> Path:
    """Get the canonizer registry root directory.

    Resolution order:
    1. Local .canonizer/registry/ directory (if .canonizer/ exists)
    2. CANONIZER_REGISTRY_ROOT environment variable
    3. Current working directory (fallback for backward compatibility)

    Returns:
        Path to registry root containing schemas/ and transforms/

    Raises:
        RuntimeError: If CANONIZER_REGISTRY_ROOT is set but path doesn't exist

    Example:
        >>> root = get_registry_root()
        >>> print(root / "schemas")
        /workspace/canonizer/schemas
    """
    # Try local .canonizer/ first
    canonizer_root = _try_find_canonizer_root()
    if canonizer_root:
        config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
        return config.get_registry_path(canonizer_root)

    # Fall back to environment variable
    env_root = os.environ.get("CANONIZER_REGISTRY_ROOT")
    if env_root:
        path = Path(env_root)
        if not path.exists():
            raise RuntimeError(
                f"CANONIZER_REGISTRY_ROOT path does not exist: {path}"
            )
        return path

    # Fallback to CWD for backward compatibility
    return Path.cwd()


# ============================================================================
# Validation API
# ============================================================================


def validate_payload(
    payload: dict[str, Any],
    schema_iglu: str,
    *,
    schemas_dir: str | Path | None = None,
) -> tuple[bool, list[str]]:
    """Validate a payload against a schema (source OR canonical).

    Use this to validate raw payloads before transformation,
    or canonical payloads after.

    Args:
        payload: JSON payload to validate
        schema_iglu: Iglu URI for schema (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")
        schemas_dir: Schema directory. Resolution order:
            1. Explicit schemas_dir parameter (if provided)
            2. Local .canonizer/registry/schemas/ (if .canonizer/ exists)
            3. CANONIZER_REGISTRY_ROOT/schemas (if env var set)
            4. Current directory/schemas (fallback)

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
        >>> if not is_valid:
        ...     print(f"Validation failed: {errors}")
    """
    try:
        # Determine schema path
        if schemas_dir is not None:
            # Explicit schemas_dir provided - use it
            schemas_dir = Path(schemas_dir)
            schema_path = load_schema_from_iglu_uri(schema_iglu, schemas_dir)
        else:
            # Try local .canonizer/ resolution first
            canonizer_root = _try_find_canonizer_root()
            if canonizer_root:
                schema_path = resolve_schema(schema_iglu, canonizer_root)
            else:
                # Fall back to old resolution
                schemas_dir = get_registry_root() / "schemas"
                schema_path = load_schema_from_iglu_uri(schema_iglu, schemas_dir)

        if not schema_path.exists():
            return False, [f"Schema file not found: {schema_path}"]

        # Validate payload against schema
        validator = SchemaValidator(schema_path)
        validator.validate(payload)

        return True, []

    except ValidationError as e:
        return False, e.errors

    except Exception as e:
        return False, [str(e)]


# ============================================================================
# Transform API
# ============================================================================


def canonicalize(
    raw_document: dict,
    *,
    transform_id: str,
    schemas_dir: str | Path | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> dict:
    """
    Transform raw JSON document to canonical format.

    This is the core Canonizer function: raw_json + transform_id → canonical_json

    Args:
        raw_document: Source JSON document (dict)
        transform_id: Transform to use. Accepts:
            - Registry-style ID: "email/gmail_to_jmap_lite@1.0.0"
            - Full path: "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"
        schemas_dir: Schema directory (default: "schemas")
        validate_input: Validate input against source schema (default: True)
        validate_output: Validate output against canonical schema (default: True)

    Returns:
        Canonical JSON document (dict)

    Raises:
        ValidationError: If input or output validation fails
        FileNotFoundError: If transform or schema files not found
        ValueError: If checksum verification fails
        Exception: If transformation execution fails

    Example:
        >>> from canonizer import canonicalize
        >>> canonical = canonicalize(
        ...     raw_gmail_message,
        ...     transform_id="email/gmail_to_jmap_lite@1.0.0"
        ... )
    """
    # Resolve transform_id to .meta.yaml path if needed
    if not transform_id.endswith(".yaml") and not transform_id.endswith(".yml"):
        # Registry-style ID - resolve to local path
        transform_meta_path = _resolve_transform_id(transform_id)
    else:
        # Already a file path
        transform_meta_path = Path(transform_id)

    # Determine schemas_dir
    if schemas_dir is None:
        canonizer_root = _try_find_canonizer_root()
        if canonizer_root:
            config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
            schemas_dir = config.get_registry_path(canonizer_root) / "schemas"
        else:
            schemas_dir = get_registry_root() / "schemas"

    runtime = TransformRuntime(schemas_dir=schemas_dir)

    # Execute transform
    result = runtime.execute(
        transform_meta_path=transform_meta_path,
        input_data=raw_document,
        validate_input=validate_input,
        validate_output=validate_output,
    )

    return result.data


def run_batch(
    documents: list[dict],
    *,
    transform_id: str,
    schemas_dir: str | Path | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> list[dict]:
    """
    Transform multiple documents in batch.

    Args:
        documents: List of source JSON documents
        transform_id: Transform to use (e.g., "email/gmail_to_jmap_lite@1.0.0")
        schemas_dir: Schema directory (default: "schemas")
        validate_input: Validate input against source schema
        validate_output: Validate output against canonical schema

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
            schemas_dir=schemas_dir,
            validate_input=validate_input,
            validate_output=validate_output,
        )
        for doc in documents
    ]


# ============================================================================
# Callable Protocol (lorchestra integration)
# ============================================================================


def execute(params: dict) -> dict:
    """Execute canonization and return CallableResult.

    This is the in-process interface for lorchestra integration.
    lorchestra calls `canonizer.execute(params)` directly (no JSON-RPC wrapper)
    and receives a dict matching the CallableResult schema.

    Args:
        params: Execution parameters with the following keys:
            - source_type (str): Type of source data (e.g., "email", "form")
            - items (list[dict]): List of raw documents to canonize
            - config (dict, optional): Configuration options:
                - transform_id (str, optional): Explicit transform ID to use
                - validate_input (bool, default True): Validate input schema
                - validate_output (bool, default True): Validate output schema
                - schemas_dir (str, optional): Schema directory path

    Returns:
        dict: CallableResult matching the schema:
            {
                "schema_version": "1.0",
                "items": [...],  # Canonized documents
                "stats": {"input": N, "output": M, "skipped": S, "errors": E}
            }

    Raises:
        ValueError: If required parameters are missing or invalid
        FileNotFoundError: If transform or schema files not found
        ValidationError: If input/output validation fails
        Exception: Other errors during transformation

    Note:
        v0 implementation always returns `items` inline.
        `items_ref` (artifact store reference) is reserved for future use.

    Example:
        >>> from canonizer import execute
        >>> result = execute({
        ...     "source_type": "email",
        ...     "items": [raw_gmail_message],
        ...     "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"}
        ... })
        >>> print(result["items"])
        [{'id': '...', 'subject': '...'}]
    """
    # Extract parameters
    source_type = params.get("source_type")
    items = params.get("items", [])
    config = params.get("config", {})

    # Validate required parameters
    if source_type is None:
        raise ValueError("Missing required parameter: 'source_type'")

    if not isinstance(items, list):
        raise ValueError("Parameter 'items' must be a list")

    # Extract config options
    transform_id = config.get("transform_id")
    validate_input = config.get("validate_input", True)
    validate_output = config.get("validate_output", True)
    schemas_dir = config.get("schemas_dir")

    # Determine transform_id from source_type if not explicitly provided
    if transform_id is None:
        transform_id = _get_default_transform_id(source_type)

    # Track statistics
    input_count = len(items)
    output_items: list[dict] = []
    error_count = 0
    skipped_count = 0

    # Process each item
    for item in items:
        try:
            # V2 pipeline: storacle.query returns full BQ rows (idem_key,
            # source_system, payload, etc.). Extract payload for transform,
            # pass through non-payload fields untouched.
            # Detect BQ rows by the presence of idem_key — raw documents
            # never have this field. Some raw formats (e.g., Gmail API)
            # have their own "payload" key, so we can't use that alone.
            raw_doc = item
            passthrough = None
            is_bq_row = isinstance(item, dict) and "idem_key" in item and "payload" in item
            if is_bq_row:
                raw_doc = item["payload"]
                if isinstance(raw_doc, str):
                    import json as _json
                    raw_doc = _json.loads(raw_doc)
                passthrough = {k: v for k, v in item.items() if k != "payload"}

            canonized = canonicalize(
                raw_doc,
                transform_id=transform_id,
                schemas_dir=schemas_dir,
                validate_input=validate_input,
                validate_output=validate_output,
            )

            if canonized is None:
                skipped_count += 1
                continue

            if passthrough is not None:
                output_item = dict(passthrough)
                output_item["payload"] = canonized
                output_items.append(output_item)
            else:
                output_items.append(canonized)
        except Exception:
            # Re-raise on error - lorchestra classifies at the boundary
            # For v0, we fail fast on any error rather than collecting partial results
            raise

    # Build result
    result = CallableResult(
        items=output_items,
        stats={
            "input": input_count,
            "output": len(output_items),
            "skipped": skipped_count,
            "errors": error_count,
        },
    )

    return result.to_dict()


def _get_default_transform_id(source_type: str) -> str:
    """Get default transform ID for a source type.

    Args:
        source_type: Type of source data

    Returns:
        Default transform ID for the source type

    Raises:
        ValueError: If source type is unknown
    """
    # Map source types to default transforms
    default_transforms = {
        "email": "email/gmail_to_jmap_lite@1.0.0",
        "gmail": "email/gmail_to_jmap_lite@1.0.0",
        "exchange": "email/exchange_to_jmap_lite@1.0.0",
        "form": "forms/google_forms_to_canonical@1.0.0",
        "google_forms": "forms/google_forms_to_canonical@1.0.0",
    }

    if source_type not in default_transforms:
        raise ValueError(
            f"Unknown source_type: {source_type}. "
            f"Provide explicit 'transform_id' in config or use one of: "
            f"{', '.join(sorted(default_transforms.keys()))}"
        )

    return default_transforms[source_type]


# ============================================================================
# Convenience Functions
# ============================================================================


def canonicalize_email_from_gmail(
    raw_email: dict,
    *,
    format: str = "lite",
    schemas_dir: str | Path | None = None,
) -> dict:
    """
    Transform Gmail API message to canonical JMAP format.

    Args:
        raw_email: Raw Gmail API message (users.messages.get response)
        format: Canonical format - "full", "lite", or "minimal" (default: "lite")
        schemas_dir: Schema directory (default: "schemas")

    Returns:
        Canonical JMAP email document

    Example:
        >>> from canonizer import canonicalize_email_from_gmail
        >>> canonical = canonicalize_email_from_gmail(
        ...     raw_gmail_message,
        ...     format="lite"
        ... )
    """
    if format not in ("full", "lite", "minimal"):
        raise ValueError(f"Invalid format: {format}. Must be 'full', 'lite', or 'minimal'")

    transform_id = f"email/gmail_to_jmap_{format}@1.0.0"
    return canonicalize(raw_email, transform_id=transform_id, schemas_dir=schemas_dir)


def canonicalize_email_from_exchange(
    raw_email: dict,
    *,
    format: str = "lite",
    schemas_dir: str | Path | None = None,
) -> dict:
    """
    Transform Microsoft Graph API message to canonical JMAP format.

    Args:
        raw_email: Raw Exchange/Graph API message
        format: Canonical format - "full", "lite", or "minimal" (default: "lite")
        schemas_dir: Schema directory (default: "schemas")

    Returns:
        Canonical JMAP email document

    Example:
        >>> from canonizer import canonicalize_email_from_exchange
        >>> canonical = canonicalize_email_from_exchange(
        ...     raw_exchange_message,
        ...     format="full"
        ... )
    """
    if format not in ("full", "lite", "minimal"):
        raise ValueError(f"Invalid format: {format}. Must be 'full', 'lite', or 'minimal'")

    transform_id = f"email/exchange_to_jmap_{format}@1.0.0"
    return canonicalize(raw_email, transform_id=transform_id, schemas_dir=schemas_dir)


def canonicalize_form_response(
    raw_form: dict,
    *,
    schemas_dir: str | Path | None = None,
) -> dict:
    """
    Transform Google Forms response to canonical form_response format.

    Args:
        raw_form: Raw Google Forms API response
        schemas_dir: Schema directory (default: "schemas")

    Returns:
        Canonical form_response document

    Example:
        >>> from canonizer import canonicalize_form_response
        >>> canonical = canonicalize_form_response(raw_google_forms_response)
    """
    transform_id = "forms/google_forms_to_canonical@1.0.0"
    return canonicalize(raw_form, transform_id=transform_id, schemas_dir=schemas_dir)


# ============================================================================
# Internal Helpers
# ============================================================================


def _resolve_transform_id(transform_id: str) -> Path:
    """
    Resolve registry-style transform ID to local .meta.yaml path.

    Resolution order:
    1. Local .canonizer/registry/transforms/ (if .canonizer/ exists)
    2. CANONIZER_REGISTRY_ROOT/transforms/ (if env var set)
    3. Current directory/transforms/ (fallback)

    Args:
        transform_id: Registry-style ID (e.g., "email/gmail_to_jmap_lite@1.0.0")

    Returns:
        Path to .meta.yaml file

    Raises:
        ValueError: If transform_id format is invalid
        FileNotFoundError: If transform doesn't exist locally
    """
    # Parse registry-style ID: "domain/name@version"
    if "@" not in transform_id:
        raise ValueError(
            f"Invalid transform_id: {transform_id}. "
            f'Expected format: "domain/name@version" (e.g., "email/gmail_to_jmap_lite@1.0.0")'
        )

    # Try local .canonizer/ resolution first
    canonizer_root = _try_find_canonizer_root()
    if canonizer_root:
        return resolve_transform(transform_id, canonizer_root)

    # Fall back to old resolution
    path_part, version = transform_id.rsplit("@", 1)
    registry_root = get_registry_root()

    # Convert to local path
    # "email/gmail_to_jmap_lite@1.0.0" → "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"
    local_path = registry_root / "transforms" / path_part / version / "spec.meta.yaml"

    if not local_path.exists():
        raise FileNotFoundError(
            f"Transform not found: {transform_id}\n"
            f"Expected path: {local_path}\n"
            f"Run 'canonizer init' and 'canonizer import' to set up local registry"
        )

    return local_path
