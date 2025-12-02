"""Integration tests for local registry resolution.

Tests that the API functions correctly resolve schemas and transforms
from the local .canonizer/ directory.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from canonizer import canonicalize, validate_payload
from canonizer.local.config import CanonizerConfig, RegistryConfig
from canonizer.local.lock import LockFile
from canonizer.local.resolver import TransformNotFoundError


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with .canonizer/ setup."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Create .canonizer directory structure
    canonizer_dir = temp_path / ".canonizer"
    canonizer_dir.mkdir()
    registry_dir = canonizer_dir / "registry"
    registry_dir.mkdir()

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def project_with_schemas(temp_project_dir):
    """Create a project with schemas copied from the test fixtures."""
    canonizer_dir = temp_project_dir / ".canonizer"
    registry_dir = canonizer_dir / "registry"
    schemas_dir = registry_dir / "schemas"

    # Create schema directories
    gmail_schema_dir = schemas_dir / "com.google" / "gmail_email" / "jsonschema"
    gmail_schema_dir.mkdir(parents=True)

    jmap_schema_dir = schemas_dir / "org.canonical" / "email_jmap_lite" / "jsonschema"
    jmap_schema_dir.mkdir(parents=True)

    # Copy schemas from the main .canonizer directory
    main_canonizer = Path("/workspace/canonizer/.canonizer/registry/schemas")
    if main_canonizer.exists():
        src_gmail = main_canonizer / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json"
        src_jmap = main_canonizer / "org.canonical" / "email_jmap_lite" / "jsonschema" / "1-0-0.json"

        if src_gmail.exists():
            shutil.copy(src_gmail, gmail_schema_dir / "1-0-0.json")
        if src_jmap.exists():
            shutil.copy(src_jmap, jmap_schema_dir / "1-0-0.json")

    # Create config
    config = CanonizerConfig(registry=RegistryConfig())
    config.save(canonizer_dir / "config.yaml")

    # Create lock file
    lock = LockFile()
    lock.save(canonizer_dir / "lock.json")

    return temp_project_dir


class TestValidatePayloadLocalResolution:
    """Test validate_payload uses local .canonizer/ resolution."""

    def test_validate_valid_gmail_email(self, project_with_schemas, monkeypatch):
        """Test validating a valid Gmail email against local schema."""
        monkeypatch.chdir(project_with_schemas)

        valid_email = {
            "id": "12345",
            "threadId": "thread-123",
            "labelIds": ["INBOX"],
            "snippet": "Test snippet",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test"}
                ]
            },
            "internalDate": "1732615200000"
        }

        is_valid, errors = validate_payload(
            valid_email,
            "iglu:com.google/gmail_email/jsonschema/1-0-0"
        )

        assert is_valid, f"Validation should pass: {errors}"
        assert errors == []

    def test_validate_invalid_gmail_email(self, project_with_schemas, monkeypatch):
        """Test validating an invalid Gmail email against local schema."""
        monkeypatch.chdir(project_with_schemas)

        invalid_email = {
            # Missing required fields
            "snippet": "Just a snippet"
        }

        is_valid, errors = validate_payload(
            invalid_email,
            "iglu:com.google/gmail_email/jsonschema/1-0-0"
        )

        assert not is_valid
        assert len(errors) > 0

    def test_validate_schema_not_found(self, project_with_schemas, monkeypatch):
        """Test error when schema is not in local registry."""
        monkeypatch.chdir(project_with_schemas)

        is_valid, errors = validate_payload(
            {"test": "data"},
            "iglu:com.nonexistent/schema/jsonschema/1-0-0"
        )

        assert not is_valid
        assert any("not found" in err.lower() for err in errors)


class TestCanonicalizeLocalResolution:
    """Test canonicalize uses local .canonizer/ resolution."""

    def test_canonicalize_transform_not_found(self, project_with_schemas, monkeypatch):
        """Test error when transform is not in local registry."""
        monkeypatch.chdir(project_with_schemas)

        with pytest.raises(TransformNotFoundError) as exc_info:
            canonicalize(
                {"test": "data"},
                transform_id="nonexistent/transform@1.0.0"
            )

        assert "not found" in str(exc_info.value).lower()


class TestCanonicalizeRealWorkspace:
    """Test canonicalize in the real workspace with Node.js available."""

    @pytest.mark.skipif(
        not Path("/workspace/canonizer/.canonizer").exists(),
        reason="Requires real .canonizer directory"
    )
    def test_canonicalize_gmail_email_real_workspace(self, monkeypatch):
        """Test canonicalizing a Gmail email using local transform in real workspace."""
        monkeypatch.chdir(Path("/workspace/canonizer"))

        gmail_message = {
            "id": "12345",
            "threadId": "thread-123",
            "labelIds": ["INBOX"],
            "snippet": "Test email snippet",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Wed, 26 Nov 2025 10:00:00 +0000"}
                ]
            },
            "internalDate": "1732615200000"
        }

        canonical = canonicalize(
            gmail_message,
            transform_id="email/gmail_to_jmap_lite@1.0.0"
        )

        assert canonical["id"] == "12345"
        assert canonical["threadId"] == "thread-123"
        assert canonical["subject"] == "Test Subject"
        assert canonical["preview"] == "Test email snippet"


class TestEnvironmentVariableFallback:
    """Test fallback to CANONIZER_REGISTRY_ROOT environment variable."""

    def test_env_var_fallback(self, temp_project_dir, monkeypatch):
        """Test that CANONIZER_REGISTRY_ROOT is used when no .canonizer/ exists."""
        # Create a registry directory outside .canonizer/
        registry_dir = temp_project_dir / "external_registry"
        registry_dir.mkdir()
        schemas_dir = registry_dir / "schemas" / "com.test" / "schema" / "jsonschema"
        schemas_dir.mkdir(parents=True)

        # Create a simple schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"]
        }
        with open(schemas_dir / "1-0-0.json", "w") as f:
            json.dump(schema, f)

        # Change to a directory without .canonizer/
        empty_dir = temp_project_dir / "empty_project"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)

        # Set environment variable
        monkeypatch.setenv("CANONIZER_REGISTRY_ROOT", str(registry_dir))

        is_valid, errors = validate_payload(
            {"value": "test"},
            "iglu:com.test/schema/jsonschema/1-0-0"
        )

        assert is_valid, f"Validation should pass: {errors}"


class TestBackwardCompatibility:
    """Test backward compatibility with old resolution patterns."""

    def test_explicit_schemas_dir_parameter(self, temp_project_dir, monkeypatch):
        """Test that explicit schemas_dir parameter overrides .canonizer/ resolution."""
        # Create schemas in a custom location
        custom_schemas = temp_project_dir / "custom" / "schemas" / "com.custom" / "schema" / "jsonschema"
        custom_schemas.mkdir(parents=True)

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"custom_field": {"type": "integer"}},
            "required": ["custom_field"]
        }
        with open(custom_schemas / "1-0-0.json", "w") as f:
            json.dump(schema, f)

        # Even if we're in a directory with .canonizer/, explicit param should win
        monkeypatch.chdir(temp_project_dir)

        is_valid, errors = validate_payload(
            {"custom_field": 42},
            "iglu:com.custom/schema/jsonschema/1-0-0",
            schemas_dir=temp_project_dir / "custom" / "schemas"
        )

        assert is_valid, f"Validation should pass: {errors}"
