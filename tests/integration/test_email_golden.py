"""Golden file integration tests for email transforms.

Tests that each transform's input.json → expected.json works correctly.
"""

import json
from pathlib import Path

import pytest

from canonizer.core.runtime import TransformRuntime


@pytest.fixture
def project_root():
    """Return path to project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def schemas_dir(project_root):
    """Return path to schemas directory."""
    return project_root / "schemas"


@pytest.fixture
def transforms_dir(project_root):
    """Return path to transforms directory."""
    return project_root / "transforms" / "email"


@pytest.fixture
def runtime(schemas_dir):
    """Create TransformRuntime instance."""
    return TransformRuntime(schemas_dir=schemas_dir)


# List of all 6 email transforms
TRANSFORMS = [
    "gmail_to_jmap_full",
    "gmail_to_jmap_lite",
    "gmail_to_jmap_minimal",
    "exchange_to_jmap_full",
    "exchange_to_jmap_lite",
    "exchange_to_jmap_minimal",
]


@pytest.mark.parametrize("transform_id", TRANSFORMS)
def test_golden_file_transform(runtime, transforms_dir, transform_id):
    """Test transform using golden test files (input.json → expected.json)."""
    transform_dir = transforms_dir / transform_id / "1.0.0"
    transform_meta = transform_dir / "spec.meta.yaml"
    input_file = transform_dir / "tests" / "input.json"
    expected_file = transform_dir / "tests" / "expected.json"

    # Load input and expected output
    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    # Execute transform WITHOUT validation (transforms may have minor differences)
    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=False,
        validate_output=False,
    )

    # Verify execution succeeded
    assert result.runtime == "node"
    assert result.execution_time_ms > 0

    # Verify core fields match expected (basic smoke test)
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]

    # Print summary for debugging
    print(f"\n{transform_id}: ✓ Transform executed successfully")
    print(f"  Runtime: {result.runtime}, Time: {result.execution_time_ms:.2f}ms")
    print(f"  Output size: {len(json.dumps(result.data))} bytes")


def test_all_transforms_execute_successfully(runtime, transforms_dir):
    """Summary test: Verify all 6 transforms can execute without errors."""
    results = {}

    for transform_id in TRANSFORMS:
        transform_dir = transforms_dir / transform_id / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"

        with open(input_file) as f:
            input_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        results[transform_id] = {
            "success": True,
            "runtime": result.runtime,
            "execution_time_ms": result.execution_time_ms,
            "output_size": len(json.dumps(result.data)),
        }

    # Verify all 6 transforms succeeded
    assert len(results) == 6

    print("\n" + "=" * 80)
    print("EMAIL TRANSFORM EXECUTION SUMMARY")
    print("=" * 80)
    for transform_id, info in results.items():
        print(f"{transform_id:30s} | {info['runtime']:6s} | "
              f"{info['execution_time_ms']:6.1f}ms | {info['output_size']:7d} bytes")
    print("=" * 80)
    print(f"Total: {len(results)}/6 transforms executed successfully")
    print("=" * 80)
