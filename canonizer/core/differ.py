"""Schema differ: classify schema changes (add/rename/remove/type-change)."""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ChangeType(str, Enum):
    """Types of schema changes."""

    ADD = "add"  # New field added (can auto-patch)
    RENAME = "rename"  # Field renamed (can auto-patch with heuristics)
    REMOVE = "remove"  # Field removed (manual review)
    TYPE_CHANGE = "type_change"  # Type changed (manual review)
    COMPLEX = "complex"  # Complex structural change (manual/LLM)


class SchemaChange(BaseModel):
    """Represents a single schema change."""

    change_type: ChangeType
    path: str  # JSON path (dot-separated, e.g., "user.email")
    old_value: Any | None = None
    new_value: Any | None = None
    description: str
    auto_patchable: bool  # Whether this change can be auto-applied


class SchemaDiff(BaseModel):
    """Result of schema diffing."""

    from_schema_path: str
    to_schema_path: str
    changes: list[SchemaChange]
    auto_patchable_count: int
    manual_review_count: int

    @property
    def has_auto_patchable(self) -> bool:
        """Check if diff has any auto-patchable changes."""
        return self.auto_patchable_count > 0

    @property
    def has_manual_review(self) -> bool:
        """Check if diff has any manual review changes."""
        return self.manual_review_count > 0


class SchemaDiffer:
    """
    Schema differ that classifies changes between two JSON Schemas.

    Philosophy:
    - Only ADD and RENAME are auto-patchable
    - REMOVE, TYPE_CHANGE, and COMPLEX require manual review or LLM
    - Conservative: when in doubt, mark as manual review
    """

    @staticmethod
    def diff_schemas(
        from_schema: dict[str, Any] | Path,
        to_schema: dict[str, Any] | Path,
    ) -> SchemaDiff:
        """
        Diff two JSON schemas and classify changes.

        Args:
            from_schema: Source schema (dict or path to JSON file)
            to_schema: Target schema (dict or path to JSON file)

        Returns:
            SchemaDiff with classified changes
        """
        # Load schemas if paths provided
        if isinstance(from_schema, Path):
            from_schema_dict = json.loads(from_schema.read_text())
            from_schema_path = str(from_schema)
        else:
            from_schema_dict = from_schema
            from_schema_path = "<dict>"

        if isinstance(to_schema, Path):
            to_schema_dict = json.loads(to_schema.read_text())
            to_schema_path = str(to_schema)
        else:
            to_schema_dict = to_schema
            to_schema_path = "<dict>"

        # Extract properties from JSON Schema
        from_props = from_schema_dict.get("properties", {})
        to_props = to_schema_dict.get("properties", {})

        # Get required fields
        from_required = set(from_schema_dict.get("required", []))
        to_required = set(to_schema_dict.get("required", []))

        changes: list[SchemaChange] = []

        # Detect additions
        added_fields = set(to_props.keys()) - set(from_props.keys())
        for field in added_fields:
            is_required = field in to_required
            change = SchemaChange(
                change_type=ChangeType.ADD,
                path=field,
                old_value=None,
                new_value=to_props[field],
                description=f"Added field '{field}' ({'required' if is_required else 'optional'})",
                auto_patchable=not is_required,  # Only optional adds are auto-patchable
            )
            changes.append(change)

        # Detect removals
        removed_fields = set(from_props.keys()) - set(to_props.keys())
        for field in removed_fields:
            was_required = field in from_required
            change = SchemaChange(
                change_type=ChangeType.REMOVE,
                path=field,
                old_value=from_props[field],
                new_value=None,
                description=f"Removed field '{field}' ({'required' if was_required else 'optional'})",
                auto_patchable=False,  # Removals require manual review
            )
            changes.append(change)

        # Detect type changes and modifications
        common_fields = set(from_props.keys()) & set(to_props.keys())
        for field in common_fields:
            from_field = from_props[field]
            to_field = to_props[field]

            # Check type changes
            from_type = from_field.get("type")
            to_type = to_field.get("type")

            if from_type != to_type:
                change = SchemaChange(
                    change_type=ChangeType.TYPE_CHANGE,
                    path=field,
                    old_value=from_field,
                    new_value=to_field,
                    description=f"Type changed for '{field}': {from_type} → {to_type}",
                    auto_patchable=False,
                )
                changes.append(change)

            # Check required status changes
            was_required = field in from_required
            is_required = field in to_required

            if was_required != is_required:
                status_change = "required → optional" if was_required else "optional → required"
                change = SchemaChange(
                    change_type=ChangeType.TYPE_CHANGE if is_required else ChangeType.COMPLEX,
                    path=field,
                    old_value=from_field,
                    new_value=to_field,
                    description=f"Field '{field}' changed: {status_change}",
                    auto_patchable=False,
                )
                changes.append(change)

        # Detect renames (heuristic: similar names, same type)
        # This is a simple heuristic - more sophisticated matching could be added
        for removed in removed_fields:
            for added in added_fields:
                # Check if names are similar (simple substring match)
                if (
                    removed.lower() in added.lower()
                    or added.lower() in removed.lower()
                    or _levenshtein_distance(removed, added) <= 3
                ):
                    # Check if types match
                    from_type = from_props[removed].get("type")
                    to_type = to_props[added].get("type")

                    if from_type == to_type:
                        # Likely a rename - mark both changes as rename
                        # Remove the original ADD and REMOVE changes
                        changes = [
                            c
                            for c in changes
                            if not (
                                (c.change_type == ChangeType.ADD and c.path == added)
                                or (c.change_type == ChangeType.REMOVE and c.path == removed)
                            )
                        ]

                        change = SchemaChange(
                            change_type=ChangeType.RENAME,
                            path=f"{removed}→{added}",
                            old_value=from_props[removed],
                            new_value=to_props[added],
                            description=f"Field renamed: '{removed}' → '{added}'",
                            auto_patchable=True,
                        )
                        changes.append(change)
                        break

        # Calculate counts
        auto_patchable_count = sum(1 for c in changes if c.auto_patchable)
        manual_review_count = len(changes) - auto_patchable_count

        return SchemaDiff(
            from_schema_path=from_schema_path,
            to_schema_path=to_schema_path,
            changes=changes,
            auto_patchable_count=auto_patchable_count,
            manual_review_count=manual_review_count,
        )


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.

    Used for rename detection heuristics.
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]
