"""Unit tests for canonizer.api module."""

import json
from pathlib import Path

import pytest

from canonizer import (
    canonicalize,
    canonicalize_email_from_exchange,
    canonicalize_email_from_gmail,
    canonicalize_form_response,
    run_batch,
)
from canonizer.local.resolver import TransformNotFoundError


class TestCanonicalizeCore:
    """Tests for core canonicalize() function."""

    def test_canonicalize_with_registry_style_id(self):
        """Test canonicalize with registry-style transform ID."""
        # Load test data
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Transform
        canonical = canonicalize(
            raw_email, transform_id="email/gmail_to_jmap_lite@1.0.0"
        )

        # Verify result is dict
        assert isinstance(canonical, dict)
        # Verify has expected JMAP fields
        assert "id" in canonical
        assert "from" in canonical or "sender" in canonical

    def test_canonicalize_with_full_path(self):
        """Test canonicalize with full path to .meta.yaml."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Transform using full path
        canonical = canonicalize(
            raw_email,
            transform_id="transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
        )

        assert isinstance(canonical, dict)

    def test_canonicalize_with_validation_disabled(self):
        """Test canonicalize with validation disabled."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Should not raise even if schemas are missing
        canonical = canonicalize(
            raw_email,
            transform_id="email/gmail_to_jmap_lite@1.0.0",
            validate_input=False,
            validate_output=False,
        )

        assert isinstance(canonical, dict)

    def test_canonicalize_invalid_transform_id(self):
        """Test canonicalize with invalid transform ID raises error."""
        with pytest.raises((FileNotFoundError, TransformNotFoundError), match="not found"):
            canonicalize(
                {"test": "data"}, transform_id="nonexistent/transform@1.0.0"
            )

    def test_canonicalize_malformed_transform_id(self):
        """Test canonicalize with malformed ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transform_id"):
            canonicalize({"test": "data"}, transform_id="no-version-specified")


class TestRunBatch:
    """Tests for run_batch() function."""

    def test_run_batch_multiple_documents(self):
        """Test batch processing of multiple documents."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Create batch of 3 identical docs (for testing)
        documents = [raw_email, raw_email, raw_email]

        # Transform batch
        canonicals = run_batch(
            documents, transform_id="email/gmail_to_jmap_lite@1.0.0"
        )

        assert isinstance(canonicals, list)
        assert len(canonicals) == 3
        for canonical in canonicals:
            assert isinstance(canonical, dict)

    def test_run_batch_empty_list(self):
        """Test batch processing with empty list."""
        canonicals = run_batch([], transform_id="email/gmail_to_jmap_lite@1.0.0")

        assert canonicals == []


class TestConvenienceFunctions:
    """Tests for convenience wrapper functions."""

    def test_canonicalize_email_from_gmail_lite(self):
        """Test Gmail convenience function with lite format."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        canonical = canonicalize_email_from_gmail(raw_email, format="lite")

        assert isinstance(canonical, dict)

    def test_canonicalize_email_from_gmail_full(self):
        """Test Gmail convenience function with full format."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Note: Full format transform may not be imported locally
        try:
            from canonizer.api import canonicalize

            canonical = canonicalize(
                raw_email,
                transform_id="email/gmail_to_jmap_full@1.0.0",
                validate_output=False,
            )
            assert isinstance(canonical, dict)
        except (FileNotFoundError, TransformNotFoundError):
            pytest.skip("Transform email/gmail_to_jmap_full@1.0.0 not available locally")

    def test_canonicalize_email_from_gmail_minimal(self):
        """Test Gmail convenience function with minimal format."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # Note: Minimal format transform may not be imported locally
        try:
            canonical = canonicalize_email_from_gmail(raw_email, format="minimal")
            assert isinstance(canonical, dict)
        except (FileNotFoundError, TransformNotFoundError):
            pytest.skip("Transform email/gmail_to_jmap_minimal@1.0.0 not available locally")

    def test_canonicalize_email_from_gmail_invalid_format(self):
        """Test Gmail convenience function with invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid format"):
            canonicalize_email_from_gmail({"test": "data"}, format="invalid")

    def test_canonicalize_email_from_exchange_lite(self):
        """Test Exchange convenience function with lite format."""
        input_file = Path("tests/golden/email/exchange_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        canonical = canonicalize_email_from_exchange(raw_email, format="lite")

        assert isinstance(canonical, dict)

    def test_canonicalize_form_response(self):
        """Test form response convenience function."""
        # Note: This will skip if transform doesn't exist yet
        input_file = Path("tests/golden/forms/google_forms_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_form = json.loads(input_file.read_text())

        canonical = canonicalize_form_response(raw_form)

        assert isinstance(canonical, dict)


class TestImports:
    """Test that imports work correctly."""

    def test_import_from_canonizer(self):
        """Test importing functions from canonizer package."""
        from canonizer import (
            canonicalize,
            canonicalize_email_from_exchange,
            canonicalize_email_from_gmail,
            canonicalize_form_response,
            run_batch,
        )

        # Verify all functions are callable
        assert callable(canonicalize)
        assert callable(run_batch)
        assert callable(canonicalize_email_from_gmail)
        assert callable(canonicalize_email_from_exchange)
        assert callable(canonicalize_form_response)

    def test_import_from_api_module(self):
        """Test importing directly from api module."""
        from canonizer.api import canonicalize

        assert callable(canonicalize)
