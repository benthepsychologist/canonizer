"""Tests for execute() callable interface."""

import json
from pathlib import Path

import pytest

from canonizer import CallableResult, execute
from canonizer.local.resolver import TransformNotFoundError


class TestExecuteBasic:
    """Basic tests for execute() function."""

    def test_execute_returns_dict(self):
        """execute() returns a dictionary."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert isinstance(result, dict)

    def test_execute_has_schema_version(self):
        """execute() result includes schema_version."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert "schema_version" in result
        assert result["schema_version"] == "1.0"

    def test_execute_returns_items_not_items_ref(self):
        """v0: execute() returns items, not items_ref."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert "items" in result
        assert "items_ref" not in result

    def test_execute_includes_stats(self):
        """execute() result includes stats dict."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert "stats" in result
        assert result["stats"]["input"] == 1
        assert result["stats"]["output"] == 1


class TestExecuteWithMultipleItems:
    """Tests for execute() with multiple items."""

    def test_execute_multiple_items(self):
        """execute() processes multiple items."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email, raw_email, raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert len(result["items"]) == 3
        assert result["stats"]["input"] == 3
        assert result["stats"]["output"] == 3

    def test_execute_empty_items(self):
        """execute() handles empty items list."""
        result = execute({
            "source_type": "email",
            "items": [],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert result["items"] == []
        assert result["stats"]["input"] == 0
        assert result["stats"]["output"] == 0


class TestExecuteDefaultTransforms:
    """Tests for execute() with default transform resolution."""

    def test_execute_email_source_type(self):
        """execute() resolves 'email' source type to gmail transform."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        # No explicit transform_id - should use default for 'email'
        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {},
        })

        assert "items" in result
        assert len(result["items"]) == 1

    def test_execute_gmail_source_type(self):
        """execute() resolves 'gmail' source type to gmail transform."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "gmail",
            "items": [raw_email],
            "config": {},
        })

        assert "items" in result

    def test_execute_exchange_source_type(self):
        """execute() resolves 'exchange' source type to exchange transform."""
        input_file = Path("tests/golden/email/exchange_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "exchange",
            "items": [raw_email],
            "config": {},
        })

        assert "items" in result

    def test_execute_unknown_source_type_raises(self):
        """execute() raises ValueError for unknown source_type."""
        with pytest.raises(ValueError, match="Unknown source_type"):
            execute({
                "source_type": "unknown_type",
                "items": [],
                "config": {},
            })


class TestExecuteValidation:
    """Tests for execute() parameter validation."""

    def test_execute_missing_source_type_raises(self):
        """execute() raises ValueError if source_type is missing."""
        with pytest.raises(ValueError, match="Missing required parameter.*source_type"):
            execute({
                "items": [],
                "config": {},
            })

    def test_execute_items_not_list_raises(self):
        """execute() raises ValueError if items is not a list."""
        with pytest.raises(ValueError, match="'items' must be a list"):
            execute({
                "source_type": "email",
                "items": "not a list",
                "config": {},
            })

    def test_execute_invalid_transform_raises(self):
        """execute() raises error for non-existent transform."""
        with pytest.raises((FileNotFoundError, TransformNotFoundError, ValueError)):
            execute({
                "source_type": "email",
                "items": [{"test": "data"}],
                "config": {"transform_id": "nonexistent/transform@1.0.0"},
            })


class TestExecuteConfig:
    """Tests for execute() config options."""

    def test_execute_with_explicit_transform_id(self):
        """execute() uses explicit transform_id from config."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        assert "items" in result

    def test_execute_with_validation_disabled(self):
        """execute() respects validate_input and validate_output config."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {
                "transform_id": "email/gmail_to_jmap_lite@1.0.0",
                "validate_input": False,
                "validate_output": False,
            },
        })

        assert "items" in result

    def test_execute_default_config(self):
        """execute() works with empty config dict."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {},
        })

        assert "items" in result

    def test_execute_missing_config_uses_defaults(self):
        """execute() works when config key is omitted entirely."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
        })

        assert "items" in result


class TestExecuteCallableResultSchema:
    """Tests that execute() result matches CallableResult schema."""

    def test_result_can_create_callable_result(self):
        """execute() result can be used to create a CallableResult."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        raw_email = json.loads(input_file.read_text())

        result = execute({
            "source_type": "email",
            "items": [raw_email],
            "config": {"transform_id": "email/gmail_to_jmap_lite@1.0.0"},
        })

        # Result should be a valid CallableResult dict
        # Verify by reconstructing
        callable_result = CallableResult(
            schema_version=result["schema_version"],
            items=result.get("items"),
            items_ref=result.get("items_ref"),
            stats=result.get("stats", {}),
        )

        assert callable_result.schema_version == "1.0"
        assert callable_result.items is not None


class TestExecuteImports:
    """Test that execute can be imported correctly."""

    def test_import_from_canonizer(self):
        """execute can be imported from canonizer package."""
        from canonizer import execute

        assert callable(execute)

    def test_import_from_api_module(self):
        """execute can be imported from canonizer.api."""
        from canonizer.api import execute

        assert callable(execute)

    def test_callable_result_import(self):
        """CallableResult can be imported from canonizer."""
        from canonizer import CallableResult

        assert CallableResult is not None
