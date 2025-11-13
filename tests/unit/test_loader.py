"""Unit tests for TransformLoader."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from canonizer.registry.loader import TransformLoader
from canonizer.registry.transform_meta import TransformMeta


def test_load_transform_success(tmp_path: Path):
    """Test successfully loading a transform."""
    # Create .jsonata file
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_content = '{"message_id": payload.id, "subject": payload.subject}'
    jsonata_file.write_text(jsonata_content)

    # Compute checksum
    checksum = hashlib.sha256(jsonata_content.encode()).hexdigest()

    # Create .meta.yaml file
    meta_data = {
        "id": "test_transform",
        "version": "1.0.0",
        "engine": "jsonata",
        "runtime": "node",
        "from_schema": "iglu:com.google/test/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/test/jsonschema/1-0-0",
        "spec_path": "test.jsonata",
        "checksum": {
            "jsonata_sha256": checksum,
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
        "status": "stable",
    }

    meta_file = tmp_path / "test.meta.yaml"
    with open(meta_file, "w") as f:
        yaml.dump(meta_data, f)

    # Load transform
    transform = TransformLoader.load(meta_file)

    assert transform.meta.id == "test_transform"
    assert transform.meta.version == "1.0.0"
    assert transform.jsonata == jsonata_content
    assert transform.meta_path == meta_file
    assert transform.jsonata_path == jsonata_file


def test_load_transform_missing_meta_file(tmp_path: Path):
    """Test loading transform with missing .meta.yaml file."""
    meta_file = tmp_path / "nonexistent.meta.yaml"

    with pytest.raises(FileNotFoundError) as exc_info:
        TransformLoader.load(meta_file)

    assert "Transform metadata not found" in str(exc_info.value)


def test_load_transform_missing_jsonata_file(tmp_path: Path):
    """Test loading transform with missing .jsonata file."""
    # Create .meta.yaml but not .jsonata
    meta_data = {
        "id": "test_transform",
        "version": "1.0.0",
        "from_schema": "iglu:com.google/test/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/test/jsonschema/1-0-0",
        "spec_path": "missing.jsonata",
        "checksum": {
            "jsonata_sha256": "a" * 64,
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

    meta_file = tmp_path / "test.meta.yaml"
    with open(meta_file, "w") as f:
        yaml.dump(meta_data, f)

    with pytest.raises(FileNotFoundError) as exc_info:
        TransformLoader.load(meta_file)

    assert "Transform file not found" in str(exc_info.value)


def test_load_transform_checksum_mismatch(tmp_path: Path):
    """Test loading transform with mismatched checksum."""
    # Create .jsonata file
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_file.write_text('{"original": "content"}')

    # Create .meta.yaml with wrong checksum
    meta_data = {
        "id": "test_transform",
        "version": "1.0.0",
        "from_schema": "iglu:com.google/test/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/test/jsonschema/1-0-0",
        "spec_path": "test.jsonata",
        "checksum": {
            "jsonata_sha256": "a" * 64,  # Wrong checksum
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

    meta_file = tmp_path / "test.meta.yaml"
    with open(meta_file, "w") as f:
        yaml.dump(meta_data, f)

    with pytest.raises(ValueError) as exc_info:
        TransformLoader.load(meta_file)

    assert "Checksum verification failed" in str(exc_info.value)


def test_discover_transforms(tmp_path: Path):
    """Test discovering transforms in a directory tree."""
    # Create directory structure
    email_dir = tmp_path / "transforms" / "email"
    email_dir.mkdir(parents=True)

    calendar_dir = tmp_path / "transforms" / "calendar"
    calendar_dir.mkdir(parents=True)

    # Create some .meta.yaml files
    (email_dir / "gmail.meta.yaml").touch()
    (email_dir / "exchange.meta.yaml").touch()
    (calendar_dir / "gcal.meta.yaml").touch()

    # Discover all transforms
    found = TransformLoader.discover(tmp_path / "transforms")

    assert len(found) == 3
    assert all(p.name.endswith(".meta.yaml") for p in found)


def test_discover_nonexistent_directory():
    """Test discovering transforms in nonexistent directory."""
    with pytest.raises(FileNotFoundError):
        TransformLoader.discover("/nonexistent/path")


def test_load_transform_with_test_fixtures(tmp_path: Path):
    """Test loading transform with test fixtures."""
    # Create .jsonata file
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_content = '{"id": payload.id}'
    jsonata_file.write_text(jsonata_content)

    checksum = hashlib.sha256(jsonata_content.encode()).hexdigest()

    # Create .meta.yaml with tests
    meta_data = {
        "id": "test_transform",
        "version": "1.0.0",
        "from_schema": "iglu:com.google/test/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/test/jsonschema/1-0-0",
        "spec_path": "test.jsonata",
        "tests": [
            {
                "input": "../../tests/golden/test/input.json",
                "expect": "../../tests/golden/test/output.json",
            }
        ],
        "checksum": {
            "jsonata_sha256": checksum,
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

    meta_file = tmp_path / "test.meta.yaml"
    with open(meta_file, "w") as f:
        yaml.dump(meta_data, f)

    transform = TransformLoader.load(meta_file)

    assert len(transform.meta.tests) == 1
    assert transform.meta.tests[0].input == "../../tests/golden/test/input.json"
