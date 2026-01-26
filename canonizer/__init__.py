"""Canonizer - Pure JSON transformation library.

Core API:
    canonicalize(raw_document, transform_id) -> dict
    run_batch(documents, transform_id) -> list[dict]
    execute(params) -> dict  # Callable protocol for lorchestra

Convenience functions:
    canonicalize_email_from_gmail(raw_email, format="lite") -> dict
    canonicalize_email_from_exchange(raw_email, format="lite") -> dict
    canonicalize_form_response(raw_form) -> dict

Example:
    >>> from canonizer import canonicalize
    >>> canonical = canonicalize(
    ...     raw_gmail_message,
    ...     transform_id="email/gmail_to_jmap_lite@1.0.0"
    ... )

    # Callable protocol (lorchestra integration)
    >>> from canonizer import execute
    >>> result = execute({
    ...     "source_type": "email",
    ...     "items": [raw_gmail_message],
    ...     "config": {}
    ... })
"""

__version__ = "0.5.0"

# Export main API
from canonizer.api import (
    canonicalize,
    canonicalize_email_from_exchange,
    canonicalize_email_from_gmail,
    canonicalize_form_response,
    execute,
    run_batch,
    validate_payload,
)
from canonizer.callable import CallableResult

__all__ = [
    "canonicalize",
    "run_batch",
    "execute",
    "validate_payload",
    "canonicalize_email_from_gmail",
    "canonicalize_email_from_exchange",
    "canonicalize_form_response",
    "CallableResult",
]
