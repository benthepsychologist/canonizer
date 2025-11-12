"""Unit tests for SchemaValidator."""

import json
from pathlib import Path

import pytest

from canonizer.core.validator import (
    SchemaValidator,
    ValidationError,
    load_schema_from_iglu_uri,
)


def test_validator_with_valid_data(tmp_path: Path):
    """Test validation with valid data."""
    # Create test schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }

    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text(json.dumps(schema))

    # Validate valid data
    validator = SchemaValidator(schema_file)
    data = {"name": "Alice", "age": 30}
    validator.validate(data)  # Should not raise


def test_validator_with_invalid_data(tmp_path: Path):
    """Test validation with invalid data."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }

    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text(json.dumps(schema))

    validator = SchemaValidator(schema_file)
    data = {"age": 30}  # Missing required 'name'

    with pytest.raises(ValidationError) as exc_info:
        validator.validate(data)

    assert "Validation failed" in str(exc_info.value)
    assert len(exc_info.value.errors) >= 1


def test_validator_missing_schema_file(tmp_path: Path):
    """Test validator with nonexistent schema file."""
    schema_file = tmp_path / "nonexistent.schema.json"

    with pytest.raises(FileNotFoundError):
        SchemaValidator(schema_file)


def test_is_valid_returns_bool(tmp_path: Path):
    """Test is_valid method returns boolean."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text(json.dumps(schema))

    validator = SchemaValidator(schema_file)

    assert validator.is_valid({"name": "Alice"}) is True
    assert validator.is_valid({"age": 30}) is False  # Missing required field


def test_validate_with_schema_dict():
    """Test validate_with_schema using schema dict."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    # Valid data
    SchemaValidator.validate_with_schema({"name": "Alice"}, schema)

    # Invalid data
    with pytest.raises(ValidationError):
        SchemaValidator.validate_with_schema({"age": 30}, schema)


def test_load_schema_from_iglu_uri(tmp_path: Path):
    """Test loading schema from Iglu URI."""
    # Create schema directory structure
    schema_dir = tmp_path / "com.google" / "gmail_email" / "jsonschema"
    schema_dir.mkdir(parents=True)

    schema_file = schema_dir / "1-0-0.json"
    schema_file.write_text(json.dumps({"type": "object"}))

    # Load via Iglu URI
    iglu_uri = "iglu:com.google/gmail_email/jsonschema/1-0-0"
    loaded_path = load_schema_from_iglu_uri(iglu_uri, tmp_path)

    assert loaded_path == schema_file
    assert loaded_path.exists()


def test_load_schema_invalid_iglu_uri():
    """Test loading schema with invalid Iglu URI."""
    with pytest.raises(ValueError) as exc_info:
        load_schema_from_iglu_uri("not-an-iglu-uri", Path("."))

    assert "Invalid Iglu URI" in str(exc_info.value)


def test_validation_error_attributes():
    """Test ValidationError has expected attributes."""
    error = ValidationError("Test error", ["error 1", "error 2"])

    assert str(error) == "Test error"
    assert error.errors == ["error 1", "error 2"]
