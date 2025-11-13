"""Transform validation for registry contributions."""

import hashlib
import json
from pathlib import Path

import yaml

from canonizer.core.jsonata_exec import JSONataExecutor
from canonizer.registry.transform_meta import TransformMeta


class TransformValidationError(Exception):
    """Transform validation error."""

    pass


class TransformValidator:
    """
    Validates a transform directory for registry contribution.

    Checks:
    - Directory structure
    - Metadata validity (Pydantic)
    - Checksum verification
    - Golden tests execution
    - Schema references
    """

    def __init__(self, transform_dir: Path):
        """
        Initialize validator for a transform directory.

        Args:
            transform_dir: Path to transform directory (e.g., transforms/email/gmail_to_canonical/1.0.0/)
        """
        self.transform_dir = Path(transform_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """
        Run all validation checks.

        Returns:
            True if all validations pass, False otherwise
        """
        success = True
        success &= self._check_structure()
        success &= self._check_metadata()
        success &= self._check_checksum()
        success &= self._check_golden_tests()

        return success

    def _check_structure(self) -> bool:
        """Check directory structure."""
        required_files = [
            "spec.jsonata",
            "spec.meta.yaml",
        ]

        for filename in required_files:
            file_path = self.transform_dir / filename
            if not file_path.exists():
                self.errors.append(f"Missing required file: {filename}")
                return False

        # Check for tests directory
        tests_dir = self.transform_dir / "tests"
        if tests_dir.exists():
            # If tests dir exists, check for test files
            if not list(tests_dir.glob("*.json")):
                self.warnings.append("tests/ directory exists but contains no JSON files")

        return True

    def _check_metadata(self) -> bool:
        """Validate metadata file."""
        meta_path = self.transform_dir / "spec.meta.yaml"

        try:
            with open(meta_path) as f:
                meta_dict = yaml.safe_load(f)

            # Validate with Pydantic
            meta = TransformMeta(**meta_dict)

            # Check that spec_path matches expected
            if meta.spec_path != "spec.jsonata":
                self.errors.append(
                    f"spec_path should be 'spec.jsonata', got '{meta.spec_path}'"
                )
                return False

            # Check version format
            version_parts = meta.version.split(".")
            if len(version_parts) != 3:
                self.errors.append(
                    f"Version must be SemVer (MAJOR.MINOR.PATCH), got '{meta.version}'"
                )
                return False

            return True

        except FileNotFoundError:
            self.errors.append("spec.meta.yaml not found")
            return False
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in spec.meta.yaml: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Metadata validation failed: {e}")
            return False

    def _check_checksum(self) -> bool:
        """Verify checksum matches."""
        meta_path = self.transform_dir / "spec.meta.yaml"
        jsonata_path = self.transform_dir / "spec.jsonata"

        try:
            with open(meta_path) as f:
                meta_dict = yaml.safe_load(f)

            meta = TransformMeta(**meta_dict)

            # Compute actual checksum
            with open(jsonata_path, "rb") as f:
                computed = hashlib.sha256(f.read()).hexdigest()

            expected = meta.checksum.jsonata_sha256

            if computed != expected:
                self.errors.append(
                    f"Checksum mismatch:\n"
                    f"  Expected: {expected}\n"
                    f"  Computed: {computed}\n"
                    f"  Update spec.meta.yaml with the correct checksum"
                )
                return False

            return True

        except Exception as e:
            self.errors.append(f"Checksum verification failed: {e}")
            return False

    def _check_golden_tests(self) -> bool:
        """Execute golden tests if they exist."""
        meta_path = self.transform_dir / "spec.meta.yaml"
        jsonata_path = self.transform_dir / "spec.jsonata"

        try:
            with open(meta_path) as f:
                meta_dict = yaml.safe_load(f)

            meta = TransformMeta(**meta_dict)

            if not meta.tests:
                self.warnings.append("No golden tests defined in metadata")
                return True

            # Load JSONata transform
            with open(jsonata_path) as f:
                jsonata_source = f.read()

            executor = JSONataExecutor()

            # Run each test
            for i, test_fixture in enumerate(meta.tests):
                input_path = self.transform_dir / test_fixture.input
                expect_path = self.transform_dir / test_fixture.expect

                if not input_path.exists():
                    self.errors.append(f"Test {i}: Input file not found: {test_fixture.input}")
                    return False

                if not expect_path.exists():
                    self.errors.append(
                        f"Test {i}: Expected output file not found: {test_fixture.expect}"
                    )
                    return False

                # Load test data
                with open(input_path) as f:
                    input_data = json.load(f)

                with open(expect_path) as f:
                    expected_output = json.load(f)

                # Execute transform
                try:
                    actual_output = executor.execute(jsonata_source, input_data)

                    # Compare outputs
                    if actual_output != expected_output:
                        self.errors.append(
                            f"Test {i}: Output mismatch\n"
                            f"  Input: {test_fixture.input}\n"
                            f"  Expected: {test_fixture.expect}\n"
                            f"  Actual output differs from expected"
                        )
                        return False

                except Exception as e:
                    self.errors.append(f"Test {i}: Transform execution failed: {e}")
                    return False

            return True

        except Exception as e:
            self.errors.append(f"Golden test execution failed: {e}")
            return False

    def get_report(self) -> str:
        """
        Get validation report.

        Returns:
            Formatted report string
        """
        lines = ["=" * 80, "TRANSFORM VALIDATION REPORT", "=" * 80, ""]

        if not self.errors and not self.warnings:
            lines.append("✅ All validations passed")
        else:
            if self.errors:
                lines.append(f"❌ Errors ({len(self.errors)}):")
                for error in self.errors:
                    lines.append(f"  - {error}")
                lines.append("")

            if self.warnings:
                lines.append(f"⚠️  Warnings ({len(self.warnings)}):")
                for warning in self.warnings:
                    lines.append(f"  - {warning}")
                lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)
