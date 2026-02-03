"""JSON Schema validation via Node.js canonizer-core."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from canonizer.core.node_bridge import get_canonizer_core_bin


class ValidationError(Exception):
    """Raised when JSON Schema validation fails."""

    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


class SchemaValidator:
    """Validates JSON data against JSON Schema using Node.js ajv."""

    def __init__(self, schema_path: Path | str):
        """
        Initialize validator with a JSON Schema file.

        Args:
            schema_path: Path to JSON Schema file

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        self.schema_path = Path(schema_path).resolve()
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        # Try to determine if this is a registry-style path
        parts = self.schema_path.parts
        self._registry_style = "schemas" in parts

    def validate(self, data: Any) -> None:
        """
        Validate data against schema using Node.js.

        Args:
            data: JSON data to validate

        Raises:
            ValidationError: If validation fails with detailed error messages
        """
        bin_path = get_canonizer_core_bin()

        if self._registry_style:
            # Use Iglu URI resolution via registry
            parts = self.schema_path.parts
            schemas_idx = parts.index("schemas")
            vendor = parts[schemas_idx + 1]
            name = parts[schemas_idx + 2]
            # jsonschema folder
            version = parts[schemas_idx + 4].replace(".json", "")
            schema_uri = f"iglu:{vendor}/{name}/jsonschema/{version}"

            # Determine registry root (parent of schemas/)
            registry_root = self.schema_path
            for _ in range(5):  # Go up 5 levels from version.json
                registry_root = registry_root.parent

            cmd = [bin_path, "validate", "--schema", schema_uri, "--registry", str(registry_root)]
        else:
            # Use direct file path validation
            cmd = [bin_path, "validate-file", "--file", str(self.schema_path)]

        # Use temp file for stdin to avoid pipe buffer truncation.
        # Python's subprocess PIPE has issues with inputs > 64KB on some systems.
        input_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".json", delete=False
            ) as f:
                f.write(json.dumps(data).encode("utf-8"))
                input_file = f.name

            with open(input_file, "rb") as stdin_fh:
                proc = subprocess.Popen(
                    cmd,
                    stdin=stdin_fh,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                _, stderr_bytes = proc.communicate()

            if proc.returncode != 0:
                # Parse error messages from stderr
                stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""
                errors = [line for line in stderr.strip().split("\n") if line]
                raise ValidationError(
                    f"Validation failed with {len(errors)} error(s)",
                    errors
                )
        finally:
            if input_file and os.path.exists(input_file):
                os.unlink(input_file)

    def is_valid(self, data: Any) -> bool:
        """
        Check if data is valid against schema without raising exception.

        Args:
            data: JSON data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate(data)
            return True
        except ValidationError:
            return False

    @staticmethod
    def validate_with_schema(data: Any, schema: dict) -> None:
        """
        Validate data against a schema dict (no file required).

        Note: This creates a temporary file for the schema since Node CLI
        expects file paths.

        Args:
            data: JSON data to validate
            schema: JSON Schema as dict

        Raises:
            ValidationError: If validation fails
        """
        import os
        import tempfile

        # Create temporary schema file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(schema, f)
            temp_path = f.name

        try:
            validator = SchemaValidator(temp_path)
            validator.validate(data)
        finally:
            os.unlink(temp_path)


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
