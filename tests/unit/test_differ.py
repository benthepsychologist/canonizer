"""Tests for schema differ."""

import pytest

from canonizer.core.differ import ChangeType, SchemaDiffer


def test_diff_add_optional_field():
    """Test detecting addition of optional field."""
    from_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    to_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["name"],
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.ADD
    assert diff.changes[0].path == "email"
    assert diff.changes[0].auto_patchable is True
    assert diff.auto_patchable_count == 1
    assert diff.manual_review_count == 0


def test_diff_add_required_field():
    """Test detecting addition of required field (not auto-patchable)."""
    from_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    to_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["name", "email"],
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.ADD
    assert diff.changes[0].path == "email"
    assert diff.changes[0].auto_patchable is False  # Required field
    assert diff.auto_patchable_count == 0
    assert diff.manual_review_count == 1


def test_diff_remove_field():
    """Test detecting removal of field."""
    from_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["name"],
    }

    to_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.REMOVE
    assert diff.changes[0].path == "email"
    assert diff.changes[0].auto_patchable is False
    assert diff.manual_review_count == 1


def test_diff_type_change():
    """Test detecting type change."""
    from_schema = {
        "type": "object",
        "properties": {"age": {"type": "string"}},
    }

    to_schema = {
        "type": "object",
        "properties": {"age": {"type": "number"}},
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.TYPE_CHANGE
    assert diff.changes[0].path == "age"
    assert diff.changes[0].auto_patchable is False


def test_diff_rename_detection():
    """Test rename detection via string similarity."""
    from_schema = {
        "type": "object",
        "properties": {"user_name": {"type": "string"}},
    }

    to_schema = {
        "type": "object",
        "properties": {"username": {"type": "string"}},
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    # Should detect rename (similar names, same type)
    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.RENAME
    assert "user_name" in diff.changes[0].path
    assert "username" in diff.changes[0].path
    assert diff.changes[0].auto_patchable is True


def test_diff_no_rename_different_types():
    """Test that rename is not detected if types differ."""
    from_schema = {
        "type": "object",
        "properties": {"user_name": {"type": "string"}},
    }

    to_schema = {
        "type": "object",
        "properties": {"username": {"type": "number"}},
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    # Should NOT detect rename (types differ)
    # Should show REMOVE and ADD instead
    change_types = {c.change_type for c in diff.changes}
    assert ChangeType.RENAME not in change_types
    assert ChangeType.ADD in change_types
    assert ChangeType.REMOVE in change_types


def test_diff_required_status_change():
    """Test detecting required status change."""
    from_schema = {
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": [],
    }

    to_schema = {
        "type": "object",
        "properties": {"email": {"type": "string"}},
        "required": ["email"],
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 1
    assert diff.changes[0].path == "email"
    assert diff.changes[0].auto_patchable is False
    assert "optional → required" in diff.changes[0].description


def test_diff_multiple_changes():
    """Test handling multiple changes at once."""
    from_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "string"},
            "old_field": {"type": "string"},
        },
        "required": ["name"],
    }

    to_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},  # Type change
            "email": {"type": "string"},  # Add
            # old_field removed
        },
        "required": ["name"],
    }

    diff = SchemaDiffer.diff_schemas(from_schema, to_schema)

    assert len(diff.changes) == 3
    change_types = {c.change_type for c in diff.changes}
    assert ChangeType.ADD in change_types
    assert ChangeType.REMOVE in change_types
    assert ChangeType.TYPE_CHANGE in change_types


def test_diff_no_changes():
    """Test diffing identical schemas."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }

    diff = SchemaDiffer.diff_schemas(schema, schema)

    assert len(diff.changes) == 0
    assert diff.auto_patchable_count == 0
    assert diff.manual_review_count == 0


def test_levenshtein_distance():
    """Test Levenshtein distance helper."""
    from canonizer.core.differ import _levenshtein_distance

    assert _levenshtein_distance("user_name", "username") == 1  # Remove underscore
    assert _levenshtein_distance("email", "email") == 0
    assert _levenshtein_distance("foo", "bar") == 3
    assert _levenshtein_distance("cat", "cats") == 1
