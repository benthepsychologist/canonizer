"""Pure JSON transformation API for Canonizer.

This module provides a clean, programmatic interface for transforming raw JSON
documents to canonical formats using JSONata transforms.

Core principle: raw_json + transform_id → canonical_json

NO orchestration logic - no events, no BigQuery, no job patterns.
"""

from pathlib import Path

from canonizer.core.runtime import TransformRuntime


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

    # Initialize runtime
    if schemas_dir is None:
        schemas_dir = "schemas"

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

    path_part, version = transform_id.rsplit("@", 1)

    # Convert to local path
    # "email/gmail_to_jmap_lite@1.0.0" → "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"
    local_path = Path("transforms") / path_part / version / "spec.meta.yaml"

    if not local_path.exists():
        raise FileNotFoundError(
            f"Transform not found: {transform_id}\n"
            f"Expected path: {local_path}\n"
            f"Make sure the transform exists locally or use the full path to .meta.yaml"
        )

    return local_path
