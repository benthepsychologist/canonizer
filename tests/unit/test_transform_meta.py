"""Unit tests for TransformMeta model."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from canonizer.registry.transform_meta import (
    Checksum,
    Provenance,
    TestFixture,
    TransformMeta,
)


def test_transform_meta_valid():
    """Test that a valid TransformMeta can be created."""
    meta = TransformMeta(
        id="email/gmail_to_canonical",
        version="1.0.0",
        engine="jsonata",
        runtime="python",
        from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
        to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
        spec_path="gmail_v1_to_canonical_v1.jsonata",
        checksum=Checksum(jsonata_sha256="a" * 64),
        provenance=Provenance(
            author="Ben Machina <ben@therapyai.com>",
            created_utc=datetime.now(UTC),
        ),
    )

    assert meta.id == "email/gmail_to_canonical"
    assert meta.version == "1.0.0"
    assert meta.engine == "jsonata"
    assert meta.runtime == "python"
    assert meta.status == "draft"  # default
    assert meta.provenance.author == "Ben Machina <ben@therapyai.com>"


def test_transform_meta_invalid_id():
    """Test that invalid IDs are rejected (uppercase, special chars)."""
    with pytest.raises(ValidationError) as exc_info:
        TransformMeta(
            id="Gmail-To-Canonical",  # Invalid: uppercase and hyphens
            version="1.0.0",
            from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
            to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
            spec_path="test.jsonata",
            checksum=Checksum(jsonata_sha256="a" * 64),
            provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
        )

    assert "id" in str(exc_info.value)


def test_transform_meta_invalid_version():
    """Test that invalid versions are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransformMeta(
            id="test_transform",
            version="v1.0",  # Invalid: not MAJOR.MINOR.PATCH
            from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
            to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
            spec_path="test.jsonata",
            checksum=Checksum(jsonata_sha256="a" * 64),
            provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
        )

    assert "version" in str(exc_info.value)


def test_transform_meta_invalid_schema_uri():
    """Test that invalid schema URIs are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransformMeta(
            id="test_transform",
            version="1.0.0",
            from_schema="not-an-iglu-uri",  # Invalid
            to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
            spec_path="test.jsonata",
            checksum=Checksum(jsonata_sha256="a" * 64),
            provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
        )

    assert "from_schema" in str(exc_info.value)


def test_transform_meta_invalid_spec_path():
    """Test that spec_path must be .jsonata file."""
    with pytest.raises(ValidationError) as exc_info:
        TransformMeta(
            id="test_transform",
            version="1.0.0",
            from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
            to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
            spec_path="transform.yaml",  # Invalid: not .jsonata
            checksum=Checksum(jsonata_sha256="a" * 64),
            provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
        )

    assert "spec_path" in str(exc_info.value)


def test_transform_meta_invalid_checksum_format():
    """Test that checksum must have correct format."""
    with pytest.raises(ValidationError) as exc_info:
        TransformMeta(
            id="test_transform",
            version="1.0.0",
            from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
            to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
            spec_path="test.jsonata",
            checksum=Checksum(jsonata_sha256="abc123"),  # Invalid: not 64 hex chars
            provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
        )

    assert "jsonata_sha256" in str(exc_info.value)


def test_transform_meta_with_tests():
    """Test TransformMeta with test fixtures."""
    meta = TransformMeta(
        id="test_transform",
        version="1.0.0",
        from_schema="iglu:com.google/gmail_email/jsonschema/1-0-0",
        to_schema="iglu:org.canonical/email/jsonschema/1-0-0",
        spec_path="test.jsonata",
        tests=[
            TestFixture(
                input="../../tests/golden/gmail_v1/input.json",
                expect="../../tests/golden/gmail_v1/output.json",
            )
        ],
        checksum=Checksum(jsonata_sha256="a" * 64),
        provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
    )

    assert len(meta.tests) == 1
    assert meta.tests[0].input.endswith("input.json")


def test_compute_checksum(tmp_path: Path):
    """Test checksum computation for a .jsonata file."""
    # Create a test .jsonata file
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_content = '{"message_id": payload.id}'
    jsonata_file.write_text(jsonata_content)

    # Compute expected checksum
    expected_checksum = hashlib.sha256(jsonata_content.encode()).hexdigest()

    # Create metadata
    meta_file = tmp_path / "test.meta.yaml"
    meta = TransformMeta(
        id="test_transform",
        version="1.0.0",
        from_schema="iglu:com.google/test/jsonschema/1-0-0",
        to_schema="iglu:org.canonical/test/jsonschema/1-0-0",
        spec_path="test.jsonata",
        checksum=Checksum(jsonata_sha256=expected_checksum),
        provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
    )

    computed = meta.compute_checksum(meta_file)
    assert computed == expected_checksum


def test_verify_checksum_valid(tmp_path: Path):
    """Test checksum verification with valid checksum."""
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_content = '{"message_id": payload.id}'
    jsonata_file.write_text(jsonata_content)

    expected_checksum = hashlib.sha256(jsonata_content.encode()).hexdigest()

    meta_file = tmp_path / "test.meta.yaml"
    meta = TransformMeta(
        id="test_transform",
        version="1.0.0",
        from_schema="iglu:com.google/test/jsonschema/1-0-0",
        to_schema="iglu:org.canonical/test/jsonschema/1-0-0",
        spec_path="test.jsonata",
        checksum=Checksum(jsonata_sha256=expected_checksum),
        provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
    )

    assert meta.verify_checksum(meta_file) is True


def test_verify_checksum_invalid(tmp_path: Path):
    """Test checksum verification with tampered file."""
    jsonata_file = tmp_path / "test.jsonata"
    jsonata_file.write_text('{"original": "content"}')

    # Wrong checksum
    meta_file = tmp_path / "test.meta.yaml"
    meta = TransformMeta(
        id="test_transform",
        version="1.0.0",
        from_schema="iglu:com.google/test/jsonschema/1-0-0",
        to_schema="iglu:org.canonical/test/jsonschema/1-0-0",
        spec_path="test.jsonata",
        checksum=Checksum(jsonata_sha256="a" * 64),  # Wrong checksum
        provenance=Provenance(author="Test <test@example.com>", created_utc=datetime.now(UTC)),
    )

    assert meta.verify_checksum(meta_file) is False


