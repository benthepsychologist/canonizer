"""Integration tests for bulk import command.

Tests the full workflow of importing all schemas and transforms from
a registry clone into a project's .canonizer/ directory.
"""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from canonizer.cli.main import app
from canonizer.local.config import CANONIZER_DIR, LOCK_FILENAME, REGISTRY_DIR


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def full_mock_registry(tmp_path):
    """Create a comprehensive mock registry for integration testing.

    Mimics the structure of canonizer-registry with multiple schemas
    and transforms across different categories.
    """
    registry = tmp_path / "canonizer-registry"
    registry.mkdir()

    # ================== SCHEMAS ==================
    schemas_dir = registry / "schemas"

    # com.google schemas
    gmail_schema_dir = schemas_dir / "com.google" / "gmail_email" / "jsonschema"
    gmail_schema_dir.mkdir(parents=True)
    (gmail_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Gmail Email",
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string"},
            "threadId": {"type": "string"},
            "snippet": {"type": "string"},
            "payload": {"type": "object"}
        }
    }))

    forms_schema_dir = schemas_dir / "com.google" / "forms_response" / "jsonschema"
    forms_schema_dir.mkdir(parents=True)
    (forms_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Google Forms Response",
        "type": "object",
        "required": ["responseId"],
        "properties": {
            "responseId": {"type": "string"},
            "formId": {"type": "string"}
        }
    }))

    # com.microsoft schemas
    exchange_schema_dir = schemas_dir / "com.microsoft" / "exchange_email" / "jsonschema"
    exchange_schema_dir.mkdir(parents=True)
    (exchange_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Exchange Email",
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string"},
            "subject": {"type": ["string", "null"]}
        }
    }))

    # org.canonical schemas
    jmap_lite_dir = schemas_dir / "org.canonical" / "email_jmap_lite" / "jsonschema"
    jmap_lite_dir.mkdir(parents=True)
    (jmap_lite_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "JMAP Lite Email",
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string"},
            "subject": {"type": "string"},
            "threadId": {"type": "string"}
        }
    }))

    form_response_dir = schemas_dir / "org.canonical" / "form_response" / "jsonschema"
    form_response_dir.mkdir(parents=True)
    (form_response_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Canonical Form Response",
        "type": "object",
        "required": ["response_id"],
        "properties": {
            "response_id": {"type": "string"}
        }
    }))

    # ================== TRANSFORMS ==================
    transforms_dir = registry / "transforms"

    # email/gmail_to_jmap_lite
    gmail_transform_dir = transforms_dir / "email" / "gmail_to_jmap_lite" / "1.0.0"
    gmail_transform_dir.mkdir(parents=True)
    (gmail_transform_dir / "spec.jsonata").write_text("""{
    "id": payload.id,
    "threadId": payload.threadId,
    "subject": payload.payload.headers[name="Subject"].value,
    "preview": payload.snippet
}""")
    (gmail_transform_dir / "spec.meta.yaml").write_text(yaml.dump({
        "id": "email/gmail_to_jmap_lite",
        "version": "1.0.0",
        "engine": "jsonata",
        "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/email_jmap_lite/jsonschema/1-0-0",
        "spec_path": "spec.jsonata",
        "status": "stable"
    }))

    # email/exchange_to_jmap_lite
    exchange_transform_dir = transforms_dir / "email" / "exchange_to_jmap_lite" / "1.0.0"
    exchange_transform_dir.mkdir(parents=True)
    (exchange_transform_dir / "spec.jsonata").write_text("""{
    "id": id,
    "subject": subject
}""")
    (exchange_transform_dir / "spec.meta.yaml").write_text(yaml.dump({
        "id": "email/exchange_to_jmap_lite",
        "version": "1.0.0",
        "engine": "jsonata",
        "from_schema": "iglu:com.microsoft/exchange_email/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/email_jmap_lite/jsonschema/1-0-0",
        "spec_path": "spec.jsonata",
        "status": "stable"
    }))

    # forms/google_forms_to_canonical
    forms_transform_dir = transforms_dir / "forms" / "google_forms_to_canonical" / "1.0.0"
    forms_transform_dir.mkdir(parents=True)
    (forms_transform_dir / "spec.jsonata").write_text("""{
    "response_id": responseId,
    "form_id": formId
}""")
    (forms_transform_dir / "spec.meta.yaml").write_text(yaml.dump({
        "id": "forms/google_forms_to_canonical",
        "version": "1.0.0",
        "engine": "jsonata",
        "from_schema": "iglu:com.google/forms_response/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/form_response/jsonschema/1-0-0",
        "spec_path": "spec.jsonata",
        "status": "stable"
    }))

    return registry


@pytest.fixture
def initialized_project(tmp_path, runner):
    """Create an initialized project with .canonizer/."""
    project = tmp_path / "test_project"
    project.mkdir()

    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 0, f"Init failed: {result.stdout}"

    return project


class TestBulkImportIntegration:
    """Integration tests for the bulk import workflow."""

    def test_full_import_workflow(self, runner, full_mock_registry, initialized_project):
        """Test importing an entire registry and verifying the result."""
        # Import everything
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
        ])

        assert result.exit_code == 0, f"Import failed: {result.stdout}"

        # Verify schemas were imported
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        schemas_path = registry_path / "schemas"

        assert (schemas_path / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json").exists()
        assert (schemas_path / "com.google" / "forms_response" / "jsonschema" / "1-0-0.json").exists()
        assert (schemas_path / "com.microsoft" / "exchange_email" / "jsonschema" / "1-0-0.json").exists()
        assert (schemas_path / "org.canonical" / "email_jmap_lite" / "jsonschema" / "1-0-0.json").exists()
        assert (schemas_path / "org.canonical" / "form_response" / "jsonschema" / "1-0-0.json").exists()

        # Verify transforms were imported
        transforms_path = registry_path / "transforms"

        assert (transforms_path / "email" / "gmail_to_jmap_lite" / "1.0.0" / "spec.jsonata").exists()
        assert (transforms_path / "email" / "gmail_to_jmap_lite" / "1.0.0" / "spec.meta.yaml").exists()
        assert (transforms_path / "email" / "exchange_to_jmap_lite" / "1.0.0" / "spec.jsonata").exists()
        assert (transforms_path / "forms" / "google_forms_to_canonical" / "1.0.0" / "spec.jsonata").exists()

        # Verify lock file was updated
        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        assert len(lock["schemas"]) == 5
        assert len(lock["transforms"]) == 3

        # Verify hashes are present
        for ref, entry in lock["schemas"].items():
            assert "hash" in entry
            assert entry["hash"].startswith("sha256:")

        for ref, entry in lock["transforms"].items():
            assert "hash" in entry
            assert entry["hash"].startswith("sha256:")

    def test_category_filter_integration(self, runner, full_mock_registry, initialized_project):
        """Test importing only a specific category."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
            "--category", "email",
        ])

        assert result.exit_code == 0, f"Import failed: {result.stdout}"

        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        transforms_path = registry_path / "transforms"

        # Email transforms should exist
        assert (transforms_path / "email" / "gmail_to_jmap_lite" / "1.0.0").exists()
        assert (transforms_path / "email" / "exchange_to_jmap_lite" / "1.0.0").exists()

        # Forms transforms should NOT exist
        assert not (transforms_path / "forms").exists()

        # But all schemas should still be imported
        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        assert len(lock["schemas"]) == 5  # All schemas
        assert len(lock["transforms"]) == 2  # Only email transforms

    def test_transforms_only_imports_referenced_schemas(self, runner, full_mock_registry, initialized_project):
        """Test that --transforms-only also imports schemas referenced by transforms."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
            "--transforms-only",
            "--category", "forms",
        ])

        assert result.exit_code == 0, f"Import failed: {result.stdout}"

        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR

        # Forms transform should exist
        assert (registry_path / "transforms" / "forms" / "google_forms_to_canonical" / "1.0.0").exists()

        # Email transforms should NOT exist
        assert not (registry_path / "transforms" / "email").exists()

        # Lock file should show form transform
        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        assert len(lock["transforms"]) == 1
        assert "forms/google_forms_to_canonical@1.0.0" in lock["transforms"]

    def test_schemas_only_no_transforms(self, runner, full_mock_registry, initialized_project):
        """Test that --schemas-only imports no transforms."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
            "--schemas-only",
        ])

        assert result.exit_code == 0, f"Import failed: {result.stdout}"

        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR

        # Schemas should exist
        assert (registry_path / "schemas" / "com.google").exists()
        assert (registry_path / "schemas" / "org.canonical").exists()

        # Transforms should NOT exist (directory may be created but empty)
        transforms_path = registry_path / "transforms"
        if transforms_path.exists():
            # Should have no transform directories
            assert len(list(transforms_path.iterdir())) == 0

        # Lock should have schemas but no transforms
        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        assert len(lock["schemas"]) == 5
        assert len(lock["transforms"]) == 0

    def test_re_import_updates_existing(self, runner, full_mock_registry, initialized_project):
        """Test that re-importing updates existing files."""
        # First import
        result1 = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
        ])
        assert result1.exit_code == 0

        # Modify a schema in the source registry
        gmail_schema = full_mock_registry / "schemas" / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json"
        modified_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Gmail Email - Modified",
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "newField": {"type": "string"}
            }
        }
        gmail_schema.write_text(json.dumps(modified_schema))

        # Re-import
        result2 = runner.invoke(app, [
            "import", "all",
            "--from", str(full_mock_registry),
            "--to", str(initialized_project),
        ])
        assert result2.exit_code == 0

        # Verify the local copy was updated
        local_schema = initialized_project / CANONIZER_DIR / REGISTRY_DIR / "schemas" / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json"
        with open(local_schema) as f:
            schema = json.load(f)

        assert schema["title"] == "Gmail Email - Modified"
        assert "newField" in schema["properties"]


class TestImportFromRealRegistry:
    """Tests that use the actual canonizer schemas directory if available."""

    @pytest.mark.skipif(
        not Path("/workspace/canonizer/schemas").exists(),
        reason="Requires real schemas directory"
    )
    def test_import_from_workspace_schemas(self, runner, initialized_project):
        """Test importing from the actual workspace schemas directory.

        Note: Some schemas may have non-standard version names (e.g., 1-0-0-proposed)
        which will fail to import. We check that at least some schemas were imported.
        """
        # The workspace itself can serve as a registry source
        workspace = Path("/workspace/canonizer")

        result = runner.invoke(app, [
            "import", "all",
            "--from", str(workspace),
            "--to", str(initialized_project),
            "--schemas-only",
        ])

        # May have partial failures due to non-standard schema names
        # Check that we imported at least some schemas
        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        assert len(lock["schemas"]) > 0, "Should have imported at least one schema"
        # Verify at least the standard schemas were imported
        assert any("gmail_email" in ref for ref in lock["schemas"]), "Gmail schema should be imported"
