"""CallableResult model for lorchestra integration.

Defines the response schema for the in-process execute() interface.
"""

from dataclasses import dataclass, field


@dataclass
class CallableResult:
    """Result of callable execution.

    Represents the response from execute(params) -> dict.

    Attributes:
        schema_version: Schema version for the result format (default: "1.0")
        items: List of result items (inline). XOR with items_ref.
        items_ref: Reference to artifact store (e.g., "artifact://..."). XOR with items.
        stats: Execution statistics (input count, output count, errors, etc.)

    Note:
        Exactly one of `items` or `items_ref` must be provided.
        v0 implementation only supports `items`; `items_ref` is reserved for
        future artifact store integration.
    """

    schema_version: str = "1.0"
    items: list[dict] | None = None
    items_ref: str | None = None
    stats: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate XOR constraint: exactly one of items or items_ref must be set."""
        has_items = self.items is not None
        has_items_ref = self.items_ref is not None

        if has_items and has_items_ref:
            raise ValueError(
                "CallableResult requires exactly one of 'items' or 'items_ref', not both"
            )

        if not has_items and not has_items_ref:
            raise ValueError(
                "CallableResult requires exactly one of 'items' or 'items_ref'"
            )

    def to_dict(self) -> dict:
        """Convert to dictionary matching CallableResult schema.

        Returns:
            Dict with schema_version, items or items_ref, and stats.
        """
        result: dict = {"schema_version": self.schema_version}

        if self.items is not None:
            result["items"] = self.items
        else:
            result["items_ref"] = self.items_ref

        if self.stats:
            result["stats"] = self.stats

        return result
