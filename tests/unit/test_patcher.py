"""Tests for transform patcher."""


from canonizer.core.differ import ChangeType, SchemaChange, SchemaDiff
from canonizer.core.patcher import TransformPatcher


def test_apply_add_to_simple_object():
    """Test applying ADD change to simple JSONata object."""
    jsonata = """{
  "name": name,
  "email": email
}"""

    change = SchemaChange(
        change_type=ChangeType.ADD,
        path="phone",
        old_value=None,
        new_value={"type": "string"},
        description="Added field 'phone'",
        auto_patchable=True,
    )

    result = TransformPatcher._apply_add(jsonata, change)

    assert result is not None
    assert '"phone": null' in result
    assert result.count("{") == result.count("}")  # Balanced braces


def test_apply_add_to_empty_object():
    """Test applying ADD to empty JSONata object."""
    jsonata = "{}"

    change = SchemaChange(
        change_type=ChangeType.ADD,
        path="email",
        old_value=None,
        new_value={"type": "string"},
        description="Added field 'email'",
        auto_patchable=True,
    )

    result = TransformPatcher._apply_add(jsonata, change)

    assert result is not None
    assert '"email": null' in result


def test_apply_add_to_complex_jsonata_fails():
    """Test that ADD to complex JSONata (not simple object) fails safely."""
    # Complex JSONata (array mapping)
    jsonata = """emails[0].{
  "address": address,
  "type": type
}"""

    change = SchemaChange(
        change_type=ChangeType.ADD,
        path="phone",
        old_value=None,
        new_value={"type": "string"},
        description="Added field 'phone'",
        auto_patchable=True,
    )

    result = TransformPatcher._apply_add(jsonata, change)

    # Should fail safely for complex structures
    assert result is None


def test_apply_rename():
    """Test applying RENAME change."""
    jsonata = """{
  "user_name": username,
  "email": email
}"""

    change = SchemaChange(
        change_type=ChangeType.RENAME,
        path="user_name→username",
        old_value={"type": "string"},
        new_value={"type": "string"},
        description="Renamed field",
        auto_patchable=True,
    )

    result = TransformPatcher._apply_rename(jsonata, change)

    assert result is not None
    assert '"username":' in result
    assert '"user_name"' not in result


def test_apply_rename_no_match():
    """Test RENAME when field not found returns None."""
    jsonata = """{
  "email": email
}"""

    change = SchemaChange(
        change_type=ChangeType.RENAME,
        path="user_name→username",
        old_value={"type": "string"},
        new_value={"type": "string"},
        description="Renamed field",
        auto_patchable=True,
    )

    result = TransformPatcher._apply_rename(jsonata, change)

    assert result is None


def test_bump_version():
    """Test version bumping (MINOR/REVISION)."""
    from datetime import UTC, datetime

    from canonizer.registry.transform_meta import Checksum, Provenance, TransformMeta

    meta = TransformMeta(
        id="test",
        version="1.0.0",
        engine="jsonata",
        runtime="python",
        from_schema="iglu:com.example/test/jsonschema/1-0-0",
        to_schema="iglu:com.example/test/jsonschema/1-0-0",
        spec_path="test.jsonata",
        tests=[],
        checksum=Checksum(jsonata_sha256="0" * 64),
        provenance=Provenance(
            author="Test <test@example.com>",
            created_utc=datetime.now(UTC),
        ),
        status="stable",
    )

    updated = TransformPatcher._bump_version(meta)

    assert updated.version == "1.1.0"


def test_bump_version_resets_addition():
    """Test that bumping REVISION resets ADDITION to 0."""
    from datetime import UTC, datetime

    from canonizer.registry.transform_meta import Checksum, Provenance, TransformMeta

    meta = TransformMeta(
        id="test",
        version="1.2.5",
        engine="jsonata",
        runtime="python",
        from_schema="iglu:com.example/test/jsonschema/1-0-0",
        to_schema="iglu:com.example/test/jsonschema/1-0-0",
        spec_path="test.jsonata",
        tests=[],
        checksum=Checksum(jsonata_sha256="0" * 64),
        provenance=Provenance(
            author="Test <test@example.com>",
            created_utc=datetime.now(UTC),
        ),
        status="stable",
    )

    updated = TransformPatcher._bump_version(meta)

    assert updated.version == "1.3.0"


def test_patch_transform_with_add(tmp_path):
    """Test patching a transform with ADD change."""
    # Create test transform files
    jsonata_path = tmp_path / "test.jsonata"
    jsonata_path.write_text('{\n  "name": name\n}')

    meta_path = tmp_path / "test.meta.yaml"
    meta_content = """id: test_transform
version: 1.0.0
engine: jsonata
runtime: python
from_schema: iglu:com.example/test/jsonschema/1-0-0
to_schema: iglu:com.example/test/jsonschema/1-0-0
spec_path: test.jsonata
tests: []
checksum:
  jsonata_sha256: 2af4e406be6f667342013c68001bc2d5850e90293acc6f0890b1889a46f8b7d9
provenance:
  author: "Test <test@example.com>"
  created_utc: "2025-11-10T00:00:00Z"
status: stable
"""
    meta_path.write_text(meta_content)

    # Create schema diff with ADD change
    diff = SchemaDiff(
        from_schema_path="test1.json",
        to_schema_path="test2.json",
        changes=[
            SchemaChange(
                change_type=ChangeType.ADD,
                path="email",
                old_value=None,
                new_value={"type": "string"},
                description="Added field 'email'",
                auto_patchable=True,
            )
        ],
        auto_patchable_count=1,
        manual_review_count=0,
    )

    result = TransformPatcher.patch_transform(meta_path, diff)

    assert result.success is True
    assert result.updated_jsonata is not None
    assert '"email": null' in result.updated_jsonata
    assert len(result.applied_changes) == 1
    assert len(result.skipped_changes) == 0
    assert result.updated_meta.version == "1.1.0"


def test_patch_transform_with_rename(tmp_path):
    """Test patching a transform with RENAME change."""
    jsonata_path = tmp_path / "test.jsonata"
    jsonata_path.write_text('{\n  "user_name": username\n}')

    meta_path = tmp_path / "test.meta.yaml"
    meta_content = """id: test_transform
version: 1.0.0
engine: jsonata
runtime: python
from_schema: iglu:com.example/test/jsonschema/1-0-0
to_schema: iglu:com.example/test/jsonschema/1-0-0
spec_path: test.jsonata
tests: []
checksum:
  jsonata_sha256: 1d59ad4e640421855dd69fd5f8afee42dd3da09ee01efd02b9b01937bd86599e
provenance:
  author: "Test <test@example.com>"
  created_utc: "2025-11-10T00:00:00Z"
status: stable
"""
    meta_path.write_text(meta_content)

    diff = SchemaDiff(
        from_schema_path="test1.json",
        to_schema_path="test2.json",
        changes=[
            SchemaChange(
                change_type=ChangeType.RENAME,
                path="user_name→username",
                old_value={"type": "string"},
                new_value={"type": "string"},
                description="Renamed field",
                auto_patchable=True,
            )
        ],
        auto_patchable_count=1,
        manual_review_count=0,
    )

    result = TransformPatcher.patch_transform(meta_path, diff)

    assert result.success is True
    assert result.updated_jsonata is not None
    assert '"username":' in result.updated_jsonata
    assert '"user_name"' not in result.updated_jsonata


def test_patch_transform_skips_non_patchable(tmp_path):
    """Test that non-patchable changes are skipped."""
    jsonata_path = tmp_path / "test.jsonata"
    jsonata_path.write_text('{\n  "name": name\n}')

    meta_path = tmp_path / "test.meta.yaml"
    meta_content = """id: test_transform
version: 1.0.0
engine: jsonata
runtime: python
from_schema: iglu:com.example/test/jsonschema/1-0-0
to_schema: iglu:com.example/test/jsonschema/1-0-0
spec_path: test.jsonata
tests: []
checksum:
  jsonata_sha256: 2af4e406be6f667342013c68001bc2d5850e90293acc6f0890b1889a46f8b7d9
provenance:
  author: "Test <test@example.com>"
  created_utc: "2025-11-10T00:00:00Z"
status: stable
"""
    meta_path.write_text(meta_content)

    diff = SchemaDiff(
        from_schema_path="test1.json",
        to_schema_path="test2.json",
        changes=[
            SchemaChange(
                change_type=ChangeType.TYPE_CHANGE,
                path="age",
                old_value={"type": "string"},
                new_value={"type": "number"},
                description="Type changed",
                auto_patchable=False,
            )
        ],
        auto_patchable_count=0,
        manual_review_count=1,
    )

    result = TransformPatcher.patch_transform(meta_path, diff)

    assert result.success is False
    assert result.error == "No auto-patchable changes found"
    assert len(result.skipped_changes) == 1
