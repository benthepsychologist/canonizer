"""Canonizer - Pure JSON transformation library.

This is a thin Python wrapper around the Node.js canonizer-core package.
All transform logic, schema validation, and JSONata execution happens in Node.

Public API:
- canonicalize(raw_document, transform_id) → canonical_dict
- validate_payload(payload, schema_iglu) → (is_valid, errors)
- run_batch(documents, transform_id) → list[dict]
"""

from canonizer.api import (
    canonicalize,
    validate_payload,
    run_batch,
    TransformError,
)

__version__ = "0.5.0"

__all__ = [
    "canonicalize",
    "validate_payload",
    "run_batch",
    "TransformError",
]
