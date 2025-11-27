"""Local registry management for Canonizer.

This module provides the `.canonizer/` directory model for local schema
and transform resolution without requiring a full registry clone.
"""

from canonizer.local.config import CanonizerConfig, RegistryConfig
from canonizer.local.lock import LockFile, SchemaLock, TransformLock
from canonizer.local.resolver import (
    CanonizerRootNotFoundError,
    InvalidReferenceError,
    ResolutionError,
    SchemaNotFoundError,
    TransformNotFoundError,
    find_canonizer_root,
    resolve_jsonata,
    resolve_schema,
    resolve_transform,
)

__all__ = [
    # Config
    "CanonizerConfig",
    "RegistryConfig",
    # Lock
    "LockFile",
    "SchemaLock",
    "TransformLock",
    # Resolver
    "find_canonizer_root",
    "resolve_schema",
    "resolve_transform",
    "resolve_jsonata",
    # Errors
    "ResolutionError",
    "CanonizerRootNotFoundError",
    "InvalidReferenceError",
    "SchemaNotFoundError",
    "TransformNotFoundError",
]
