"""Tests for canonizer import CLI commands."""

import json

import pytest
import yaml
from typer.testing import CliRunner

from canonizer.cli.cmds.import_cmd import (
    collect_schema_refs,
    collect_transform_refs,
)
from canonizer.cli.main import app
from canonizer.local.config import (
    CANONIZER_DIR,
    LOCK_FILENAME,
    REGISTRY_DIR,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_registry(tmp_path):
    """Create a mock registry structure for testing."""
    registry = tmp_path / "mock_registry"
    registry.mkdir()

    # Create schemas
    schemas_dir = registry / "schemas"

    # com.google/gmail_email
    gmail_schema_dir = schemas_dir / "com.google" / "gmail_email" / "jsonschema"
    gmail_schema_dir.mkdir(parents=True)
    (gmail_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"id": {"type": "string"}}
    }))

    # org.canonical/email_jmap_lite
    canonical_schema_dir = schemas_dir / "org.canonical" / "email_jmap_lite" / "jsonschema"
    canonical_schema_dir.mkdir(parents=True)
    (canonical_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"id": {"type": "string"}}
    }))

    # com.example/test
    test_schema_dir = schemas_dir / "com.example" / "test" / "jsonschema"
    test_schema_dir.mkdir(parents=True)
    (test_schema_dir / "1-0-0.json").write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object"
    }))

    # Create transforms
    transforms_dir = registry / "transforms"

    # email/gmail_to_jmap_lite
    gmail_transform_dir = transforms_dir / "email" / "gmail_to_jmap_lite" / "1.0.0"
    gmail_transform_dir.mkdir(parents=True)
    (gmail_transform_dir / "spec.jsonata").write_text('{"id": payload.id}')
    (gmail_transform_dir / "spec.meta.yaml").write_text(yaml.dump({
        "id": "email/gmail_to_jmap_lite",
        "version": "1.0.0",
        "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/email_jmap_lite/jsonschema/1-0-0",
    }))

    # forms/google_forms_to_canonical
    forms_transform_dir = transforms_dir / "forms" / "google_forms_to_canonical" / "1.0.0"
    forms_transform_dir.mkdir(parents=True)
    (forms_transform_dir / "spec.jsonata").write_text('{"response_id": payload.responseId}')
    (forms_transform_dir / "spec.meta.yaml").write_text(yaml.dump({
        "id": "forms/google_forms_to_canonical",
        "version": "1.0.0",
        "from_schema": "iglu:com.google/forms_response/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/form_response/jsonschema/1-0-0",
    }))

    return registry


@pytest.fixture
def initialized_project(tmp_path, runner):
    """Create an initialized project with .canonizer/."""
    project = tmp_path / "test_project"
    project.mkdir()

    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 0

    return project


class TestCollectRefs:
    """Tests for ref collection helper functions."""

    def test_collect_schema_refs(self, mock_registry):
        """Test collecting schema refs from registry."""
        refs = collect_schema_refs(mock_registry)

        assert len(refs) == 3
        assert "iglu:com.google/gmail_email/jsonschema/1-0-0" in refs
        assert "iglu:org.canonical/email_jmap_lite/jsonschema/1-0-0" in refs
        assert "iglu:com.example/test/jsonschema/1-0-0" in refs

    def test_collect_schema_refs_empty(self, tmp_path):
        """Test collecting schema refs from empty registry."""
        empty_registry = tmp_path / "empty"
        empty_registry.mkdir()

        refs = collect_schema_refs(empty_registry)
        assert refs == []

    def test_collect_transform_refs(self, mock_registry):
        """Test collecting transform refs from registry."""
        refs = collect_transform_refs(mock_registry)

        assert len(refs) == 2
        assert "email/gmail_to_jmap_lite@1.0.0" in refs
        assert "forms/google_forms_to_canonical@1.0.0" in refs

    def test_collect_transform_refs_with_category(self, mock_registry):
        """Test collecting transform refs with category filter."""
        refs = collect_transform_refs(mock_registry, category="email")

        assert len(refs) == 1
        assert "email/gmail_to_jmap_lite@1.0.0" in refs

    def test_collect_transform_refs_nonexistent_category(self, mock_registry):
        """Test collecting transform refs with nonexistent category."""
        refs = collect_transform_refs(mock_registry, category="nonexistent")

        assert refs == []


class TestImportAllCommand:
    """Tests for the import all command."""

    def test_import_all_basic(self, runner, mock_registry, initialized_project):
        """Test basic import all functionality."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "3 schemas" in result.stdout
        assert "2 transforms" in result.stdout
        assert "Import complete" in result.stdout

        # Check files were created
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        assert (registry_path / "schemas" / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json").exists()
        assert (registry_path / "transforms" / "email" / "gmail_to_jmap_lite" / "1.0.0" / "spec.jsonata").exists()

    def test_import_all_with_category(self, runner, mock_registry, initialized_project):
        """Test import all with category filter."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "--category", "email",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "1 transforms" in result.stdout

        # Check only email transform was imported
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        assert (registry_path / "transforms" / "email" / "gmail_to_jmap_lite" / "1.0.0").exists()
        assert not (registry_path / "transforms" / "forms").exists()

    def test_import_all_schemas_only(self, runner, mock_registry, initialized_project):
        """Test import all with --schemas-only."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "--schemas-only",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "3 schemas, 0 transforms" in result.stdout

        # Check only schemas were imported
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        assert (registry_path / "schemas" / "com.google").exists()
        assert not (registry_path / "transforms" / "email").exists()

    def test_import_all_transforms_only(self, runner, mock_registry, initialized_project):
        """Test import all with --transforms-only."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "--transforms-only",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "0 schemas, 2 transforms" in result.stdout
        # Also imports referenced schemas
        assert "Schemas (from transforms)" in result.stdout or "imported" in result.stdout

    def test_import_all_mutually_exclusive_flags(self, runner, mock_registry, initialized_project):
        """Test that --schemas-only and --transforms-only are mutually exclusive."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "--schemas-only",
            "--transforms-only",
        ])

        assert result.exit_code == 1
        assert "Cannot use --schemas-only and --transforms-only together" in result.stdout

    def test_import_all_updates_lock_file(self, runner, mock_registry, initialized_project):
        """Test that import all updates lock.json."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
        ])

        assert result.exit_code == 0

        lock_path = initialized_project / CANONIZER_DIR / LOCK_FILENAME
        with open(lock_path) as f:
            lock = json.load(f)

        # Check schemas in lock
        assert len(lock["schemas"]) == 3
        assert "iglu:com.google/gmail_email/jsonschema/1-0-0" in lock["schemas"]

        # Check transforms in lock
        assert len(lock["transforms"]) == 2
        assert "email/gmail_to_jmap_lite@1.0.0" in lock["transforms"]

    def test_import_all_nonexistent_source(self, runner, initialized_project):
        """Test import all with nonexistent source."""
        result = runner.invoke(app, [
            "import", "all",
            "--from", "/nonexistent/path",
            "--to", str(initialized_project),
        ])

        assert result.exit_code == 1
        assert "Source registry not found" in result.stdout

    def test_import_all_no_canonizer_root(self, runner, mock_registry, tmp_path):
        """Test import all without .canonizer/ directory."""
        project = tmp_path / "no_canonizer"
        project.mkdir()

        result = runner.invoke(app, [
            "import", "all",
            "--from", str(mock_registry),
            "--to", str(project),
        ])

        assert result.exit_code == 1
        assert "No .canonizer/ directory found" in result.stdout

    def test_import_all_empty_registry(self, runner, initialized_project, tmp_path):
        """Test import all from empty registry."""
        empty_registry = tmp_path / "empty_registry"
        empty_registry.mkdir()
        (empty_registry / "schemas").mkdir()
        (empty_registry / "transforms").mkdir()

        result = runner.invoke(app, [
            "import", "all",
            "--from", str(empty_registry),
            "--to", str(initialized_project),
        ])

        assert result.exit_code == 0
        assert "Nothing to import" in result.stdout


class TestImportRunCommand:
    """Tests for the import run command (single import)."""

    def test_import_single_schema(self, runner, mock_registry, initialized_project):
        """Test importing a single schema."""
        result = runner.invoke(app, [
            "import", "run",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "iglu:com.google/gmail_email/jsonschema/1-0-0",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "Importing schema" in result.stdout

        # Check file was created
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        assert (registry_path / "schemas" / "com.google" / "gmail_email" / "jsonschema" / "1-0-0.json").exists()

    def test_import_single_transform(self, runner, mock_registry, initialized_project):
        """Test importing a single transform."""
        result = runner.invoke(app, [
            "import", "run",
            "--from", str(mock_registry),
            "--to", str(initialized_project),
            "email/gmail_to_jmap_lite@1.0.0",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "Importing transform" in result.stdout

        # Check files were created
        registry_path = initialized_project / CANONIZER_DIR / REGISTRY_DIR
        transform_dir = registry_path / "transforms" / "email" / "gmail_to_jmap_lite" / "1.0.0"
        assert transform_dir.exists()
        assert (transform_dir / "spec.jsonata").exists()
        assert (transform_dir / "spec.meta.yaml").exists()


class TestImportListCommand:
    """Tests for the import list command."""

    def test_list_all(self, runner, mock_registry):
        """Test listing all items in registry."""
        result = runner.invoke(app, [
            "import", "list",
            "--from", str(mock_registry),
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "Schemas:" in result.stdout
        assert "iglu:com.google/gmail_email/jsonschema/1-0-0" in result.stdout
        assert "Transforms:" in result.stdout
        assert "email/gmail_to_jmap_lite@1.0.0" in result.stdout

    def test_list_with_category(self, runner, mock_registry):
        """Test listing with category filter."""
        result = runner.invoke(app, [
            "import", "list",
            "--from", str(mock_registry),
            "--category", "forms",
        ])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        assert "forms/google_forms_to_canonical@1.0.0" in result.stdout
        # Email transforms should not appear
        assert "email/gmail_to_jmap_lite" not in result.stdout
