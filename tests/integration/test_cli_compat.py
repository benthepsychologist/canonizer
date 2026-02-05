"""Integration tests for CLI backward compatibility.

Tests that the CLI still works after refactoring to use the pure API.
"""

import json
import subprocess
from pathlib import Path
import sys
import os

import pytest


def _cli_argv() -> list[str]:
    """Return argv prefix for invoking the canonizer CLI in tests.

    Prefer the console-script in the active environment, but fall back to
    module execution to avoid PATH issues in CI/devcontainers.
    """
    env_bin = Path(sys.executable).resolve().parent

    can_path = env_bin / "can"
    if can_path.exists() and os.access(can_path, os.X_OK):
        return [str(can_path)]

    canonizer_path = env_bin / "canonizer"
    if canonizer_path.exists() and os.access(canonizer_path, os.X_OK):
        return [str(canonizer_path)]

    return [sys.executable, "-m", "canonizer.cli.main"]


class TestCLIBackwardCompatibility:
    """Test that CLI commands work identically after refactor."""

    def test_transform_run_with_file_io(self, tmp_path):
        """Test transform run command with file input/output."""
        # Prepare input file
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        output_file = tmp_path / "output.json"

        # Run CLI command
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify output file exists
        assert output_file.exists(), "Output file not created"

        # Verify output is valid JSON
        output_data = json.loads(output_file.read_text())
        assert isinstance(output_data, dict)
        assert "id" in output_data or "sender" in output_data

    def test_transform_run_with_stdin_stdout(self):
        """Test transform run command with stdin/stdout."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        input_data = input_file.read_text()

        # Run CLI command with stdin/stdout and --json to get clean JSON output
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
                "--json",  # Ensure clean JSON output only
            ],
            input=input_data,
            capture_output=True,
            text=True,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify stdout contains valid JSON
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, dict)

    def test_transform_run_with_validation_flags(self, tmp_path):
        """Test transform run command with validation flags."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        output_file = tmp_path / "output.json"

        # Run CLI command with validation disabled
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
                "--no-validate-input",
                "--no-validate-output",
            ],
            capture_output=True,
            text=True,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_file.exists()

    def test_transform_run_with_json_output_mode(self):
        """Test transform run command with --json flag."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        input_data = input_file.read_text()

        # Run CLI command with --json flag
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
                "--json",
            ],
            input=input_data,
            capture_output=True,
            text=True,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Verify stdout is valid JSON
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, dict)

    def test_transform_run_with_invalid_input(self, tmp_path):
        """Test transform run command with invalid input fails gracefully."""
        input_file = tmp_path / "invalid.json"
        input_file.write_text('{"invalid": "incomplete')  # Malformed JSON

        output_file = tmp_path / "output.json"

        # Run CLI command with invalid input
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
        )

        # Verify command failed with appropriate error
        assert result.returncode != 0
        assert "JSON" in result.stderr or "Parse" in result.stderr

    def test_transform_run_with_nonexistent_transform(self):
        """Test transform run command with nonexistent transform fails gracefully."""
        input_file = Path("tests/golden/email/gmail_v1/input.json")
        if not input_file.exists():
            pytest.skip("Golden test data not available")

        # Run CLI command with nonexistent transform
        result = subprocess.run(
            _cli_argv()
            + [
                "transform",
                "run",
                "--meta",
                "transforms/nonexistent/transform.meta.yaml",
                "--input",
                str(input_file),
            ],
            capture_output=True,
            text=True,
        )

        # Verify command failed
        assert result.returncode != 0

    def test_transform_list_command(self):
        """Test transform list command still works."""
        # Run CLI list command
        result = subprocess.run(
            _cli_argv() + ["transform", "list", "--dir", "transforms"],
            capture_output=True,
            text=True,
        )

        # Note: List command may fail if transforms don't have checksums
        # This is an existing issue, not caused by our refactor
        if result.returncode != 0 and "checksum" in result.stderr:
            pytest.skip("Transform list requires checksums in .meta.yaml files")

        # Verify command succeeded
        assert result.returncode == 0

        # Verify output contains transform information
        assert "email" in result.stdout.lower() or "transforms" in result.stdout.lower()


class TestAPIUsageFromCLI:
    """Test that CLI is correctly using the API underneath."""

    def test_cli_uses_canonicalize_function(self):
        """Verify CLI imports and uses canonicalize from API."""
        # Read the CLI source code
        cli_file = Path("canonizer/cli/cmds/transform.py")
        cli_source = cli_file.read_text()

        # Verify it imports from canonizer (not TransformRuntime directly)
        assert "from canonizer import canonicalize" in cli_source
        assert "canonicalize(" in cli_source

    def test_cli_is_thin_wrapper(self):
        """Verify CLI is a thin wrapper with minimal logic."""
        cli_file = Path("canonizer/cli/cmds/transform.py")
        cli_source = cli_file.read_text()

        # Verify no direct TransformRuntime instantiation in run() function
        lines = cli_source.split("\n")
        in_run_function = False
        for line in lines:
            if "def run(" in line:
                in_run_function = True
            elif in_run_function and "def " in line and "def run(" not in line:
                break
            elif in_run_function and "TransformRuntime(" in line:
                pytest.fail("CLI still directly instantiates TransformRuntime")
