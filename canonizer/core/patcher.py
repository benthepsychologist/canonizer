"""Transform patcher: apply schema changes to JSONata transforms."""

import re
from pathlib import Path
from typing import NamedTuple

from canonizer.core.differ import ChangeType, SchemaChange, SchemaDiff
from canonizer.registry.loader import TransformLoader
from canonizer.registry.transform_meta import TransformMeta


class PatchResult(NamedTuple):
    """Result of applying a patch to a transform."""

    success: bool
    updated_jsonata: str | None
    updated_meta: TransformMeta | None
    applied_changes: list[SchemaChange]
    skipped_changes: list[SchemaChange]
    error: str | None


class TransformPatcher:
    """
    Apply schema diffs to JSONata transforms.

    Philosophy:
    - Only handles ADD (optional fields) and RENAME changes
    - All other changes require manual review or LLM
    - Conservative: fail safely rather than apply incorrect patches
    """

    @staticmethod
    def patch_transform(
        transform_path: Path | str,
        schema_diff: SchemaDiff,
        bump_version: bool = True,
    ) -> PatchResult:
        """
        Apply schema diff to a transform.

        Args:
            transform_path: Path to .meta.yaml file
            schema_diff: SchemaDiff from differ
            bump_version: Whether to bump MINOR version (default: True)

        Returns:
            PatchResult with updated transform or error
        """
        try:
            # Load transform
            transform = TransformLoader.load(transform_path)
            jsonata_content = transform.jsonata

            applied_changes: list[SchemaChange] = []
            skipped_changes: list[SchemaChange] = []

            # Apply each change
            for change in schema_diff.changes:
                if not change.auto_patchable:
                    skipped_changes.append(change)
                    continue

                if change.change_type == ChangeType.ADD:
                    # Apply ADD change
                    result = TransformPatcher._apply_add(jsonata_content, change)
                    if result:
                        jsonata_content = result
                        applied_changes.append(change)
                    else:
                        skipped_changes.append(change)

                elif change.change_type == ChangeType.RENAME:
                    # Apply RENAME change
                    result = TransformPatcher._apply_rename(jsonata_content, change)
                    if result:
                        jsonata_content = result
                        applied_changes.append(change)
                    else:
                        skipped_changes.append(change)

                else:
                    skipped_changes.append(change)

            # If no changes applied, return early
            if not applied_changes:
                return PatchResult(
                    success=False,
                    updated_jsonata=None,
                    updated_meta=None,
                    applied_changes=[],
                    skipped_changes=skipped_changes,
                    error="No auto-patchable changes found",
                )

            # Bump version if requested
            updated_meta = transform.meta.model_copy(deep=True)
            if bump_version:
                updated_meta = TransformPatcher._bump_version(updated_meta)

            return PatchResult(
                success=True,
                updated_jsonata=jsonata_content,
                updated_meta=updated_meta,
                applied_changes=applied_changes,
                skipped_changes=skipped_changes,
                error=None,
            )

        except Exception as e:
            return PatchResult(
                success=False,
                updated_jsonata=None,
                updated_meta=None,
                applied_changes=[],
                skipped_changes=schema_diff.changes,
                error=str(e),
            )

    @staticmethod
    def _apply_add(jsonata: str, change: SchemaChange) -> str | None:
        """
        Apply ADD change to JSONata.

        Strategy: Add field to output object with null/undefined default.
        Only works if JSONata has a simple object output.
        """
        field_name = change.path

        # Check if JSONata is a simple object (starts with '{' and ends with '}')
        jsonata_stripped = jsonata.strip()
        if not (jsonata_stripped.startswith("{") and jsonata_stripped.endswith("}")):
            return None  # Too complex, skip

        # Add field before closing brace
        # Find the last closing brace
        last_brace_idx = jsonata_stripped.rfind("}")

        # Check if there's already a trailing comma or if object is empty
        before_brace = jsonata_stripped[:last_brace_idx].rstrip()

        if before_brace.endswith("{"):
            # Empty object
            new_field = f'  "{field_name}": null'
        else:
            # Add comma and new field
            new_field = f',\n  "{field_name}": null'

        # Insert new field
        updated = (
            jsonata_stripped[:last_brace_idx] + new_field + "\n" + jsonata_stripped[last_brace_idx:]
        )

        return updated

    @staticmethod
    def _apply_rename(jsonata: str, change: SchemaChange) -> str | None:
        """
        Apply RENAME change to JSONata.

        Strategy: Simple string replacement of field names.
        Conservative: only replaces in quoted strings to avoid false positives.
        """
        # Parse rename path (format: "old_name→new_name")
        parts = change.path.split("→")
        if len(parts) != 2:
            return None

        old_name, new_name = parts

        # Replace quoted field names (in JSONata output)
        # Pattern: "field_name": or 'field_name':
        pattern_double = rf'"{re.escape(old_name)}"(\s*):'
        pattern_single = rf"'{re.escape(old_name)}'(\s*):"

        updated = re.sub(pattern_double, rf'"{new_name}"\1:', jsonata)
        updated = re.sub(pattern_single, rf"'{new_name}'\1:", updated)

        # Check if any replacements were made
        if updated == jsonata:
            return None  # No matches found

        return updated

    @staticmethod
    def _bump_version(meta: TransformMeta) -> TransformMeta:
        """
        Bump MINOR version (SchemaVer: MODEL-REVISION-ADDITION).

        For schema evolution:
        - ADD → bump ADDITION (patch version)
        - RENAME → bump REVISION (minor version)
        - Breaking changes → bump MODEL (major version)

        Since we only handle ADD and RENAME, we bump REVISION (minor).
        """
        parts = meta.version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {meta.version}")

        model, revision, addition = parts

        # Bump REVISION (minor version)
        new_revision = int(revision) + 1
        new_version = f"{model}.{new_revision}.0"

        # Update meta
        updated_meta = meta.model_copy(deep=True)
        updated_meta.version = new_version

        return updated_meta


def save_patched_transform(
    result: PatchResult,
    output_jsonata_path: Path,
    output_meta_path: Path | None = None,
) -> None:
    """
    Save patched transform to disk.

    Args:
        result: PatchResult from patch_transform
        output_jsonata_path: Where to write updated .jsonata file
        output_meta_path: Where to write updated .meta.yaml (optional)

    Raises:
        ValueError: If patch was not successful
    """
    if not result.success or not result.updated_jsonata:
        raise ValueError("Cannot save unsuccessful patch result")

    # Write JSONata file
    output_jsonata_path.write_text(result.updated_jsonata)

    # Write meta file if provided
    if output_meta_path and result.updated_meta:
        import yaml

        meta_dict = result.updated_meta.model_dump(mode="json")
        output_meta_path.write_text(yaml.dump(meta_dict, default_flow_style=False, sort_keys=False))
