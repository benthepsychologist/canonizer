"""JSON Schema validation for inputs and outputs."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


class ValidationError(Exception):
    """Raised when JSON Schema validation fails."""

    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


class SchemaValidator:
    """Validates JSON data against JSON Schema."""

    def __init__(self, schema_path: Path | str):
        """
        Initialize validator with a JSON Schema file.

        Args:
            schema_path: Path to JSON Schema file

        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema is invalid JSON
        """
        self.schema_path = Path(schema_path)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        with open(self.schema_path) as f:
            self.schema = json.load(f)

        # Create validator with format checking enabled
        self.validator = Draft7Validator(self.schema)

    def validate(self, data: Any) -> None:
        """
        Validate data against schema.

        Args:
            data: JSON data to validate

        Raises:
            ValidationError: If validation fails with detailed error messages
        """
        errors = list(self.validator.iter_errors(data))

        if errors:
            error_messages = [
                f"{error.json_path}: {error.message}" for error in errors
            ]
            raise ValidationError(
                f"Validation failed with {len(errors)} error(s)", error_messages
            )

    def is_valid(self, data: Any) -> bool:
        """
        Check if data is valid against schema without raising exception.

        Args:
            data: JSON data to validate

        Returns:
            True if valid, False otherwise
        """
        return self.validator.is_valid(data)

    @staticmethod
    def validate_with_schema(data: Any, schema: dict) -> None:
        """
        Validate data against a schema dict (no file required).

        Args:
            data: JSON data to validate
            schema: JSON Schema as dict

        Raises:
            ValidationError: If validation fails
        """
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))

        if errors:
            error_messages = [
                f"{error.json_path}: {error.message}" for error in errors
            ]
            raise ValidationError(
                f"Validation failed with {len(errors)} error(s)", error_messages
            )


def load_schema_from_iglu_uri(iglu_uri: str, schemas_dir: Path) -> Path:
    """
    Resolve Iglu schema URI to local file path.

    Args:
        iglu_uri: Iglu URI (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")
        schemas_dir: Base directory for schemas

    Returns:
        Path to schema file

    Example:
        iglu:com.google/gmail_email/jsonschema/1-0-0
        → schemas_dir/com.google/gmail_email/jsonschema/1-0-0.json
    """
    # Parse Iglu URI: iglu:vendor/name/format/version
    if not iglu_uri.startswith("iglu:"):
        raise ValueError(f"Invalid Iglu URI: {iglu_uri}")

    parts = iglu_uri[5:].split("/")  # Remove "iglu:" prefix
    if len(parts) != 4:
        raise ValueError(f"Invalid Iglu URI format: {iglu_uri}")

    vendor, name, format_type, version = parts

    # Convert SchemaVer (1-0-0) to path
    schema_path = schemas_dir / vendor / name / format_type / f"{version}.json"

    return schema_path
