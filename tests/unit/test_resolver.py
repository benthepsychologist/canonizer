"""Tests for local registry resolution functions."""

import tempfile
from pathlib import Path

import pytest

from canonizer.local.config import CanonizerConfig
from canonizer.local.lock import LockFile
from canonizer.local.resolver import (
    CanonizerRootNotFoundError,
    InvalidReferenceError,
    SchemaNotFoundError,
    TransformNotFoundError,
    find_canonizer_root,
    parse_iglu_ref,
    parse_transform_ref,
    resolve_jsonata,
    resolve_schema,
    resolve_transform,
    schema_ref_to_path,
    transform_ref_to_path,
)


def create_canonizer_dir(base_path: Path) -> Path:
    """Helper to create a valid .canonizer/ directory structure."""
    canonizer_dir = base_path / ".canonizer"
    registry_dir = canonizer_dir / "registry"
    (registry_dir / "schemas").mkdir(parents=True)
    (registry_dir / "transforms").mkdir(parents=True)

    # Create config.yaml
    config = CanonizerConfig.default()
    config.save(canonizer_dir / "config.yaml")

    # Create lock.json
    lock = LockFile.empty()
    lock.save(canonizer_dir / "lock.json")

    return canonizer_dir


class TestParseIgluRef:
    """Tests for parse_iglu_ref function."""

    def test_valid_ref(self):
        """Test parsing a valid Iglu reference."""
        vendor, name, version = parse_iglu_ref("iglu:com.google/gmail_email/jsonschema/1-0-0")
        assert vendor == "com.google"
        assert name == "gmail_email"
        assert version == "1-0-0"

    def test_valid_ref_with_dots_in_vendor(self):
        """Test parsing reference with dots in vendor name."""
        vendor, name, version = parse_iglu_ref("iglu:org.canonical/email_jmap_lite/jsonschema/2-1-0")
        assert vendor == "org.canonical"
        assert name == "email_jmap_lite"
        assert version == "2-1-0"

    def test_invalid_ref_no_prefix(self):
        """Test that reference without iglu: prefix fails."""
        with pytest.raises(InvalidReferenceError, match="Invalid Iglu"):
            parse_iglu_ref("com.google/gmail_email/jsonschema/1-0-0")

    def test_invalid_ref_wrong_format(self):
        """Test that malformed reference fails."""
        with pytest.raises(InvalidReferenceError, match="Invalid Iglu"):
            parse_iglu_ref("iglu:invalid")

    def test_invalid_ref_missing_version(self):
        """Test that reference without version fails."""
        with pytest.raises(InvalidReferenceError, match="Invalid Iglu"):
            parse_iglu_ref("iglu:com.google/gmail_email/jsonschema")


class TestParseTransformRef:
    """Tests for parse_transform_ref function."""

    def test_valid_ref(self):
        """Test parsing a valid transform reference."""
        transform_id, version = parse_transform_ref("email/gmail_to_jmap_lite@1.0.0")
        assert transform_id == "email/gmail_to_jmap_lite"
        assert version == "1.0.0"

    def test_valid_ref_nested(self):
        """Test parsing nested transform reference."""
        transform_id, version = parse_transform_ref("crm/salesforce/contact_to_canonical@2.1.0")
        assert transform_id == "crm/salesforce/contact_to_canonical"
        assert version == "2.1.0"

    def test_invalid_ref_no_version(self):
        """Test that reference without version fails."""
        with pytest.raises(InvalidReferenceError, match="Invalid transform"):
            parse_transform_ref("email/gmail_to_jmap_lite")

    def test_invalid_ref_wrong_version_format(self):
        """Test that reference with wrong version format fails."""
        with pytest.raises(InvalidReferenceError, match="Invalid transform"):
            parse_transform_ref("email/gmail@1.0")


class TestFindCanonizerRoot:
    """Tests for find_canonizer_root function."""

    def test_find_in_current_dir(self):
        """Test finding .canonizer/ in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            found = find_canonizer_root(base)
            assert found == canonizer_dir

    def test_find_in_parent_dir(self):
        """Test finding .canonizer/ in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            # Create nested directory
            nested = base / "src" / "lib" / "deep"
            nested.mkdir(parents=True)

            found = find_canonizer_root(nested)
            assert found == canonizer_dir

    def test_not_found(self):
        """Test error when .canonizer/ not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CanonizerRootNotFoundError, match="No .canonizer"):
                find_canonizer_root(Path(tmpdir))

    def test_ignores_dir_without_config(self):
        """Test that .canonizer/ without config.yaml is ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create .canonizer/ without config.yaml
            (base / ".canonizer").mkdir()

            with pytest.raises(CanonizerRootNotFoundError):
                find_canonizer_root(base)


class TestResolveSchema:
    """Tests for resolve_schema function."""

    def test_resolve_existing_schema(self):
        """Test resolving an existing schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            # Create schema file
            schema_dir = canonizer_dir / "registry" / "schemas" / "com.google" / "gmail_email" / "jsonschema"
            schema_dir.mkdir(parents=True)
            schema_file = schema_dir / "1-0-0.json"
            schema_file.write_text('{"type": "object"}')

            path = resolve_schema("iglu:com.google/gmail_email/jsonschema/1-0-0", canonizer_dir)
            assert path == schema_file.resolve()

    def test_resolve_nonexistent_schema_error(self):
        """Test that resolving non-existent schema raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            with pytest.raises(SchemaNotFoundError, match="Schema not found"):
                resolve_schema("iglu:com.google/gmail_email/jsonschema/1-0-0", canonizer_dir)

    def test_resolve_nonexistent_schema_no_error(self):
        """Test resolving non-existent schema without error when must_exist=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            path = resolve_schema(
                "iglu:com.google/gmail_email/jsonschema/1-0-0",
                canonizer_dir,
                must_exist=False,
            )
            assert "com.google" in str(path)
            assert "1-0-0.json" in str(path)

    def test_resolve_schema_auto_detect_root(self):
        """Test resolving schema with auto-detected root."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            # Create schema
            schema_dir = canonizer_dir / "registry" / "schemas" / "org.test" / "myschema" / "jsonschema"
            schema_dir.mkdir(parents=True)
            (schema_dir / "1-0-0.json").write_text("{}")

            # Change to that directory
            original_cwd = os.getcwd()
            try:
                os.chdir(base)
                path = resolve_schema("iglu:org.test/myschema/jsonschema/1-0-0")
                assert path.exists()
            finally:
                os.chdir(original_cwd)


class TestResolveTransform:
    """Tests for resolve_transform function."""

    def test_resolve_existing_transform(self):
        """Test resolving an existing transform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            # Create transform files
            transform_dir = canonizer_dir / "registry" / "transforms" / "email" / "gmail_to_jmap_lite" / "1.0.0"
            transform_dir.mkdir(parents=True)
            meta_file = transform_dir / "spec.meta.yaml"
            meta_file.write_text("id: email/gmail_to_jmap_lite")
            (transform_dir / "spec.jsonata").write_text("{}")

            path = resolve_transform("email/gmail_to_jmap_lite@1.0.0", canonizer_dir)
            assert path == meta_file.resolve()

    def test_resolve_nonexistent_transform_error(self):
        """Test that resolving non-existent transform raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            with pytest.raises(TransformNotFoundError, match="Transform not found"):
                resolve_transform("email/gmail_to_jmap_lite@1.0.0", canonizer_dir)

    def test_resolve_nonexistent_transform_no_error(self):
        """Test resolving non-existent transform without error when must_exist=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            path = resolve_transform(
                "email/gmail_to_jmap_lite@1.0.0",
                canonizer_dir,
                must_exist=False,
            )
            assert "gmail_to_jmap_lite" in str(path)
            assert "spec.meta.yaml" in str(path)


class TestResolveJsonata:
    """Tests for resolve_jsonata function."""

    def test_resolve_existing_jsonata(self):
        """Test resolving an existing JSONata file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            # Create transform files
            transform_dir = canonizer_dir / "registry" / "transforms" / "forms" / "google_to_canonical" / "1.0.0"
            transform_dir.mkdir(parents=True)
            (transform_dir / "spec.meta.yaml").write_text("id: forms/google_to_canonical")
            jsonata_file = transform_dir / "spec.jsonata"
            jsonata_file.write_text('{"output": input}')

            path = resolve_jsonata("forms/google_to_canonical@1.0.0", canonizer_dir)
            assert path == jsonata_file.resolve()

    def test_resolve_nonexistent_jsonata_error(self):
        """Test that resolving non-existent JSONata raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            with pytest.raises(TransformNotFoundError, match="JSONata not found"):
                resolve_jsonata("forms/google_to_canonical@1.0.0", canonizer_dir)


class TestRefToPath:
    """Tests for reference to path conversion functions."""

    def test_schema_ref_to_path(self):
        """Test converting schema reference to path."""
        path = schema_ref_to_path("iglu:com.google/gmail_email/jsonschema/1-0-0")
        assert path == "schemas/com.google/gmail_email/jsonschema/1-0-0.json"

    def test_transform_ref_to_path(self):
        """Test converting transform reference to path."""
        path = transform_ref_to_path("email/gmail_to_jmap_lite@1.0.0")
        assert path == "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"

    def test_nested_transform_ref_to_path(self):
        """Test converting nested transform reference to path."""
        path = transform_ref_to_path("crm/salesforce/contact@2.0.0")
        assert path == "transforms/crm/salesforce/contact/2.0.0/spec.meta.yaml"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_invalid_schema_ref_empty(self):
        """Test empty schema reference."""
        with pytest.raises(InvalidReferenceError):
            parse_iglu_ref("")

    def test_invalid_transform_ref_empty(self):
        """Test empty transform reference."""
        with pytest.raises(InvalidReferenceError):
            parse_transform_ref("")

    def test_schema_error_message_includes_path(self):
        """Test that schema error message includes expected path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            with pytest.raises(SchemaNotFoundError) as exc_info:
                resolve_schema("iglu:com.google/test/jsonschema/1-0-0", canonizer_dir)

            assert "Expected at:" in str(exc_info.value)
            assert "canonizer import" in str(exc_info.value)

    def test_transform_error_message_includes_path(self):
        """Test that transform error message includes expected path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            canonizer_dir = create_canonizer_dir(base)

            with pytest.raises(TransformNotFoundError) as exc_info:
                resolve_transform("test/transform@1.0.0", canonizer_dir)

            assert "Expected at:" in str(exc_info.value)
            assert "canonizer import" in str(exc_info.value)
