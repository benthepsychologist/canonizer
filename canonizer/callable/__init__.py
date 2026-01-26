"""Callable protocol for lorchestra integration.

This module provides the in-process execute() interface that lorchestra
calls directly (no JSON-RPC wrapper) to perform canonization.

Example:
    >>> from canonizer.callable import CallableResult
    >>> result = CallableResult(
    ...     items=[{"id": "1", "data": "..."}],
    ...     stats={"input": 1, "output": 1}
    ... )
"""

from canonizer.callable.result import CallableResult

__all__ = ["CallableResult"]
