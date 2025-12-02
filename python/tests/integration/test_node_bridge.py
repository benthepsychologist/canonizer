"""Integration tests for Python → Node.js bridge.

These tests verify that the Python wrapper correctly calls
the Node.js canonizer-core CLI and handles results.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add python package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from canonizer import TransformError, canonicalize, run_batch, validate_payload

# Registry root is the main canonizer repo root
REGISTRY_ROOT = Path(__file__).parent.parent.parent.parent


class TestCanonicalizeIntegration:
    """Integration tests for canonicalize function."""

    def test_gmail_to_jmap_lite(self):
        """Test Gmail to JMAP Lite transform via Node bridge."""
        # Load test input
        input_path = REGISTRY_ROOT / "transforms/email/gmail_to_jmap_lite/1.0.0/tests/input.json"
        if not input_path.exists():
            pytest.skip("Test input file not found")

        with open(input_path) as f:
            input_data = json.load(f)

        result = canonicalize(
            input_data,
            transform_id="email/gmail_to_jmap_lite@1.0.0",
            registry_root=str(REGISTRY_ROOT),
        )

        # Check basic structure
        assert isinstance(result, dict)
        assert "id" in result
        assert "from" in result
        assert "subject" in result

    def test_gmail_to_jmap_full(self):
        """Test Gmail to JMAP Full transform via Node bridge."""
        input_path = REGISTRY_ROOT / "transforms/email/gmail_to_jmap_full/1.0.0/tests/input.json"
        if not input_path.exists():
            pytest.skip("Test input file not found")

        with open(input_path) as f:
            input_data = json.load(f)

        result = canonicalize(
            input_data,
            transform_id="email/gmail_to_jmap_full@1.0.0",
            registry_root=str(REGISTRY_ROOT),
        )

        assert isinstance(result, dict)
        assert "id" in result
        assert "bodyStructure" in result or "textBody" in result

    def test_invalid_transform_id(self):
        """Test error handling for non-existent transform."""
        with pytest.raises(TransformError) as exc_info:
            canonicalize(
                {"test": "data"},
                transform_id="nonexistent/transform@1.0.0",
                registry_root=str(REGISTRY_ROOT),
            )

        assert "nonexistent" in str(exc_info.value) or exc_info.value.stderr

    def test_validation_disabled(self):
        """Test running transform with validation disabled."""
        input_path = REGISTRY_ROOT / "transforms/email/gmail_to_jmap_lite/1.0.0/tests/input.json"
        if not input_path.exists():
            pytest.skip("Test input file not found")

        with open(input_path) as f:
            input_data = json.load(f)

        # Should work with validation disabled
        result = canonicalize(
            input_data,
            transform_id="email/gmail_to_jmap_lite@1.0.0",
            validate=False,
            registry_root=str(REGISTRY_ROOT),
        )

        assert isinstance(result, dict)


class TestValidatePayloadIntegration:
    """Integration tests for validate_payload function."""

    def test_valid_gmail_message(self):
        """Test validation of valid Gmail message."""
        input_path = REGISTRY_ROOT / "transforms/email/gmail_to_jmap_lite/1.0.0/tests/input.json"
        if not input_path.exists():
            pytest.skip("Test input file not found")

        with open(input_path) as f:
            input_data = json.load(f)

        is_valid, errors = validate_payload(
            input_data,
            "iglu:com.google/gmail_email/jsonschema/1-0-0",
            registry_root=str(REGISTRY_ROOT),
        )

        assert is_valid is True
        assert errors == []

    def test_invalid_payload(self):
        """Test validation of invalid payload."""
        is_valid, errors = validate_payload(
            {"invalid": "data"},
            "iglu:com.google/gmail_email/jsonschema/1-0-0",
            registry_root=str(REGISTRY_ROOT),
        )

        assert is_valid is False
        assert len(errors) > 0


class TestRunBatchIntegration:
    """Integration tests for run_batch function."""

    def test_batch_transform(self):
        """Test batch transformation."""
        input_path = REGISTRY_ROOT / "transforms/email/gmail_to_jmap_lite/1.0.0/tests/input.json"
        if not input_path.exists():
            pytest.skip("Test input file not found")

        with open(input_path) as f:
            input_data = json.load(f)

        # Transform same document twice
        results = run_batch(
            [input_data, input_data],
            transform_id="email/gmail_to_jmap_lite@1.0.0",
            registry_root=str(REGISTRY_ROOT),
        )

        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)
        assert results[0]["id"] == results[1]["id"]


class TestNodeBinaryResolution:
    """Test that Node binary is correctly resolved."""

    def test_binary_exists(self):
        """Test that canonizer-core binary can be found."""
        from canonizer.api import _get_canonizer_core_bin

        try:
            bin_path = _get_canonizer_core_bin()
            assert bin_path is not None
            assert os.path.exists(bin_path) or bin_path == "canonizer-core"
        except RuntimeError:
            pytest.skip("canonizer-core not installed")
