"""Tests for local registry configuration and lock file models."""

import json
import tempfile
from pathlib import Path

import pytest

from canonizer.local.config import (
    CANONIZER_DIR,
    CONFIG_FILENAME,
    LOCK_FILENAME,
    CanonizerConfig,
    RegistryConfig,
    RegistryMode,
)
from canonizer.local.lock import (
    LockFile,
    SchemaLock,
    TransformLock,
    compute_file_hash,
)


class TestRegistryConfig:
    """Tests for RegistryConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RegistryConfig()
        assert config.mode == RegistryMode.LOCAL
        assert config.root == "registry"

    def test_custom_root(self):
        """Test custom registry root path."""
        config = RegistryConfig(root="custom/registry/path")
        assert config.root == "custom/registry/path"

    def test_rejects_absolute_path(self):
        """Test that absolute paths are rejected."""
        with pytest.raises(ValueError, match="relative path"):
            RegistryConfig(root="/absolute/path")

    def test_rejects_parent_traversal(self):
        """Test that parent directory traversal is rejected."""
        with pytest.raises(ValueError, match="relative path"):
            RegistryConfig(root="../escape/path")

        with pytest.raises(ValueError, match="relative path"):
            RegistryConfig(root="some/../../../escape")


class TestCanonizerConfig:
    """Tests for CanonizerConfig model."""

    def test_default_config(self):
        """Test default configuration."""
        config = CanonizerConfig.default()
        assert config.registry.mode == RegistryMode.LOCAL
        assert config.registry.root == "registry"

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / CONFIG_FILENAME

            # Create and save config
            config = CanonizerConfig.default()
            config.save(config_path)

            # Verify file exists
            assert config_path.exists()

            # Load and verify
            loaded = CanonizerConfig.load(config_path)
            assert loaded.registry.mode == config.registry.mode
            assert loaded.registry.root == config.registry.root

    def test_load_missing_file(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            CanonizerConfig.load(Path("/nonexistent/config.yaml"))

    def test_get_registry_path(self):
        """Test getting absolute registry path."""
        config = CanonizerConfig()
        canonizer_root = Path("/project/.canonizer")
        registry_path = config.get_registry_path(canonizer_root)

        assert registry_path == Path("/project/.canonizer/registry").resolve()

    def test_custom_registry_config(self):
        """Test custom registry configuration."""
        config = CanonizerConfig(
            registry=RegistryConfig(
                mode=RegistryMode.LOCAL,
                root="my/custom/registry",
            )
        )
        assert config.registry.root == "my/custom/registry"


class TestSchemaLock:
    """Tests for SchemaLock model."""

    def test_valid_schema_lock(self):
        """Test creating a valid schema lock entry."""
        lock = SchemaLock(
            path="schemas/com.google/gmail_email/jsonschema/1-0-0.json",
            hash="sha256:" + "a" * 64,
        )
        assert lock.path == "schemas/com.google/gmail_email/jsonschema/1-0-0.json"
        assert lock.hash.startswith("sha256:")

    def test_invalid_hash_prefix(self):
        """Test that invalid hash prefix is rejected."""
        with pytest.raises(ValueError, match="sha256:"):
            SchemaLock(
                path="test.json",
                hash="md5:" + "a" * 32,
            )

    def test_invalid_hash_length(self):
        """Test that invalid hash length is rejected."""
        with pytest.raises(ValueError, match="64 hex characters"):
            SchemaLock(
                path="test.json",
                hash="sha256:" + "a" * 32,  # Too short
            )

    def test_invalid_hash_chars(self):
        """Test that invalid hash characters are rejected."""
        with pytest.raises(ValueError, match="hexadecimal"):
            SchemaLock(
                path="test.json",
                hash="sha256:" + "g" * 64,  # 'g' is not hex
            )


class TestTransformLock:
    """Tests for TransformLock model."""

    def test_valid_transform_lock(self):
        """Test creating a valid transform lock entry."""
        lock = TransformLock(
            path="transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
            hash="sha256:" + "b" * 64,
        )
        assert "gmail_to_jmap_lite" in lock.path
        assert lock.hash.startswith("sha256:")


class TestLockFile:
    """Tests for LockFile model."""

    def test_empty_lock_file(self):
        """Test creating an empty lock file."""
        lock = LockFile.empty()
        assert lock.version == "1"
        assert lock.schemas == {}
        assert lock.transforms == {}
        assert lock.updated_at is not None

    def test_save_and_load(self):
        """Test saving and loading lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / LOCK_FILENAME

            # Create and save lock file
            lock = LockFile.empty()
            lock.add_schema(
                "iglu:com.google/gmail_email/jsonschema/1-0-0",
                "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
                b"test schema content",
            )
            lock.save(lock_path)

            # Verify file exists
            assert lock_path.exists()

            # Load and verify
            loaded = LockFile.load(lock_path)
            assert "iglu:com.google/gmail_email/jsonschema/1-0-0" in loaded.schemas
            assert loaded.schemas["iglu:com.google/gmail_email/jsonschema/1-0-0"].path == (
                "schemas/com.google/gmail_email/jsonschema/1-0-0.json"
            )

    def test_add_schema(self):
        """Test adding a schema entry."""
        lock = LockFile.empty()
        content = b'{"type": "object"}'

        lock.add_schema(
            "iglu:org.canonical/email/jsonschema/1-0-0",
            "schemas/org.canonical/email/jsonschema/1-0-0.json",
            content,
        )

        assert "iglu:org.canonical/email/jsonschema/1-0-0" in lock.schemas
        entry = lock.schemas["iglu:org.canonical/email/jsonschema/1-0-0"]
        assert entry.path == "schemas/org.canonical/email/jsonschema/1-0-0.json"
        assert entry.hash.startswith("sha256:")

    def test_add_transform(self):
        """Test adding a transform entry."""
        lock = LockFile.empty()
        jsonata_content = b'{"id": source.id}'

        lock.add_transform(
            "email/gmail_to_jmap_lite@1.0.0",
            "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
            jsonata_content,
        )

        assert "email/gmail_to_jmap_lite@1.0.0" in lock.transforms
        entry = lock.transforms["email/gmail_to_jmap_lite@1.0.0"]
        assert "gmail_to_jmap_lite" in entry.path
        assert entry.hash.startswith("sha256:")

    def test_get_schema_path(self):
        """Test getting schema path by reference."""
        lock = LockFile.empty()
        lock.add_schema(
            "iglu:com.google/forms/jsonschema/1-0-0",
            "schemas/com.google/forms/jsonschema/1-0-0.json",
            b"content",
        )

        path = lock.get_schema_path("iglu:com.google/forms/jsonschema/1-0-0")
        assert path == "schemas/com.google/forms/jsonschema/1-0-0.json"

        # Non-existent schema
        assert lock.get_schema_path("iglu:nonexistent/schema/1-0-0") is None

    def test_get_transform_path(self):
        """Test getting transform path by reference."""
        lock = LockFile.empty()
        lock.add_transform(
            "forms/google_to_canonical@1.0.0",
            "transforms/forms/google_to_canonical/1.0.0/spec.meta.yaml",
            b"jsonata content",
        )

        path = lock.get_transform_path("forms/google_to_canonical@1.0.0")
        assert path == "transforms/forms/google_to_canonical/1.0.0/spec.meta.yaml"

        # Non-existent transform
        assert lock.get_transform_path("nonexistent/transform@1.0.0") is None

    def test_verify_schema(self):
        """Test verifying schema content hash."""
        lock = LockFile.empty()
        content = b'{"type": "object", "properties": {}}'

        lock.add_schema(
            "iglu:test/schema/jsonschema/1-0-0",
            "schemas/test/schema/jsonschema/1-0-0.json",
            content,
        )

        # Correct content should verify
        assert lock.verify_schema("iglu:test/schema/jsonschema/1-0-0", content)

        # Modified content should fail
        assert not lock.verify_schema("iglu:test/schema/jsonschema/1-0-0", b"modified")

        # Non-existent schema should fail
        assert not lock.verify_schema("iglu:nonexistent/1-0-0", content)

    def test_verify_transform(self):
        """Test verifying transform content hash."""
        lock = LockFile.empty()
        jsonata_content = b'{"output": input.field}'

        lock.add_transform(
            "test/transform@1.0.0",
            "transforms/test/transform/1.0.0/spec.meta.yaml",
            jsonata_content,
        )

        # Correct content should verify
        assert lock.verify_transform("test/transform@1.0.0", jsonata_content)

        # Modified content should fail
        assert not lock.verify_transform("test/transform@1.0.0", b"modified")

        # Non-existent transform should fail
        assert not lock.verify_transform("nonexistent@1.0.0", jsonata_content)

    def test_load_missing_file(self):
        """Test loading non-existent lock file."""
        with pytest.raises(FileNotFoundError):
            LockFile.load(Path("/nonexistent/lock.json"))


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_compute_hash(self):
        """Test computing file hash."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()

            hash_value = compute_file_hash(Path(f.name))
            assert hash_value.startswith("sha256:")
            assert len(hash_value) == 7 + 64  # "sha256:" + 64 hex chars

    def test_hash_consistency(self):
        """Test that same content produces same hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            content = b"identical content"
            file1.write_bytes(content)
            file2.write_bytes(content)

            assert compute_file_hash(file1) == compute_file_hash(file2)

    def test_hash_differs_for_different_content(self):
        """Test that different content produces different hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            file1.write_bytes(b"content one")
            file2.write_bytes(b"content two")

            assert compute_file_hash(file1) != compute_file_hash(file2)


class TestConstants:
    """Tests for module constants."""

    def test_constants_defined(self):
        """Test that constants are properly defined."""
        assert CANONIZER_DIR == ".canonizer"
        assert CONFIG_FILENAME == "config.yaml"
        assert LOCK_FILENAME == "lock.json"
