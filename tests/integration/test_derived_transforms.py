"""Integration tests for derived schema transforms (formation + projection).

Tests all 5 transforms for Gate 9:
- Formation transforms:
  1. formation/form_response_to_measurement_event@1.0.0
  2. formation/measurement_event_to_finalform_input@1.0.0
  3. formation/finalform_event_to_observation_row@1.0.0
- Projection transforms:
  4. projection/bq_rows_to_sqlite_sync@1.0.0
  5. projection/bq_rows_to_sheets_write_table@1.0.0

Tests include:
- End-to-end transform execution
- Golden fixture validation
- Edge cases (missing optional fields, email fallback, multiple measures)
- Deterministic key generation
- Stable column ordering
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
def formation_transforms_dir(project_root):
    """Return path to formation transforms directory."""
    return project_root / "transforms" / "formation"


@pytest.fixture
def projection_transforms_dir(project_root):
    """Return path to projection transforms directory."""
    return project_root / "transforms" / "projection"


@pytest.fixture
def runtime(schemas_dir):
    """Create TransformRuntime instance."""
    return TransformRuntime(schemas_dir=schemas_dir)


# ============================================================================
# Formation Transform Tests
# ============================================================================


class TestFormResponseToMeasurementEvent:
    """Tests for formation/form_response_to_measurement_event@1.0.0"""

    def test_end_to_end(self, runtime, formation_transforms_dir):
        """Test form_response to measurement_event transform with external_id."""
        transform_dir = formation_transforms_dir / "form_response_to_measurement_event" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"
        expected_file = transform_dir / "tests" / "expected.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,  # Skip validation since we use config wrapper
            validate_output=False,
        )

        # Verify core fields
        assert result.data["idem_key"] == expected_data["idem_key"]
        assert result.data["measurement_event_id"] == expected_data["measurement_event_id"]
        assert result.data["canonical_object_id"] == expected_data["canonical_object_id"]
        assert result.data["subject_id"] == expected_data["subject_id"]
        assert result.data["event_type"] == expected_data["event_type"]
        assert result.data["binding_id"] == expected_data["binding_id"]
        assert result.data["source_system"] == expected_data["source_system"]
        assert result.data["source_entity"] == expected_data["source_entity"]
        assert result.data["occurred_at"] == expected_data["occurred_at"]

        # Verify metadata contains answers for downstream scoring
        assert "metadata" in result.data
        assert "answers" in result.data["metadata"]
        assert len(result.data["metadata"]["answers"]) == len(expected_data["metadata"]["answers"])

        # Verify execution metadata
        assert result.runtime == "node"
        assert result.execution_time_ms > 0

    def test_email_fallback(self, runtime, formation_transforms_dir):
        """Test subject_id falls back to email when external_id is missing."""
        transform_dir = formation_transforms_dir / "form_response_to_measurement_event" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input_email_fallback.json"
        expected_file = transform_dir / "tests" / "expected_email_fallback.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Verify email fallback
        assert result.data["subject_id"] == "anonymous@example.com"
        assert result.data["subject_id"] == expected_data["subject_id"]

    def test_deterministic_ids(self, runtime, formation_transforms_dir):
        """Test that measurement_event_id and canonical_object_id are deterministic."""
        transform_dir = formation_transforms_dir / "form_response_to_measurement_event" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"

        with open(input_file) as f:
            input_data = json.load(f)

        # Run transform twice
        result1 = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        result2 = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Verify deterministic keys
        assert result1.data["measurement_event_id"] == result2.data["measurement_event_id"]
        assert result1.data["canonical_object_id"] == result2.data["canonical_object_id"]
        assert result1.data["idem_key"] == result2.data["idem_key"]


class TestMeasurementEventToFinalformInput:
    """Tests for formation/measurement_event_to_finalform_input@1.0.0"""

    def test_end_to_end(self, runtime, formation_transforms_dir):
        """Test measurement_event to finalform_input transform."""
        transform_dir = formation_transforms_dir / "measurement_event_to_finalform_input" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"
        expected_file = transform_dir / "tests" / "expected.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Verify core fields
        assert result.data["form_id"] == expected_data["form_id"]
        assert result.data["form_submission_id"] == expected_data["form_submission_id"]
        assert result.data["subject_id"] == expected_data["subject_id"]
        assert result.data["timestamp"] == expected_data["timestamp"]
        assert result.data["form_correlation_id"] == expected_data["form_correlation_id"]

        # Verify items array
        assert len(result.data["items"]) == len(expected_data["items"])
        for i, item in enumerate(result.data["items"]):
            assert item["question_id"] == expected_data["items"][i]["question_id"]
            assert item["answer_value"] == expected_data["items"][i]["answer_value"]

    def test_preserves_correlation_id(self, runtime, formation_transforms_dir):
        """Test that form_correlation_id is preserved for downstream observation keys."""
        transform_dir = formation_transforms_dir / "measurement_event_to_finalform_input" / "1.0.0"
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

        assert result.data["form_correlation_id"] == input_data["correlation_id"]


class TestFinalformEventToObservationRow:
    """Tests for formation/finalform_event_to_observation_row@1.0.0"""

    def test_single_measure(self, runtime, formation_transforms_dir):
        """Test finalform to observation rows transform with single measure."""
        transform_dir = formation_transforms_dir / "finalform_event_to_observation_row" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"
        expected_file = transform_dir / "tests" / "expected.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Output should be array (1:N transform)
        assert isinstance(result.data, list)
        assert len(result.data) == 1

        obs = result.data[0]
        expected_obs = expected_data[0]

        assert obs["idem_key"] == expected_obs["idem_key"]
        assert obs["observation_id"] == expected_obs["observation_id"]
        assert obs["measurement_event_id"] == expected_obs["measurement_event_id"]
        assert obs["subject_id"] == expected_obs["subject_id"]
        assert obs["measure_code"] == expected_obs["measure_code"]
        assert obs["occurred_at"] == expected_obs["occurred_at"]
        assert len(obs["components"]) == len(expected_obs["components"])

    def test_multiple_measures(self, runtime, formation_transforms_dir):
        """Test 1:N output with multiple measures (phq9 + gad7)."""
        transform_dir = formation_transforms_dir / "finalform_event_to_observation_row" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input_multiple_measures.json"
        expected_file = transform_dir / "tests" / "expected_multiple_measures.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Should produce 2 observation rows
        assert isinstance(result.data, list)
        assert len(result.data) == 2

        # Verify both measures are present
        measure_codes = [obs["measure_code"] for obs in result.data]
        assert "phq9" in measure_codes
        assert "gad7" in measure_codes

        # Verify deterministic idem_keys
        idem_keys = [obs["idem_key"] for obs in result.data]
        assert "corr_multi456:phq9" in idem_keys
        assert "corr_multi456:gad7" in idem_keys

    def test_deterministic_idem_key(self, runtime, formation_transforms_dir):
        """Test that idem_key is deterministic for idempotent upsert."""
        transform_dir = formation_transforms_dir / "finalform_event_to_observation_row" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"

        with open(input_file) as f:
            input_data = json.load(f)

        result1 = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        result2 = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # idem_key should be deterministic
        assert result1.data[0]["idem_key"] == result2.data[0]["idem_key"]


# ============================================================================
# Projection Transform Tests
# ============================================================================


class TestBqRowsToSqliteSync:
    """Tests for projection/bq_rows_to_sqlite_sync@1.0.0"""

    def test_end_to_end(self, runtime, projection_transforms_dir):
        """Test BQ rows to sqlite.sync op params transform."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sqlite_sync" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"
        expected_file = transform_dir / "tests" / "expected.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Verify config fields
        assert result.data["sqlite_path"] == expected_data["sqlite_path"]
        assert result.data["table"] == expected_data["table"]

        # Verify columns are deterministic (sorted alphabetically + timestamp)
        assert result.data["columns"] == expected_data["columns"]

        # Verify rows have timestamp injected
        assert len(result.data["rows"]) == len(expected_data["rows"])
        for row in result.data["rows"]:
            assert "projected_at" in row

    def test_deterministic_column_ordering(self, runtime, projection_transforms_dir):
        """Test that column ordering is deterministic."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sqlite_sync" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"

        # Input with columns in different orders across rows
        input_data = {
            "rows": [
                {"z_col": "1", "a_col": "2", "m_col": "3"},
                {"a_col": "4", "z_col": "5", "m_col": "6"},
            ],
            "config": {
                "sqlite_path": "/test/db.sqlite",
                "table": "test_table"
            }
        }

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Columns should be sorted alphabetically
        assert result.data["columns"] == ["a_col", "m_col", "z_col"]


class TestBqRowsToSheetsWriteTable:
    """Tests for projection/bq_rows_to_sheets_write_table@1.0.0"""

    def test_end_to_end(self, runtime, projection_transforms_dir):
        """Test BQ rows to sheets.write_table op params transform."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sheets_write_table" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"
        input_file = transform_dir / "tests" / "input.json"
        expected_file = transform_dir / "tests" / "expected.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(expected_file) as f:
            expected_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Verify config fields
        assert result.data["spreadsheet_id"] == expected_data["spreadsheet_id"]
        assert result.data["sheet_name"] == expected_data["sheet_name"]
        assert result.data["strategy"] == expected_data["strategy"]
        assert result.data["account"] == expected_data["account"]

        # Verify 2D values matrix structure
        assert len(result.data["values"]) == len(expected_data["values"])

        # First row should be headers
        assert result.data["values"][0] == expected_data["values"][0]

        # Data rows should match
        for i in range(1, len(result.data["values"])):
            assert result.data["values"][i] == expected_data["values"][i]

    def test_header_row_plus_data_rows(self, runtime, projection_transforms_dir):
        """Test that output has header row followed by data rows."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sheets_write_table" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"

        input_data = {
            "rows": [
                {"id": "1", "value": "a"},
                {"id": "2", "value": "b"},
            ],
            "config": {
                "spreadsheet_id": "test123",
                "sheet_name": "Sheet1"
            }
        }

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Should have 3 rows total (1 header + 2 data)
        assert len(result.data["values"]) == 3

        # First row is header
        assert result.data["values"][0] == ["id", "value"]

        # Data rows follow
        assert result.data["values"][1] == ["1", "a"]
        assert result.data["values"][2] == ["2", "b"]

    def test_deterministic_column_ordering(self, runtime, projection_transforms_dir):
        """Test that column/header ordering is deterministic."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sheets_write_table" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"

        input_data = {
            "rows": [
                {"z_col": "1", "a_col": "2"},
            ],
            "config": {
                "spreadsheet_id": "test123",
                "sheet_name": "Sheet1"
            }
        }

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        # Header should be sorted alphabetically
        assert result.data["values"][0] == ["a_col", "z_col"]

        # Data should match header order
        assert result.data["values"][1] == ["2", "1"]

    def test_default_strategy(self, runtime, projection_transforms_dir):
        """Test that default strategy is 'replace'."""
        transform_dir = projection_transforms_dir / "bq_rows_to_sheets_write_table" / "1.0.0"
        transform_meta = transform_dir / "spec.meta.yaml"

        input_data = {
            "rows": [{"id": "1"}],
            "config": {
                "spreadsheet_id": "test123",
                "sheet_name": "Sheet1"
                # No strategy specified
            }
        }

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=False,
            validate_output=False,
        )

        assert result.data["strategy"] == "replace"
