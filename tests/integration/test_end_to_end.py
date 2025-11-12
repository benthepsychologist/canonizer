"""Integration tests for end-to-end transform pipeline."""

from pathlib import Path

import pytest

from canonizer.core.runtime import TransformRuntime


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def schemas_dir(fixtures_dir):
    """Return path to test schemas directory."""
    return fixtures_dir / "schemas"


@pytest.fixture
def transforms_dir(fixtures_dir):
    """Return path to test transforms directory."""
    return fixtures_dir / "transforms"


def test_simple_transform_end_to_end_python(schemas_dir, transforms_dir):
    """Test simple transform using Python JSONata runtime."""
    runtime = TransformRuntime(schemas_dir=schemas_dir)

    input_data = {"message": "Hello, World!", "count": 42}

    transform_meta = transforms_dir / "simple_transform.meta.yaml"

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Check output
    assert result.data["text"] == "Hello, World!"
    assert result.data["number"] == 42
    assert "processed_at" in result.data

    # Check runtime metadata
    assert result.runtime == "python"
    assert result.execution_time_ms > 0


def test_transform_without_validation(schemas_dir, transforms_dir):
    """Test transform without input/output validation."""
    runtime = TransformRuntime(schemas_dir=schemas_dir)

    input_data = {"message": "Test", "count": 10}

    transform_meta = transforms_dir / "simple_transform.meta.yaml"

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=False,
        validate_output=False,
    )

    assert result.data["text"] == "Test"
    assert result.data["number"] == 10


def test_transform_with_invalid_input(schemas_dir, transforms_dir):
    """Test transform fails with invalid input when validation enabled."""
    from canonizer.core.validator import ValidationError

    runtime = TransformRuntime(schemas_dir=schemas_dir)

    # Invalid input (missing required 'message' field)
    input_data = {"count": 42}

    transform_meta = transforms_dir / "simple_transform.meta.yaml"

    with pytest.raises(ValidationError):
        runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=True,
            validate_output=True,
        )


def test_transform_checksum_verification(schemas_dir, transforms_dir, tmp_path):
    """Test that checksum verification prevents tampered transforms."""
    import shutil

    # Copy transform to temp directory
    temp_meta = tmp_path / "simple_transform.meta.yaml"
    temp_jsonata = tmp_path / "simple_transform.jsonata"

    shutil.copy(transforms_dir / "simple_transform.meta.yaml", temp_meta)
    shutil.copy(transforms_dir / "simple_transform.jsonata", temp_jsonata)

    # Tamper with .jsonata file
    temp_jsonata.write_text('{"malicious": "code"}')

    runtime = TransformRuntime(schemas_dir=schemas_dir)
    input_data = {"message": "Test"}

    with pytest.raises(ValueError) as exc_info:
        runtime.execute(
            transform_meta_path=temp_meta,
            input_data=input_data,
        )

    assert "Checksum verification failed" in str(exc_info.value)


def test_execute_safe_success(schemas_dir, transforms_dir):
    """Test execute_safe returns result on success."""
    runtime = TransformRuntime(schemas_dir=schemas_dir)

    input_data = {"message": "Hello"}
    transform_meta = transforms_dir / "simple_transform.meta.yaml"

    result, error = runtime.execute_safe(
        transform_meta_path=transform_meta,
        input_data=input_data,
    )

    assert result is not None
    assert error is None
    assert result.data["text"] == "Hello"


def test_execute_safe_failure(schemas_dir, transforms_dir):
    """Test execute_safe returns error on failure."""
    runtime = TransformRuntime(schemas_dir=schemas_dir)

    # Invalid input
    input_data = {"count": 42}  # Missing required 'message'
    transform_meta = transforms_dir / "simple_transform.meta.yaml"

    result, error = runtime.execute_safe(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
    )

    assert result is None
    assert error is not None
    assert isinstance(error, Exception)
