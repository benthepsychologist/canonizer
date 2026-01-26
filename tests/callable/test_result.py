"""Tests for CallableResult model."""

import pytest

from canonizer.callable import CallableResult


class TestCallableResult:
    """Tests for CallableResult dataclass."""

    def test_items_only_valid(self):
        """CallableResult with only items is valid."""
        result = CallableResult(items=[{"id": "1"}])
        assert result.items == [{"id": "1"}]
        assert result.items_ref is None
        assert result.schema_version == "1.0"

    def test_items_ref_only_valid(self):
        """CallableResult with only items_ref is valid."""
        result = CallableResult(items_ref="artifact://bucket/path")
        assert result.items is None
        assert result.items_ref == "artifact://bucket/path"
        assert result.schema_version == "1.0"

    def test_empty_items_list_valid(self):
        """CallableResult with empty items list is valid."""
        result = CallableResult(items=[])
        assert result.items == []
        assert result.items_ref is None

    def test_both_items_and_items_ref_raises(self):
        """CallableResult with both items and items_ref raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CallableResult(items=[{"id": "1"}], items_ref="artifact://bucket/path")

        assert "exactly one of 'items' or 'items_ref'" in str(exc_info.value)

    def test_neither_items_nor_items_ref_raises(self):
        """CallableResult with neither items nor items_ref raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CallableResult()

        assert "exactly one of 'items' or 'items_ref'" in str(exc_info.value)

    def test_schema_version_default(self):
        """schema_version defaults to '1.0'."""
        result = CallableResult(items=[])
        assert result.schema_version == "1.0"

    def test_schema_version_custom(self):
        """Custom schema_version is preserved."""
        result = CallableResult(schema_version="2.0", items=[])
        assert result.schema_version == "2.0"

    def test_stats_default_empty(self):
        """stats defaults to empty dict."""
        result = CallableResult(items=[])
        assert result.stats == {}

    def test_stats_custom(self):
        """Custom stats are preserved."""
        stats = {"input": 10, "output": 8, "errors": 2}
        result = CallableResult(items=[], stats=stats)
        assert result.stats == stats


class TestCallableResultToDict:
    """Tests for CallableResult.to_dict() method."""

    def test_to_dict_with_items(self):
        """to_dict includes items when set."""
        result = CallableResult(
            items=[{"id": "1"}, {"id": "2"}],
            stats={"input": 2, "output": 2},
        )
        d = result.to_dict()

        assert d == {
            "schema_version": "1.0",
            "items": [{"id": "1"}, {"id": "2"}],
            "stats": {"input": 2, "output": 2},
        }

    def test_to_dict_with_items_ref(self):
        """to_dict includes items_ref when set."""
        result = CallableResult(
            items_ref="artifact://bucket/path",
            stats={"input": 100, "output": 100},
        )
        d = result.to_dict()

        assert d == {
            "schema_version": "1.0",
            "items_ref": "artifact://bucket/path",
            "stats": {"input": 100, "output": 100},
        }

    def test_to_dict_empty_stats_excluded(self):
        """to_dict excludes stats when empty."""
        result = CallableResult(items=[])
        d = result.to_dict()

        assert d == {
            "schema_version": "1.0",
            "items": [],
        }
        assert "stats" not in d

    def test_to_dict_never_includes_both(self):
        """to_dict never includes both items and items_ref."""
        result_items = CallableResult(items=[{"a": 1}])
        result_ref = CallableResult(items_ref="artifact://x")

        d_items = result_items.to_dict()
        d_ref = result_ref.to_dict()

        assert "items" in d_items and "items_ref" not in d_items
        assert "items_ref" in d_ref and "items" not in d_ref
