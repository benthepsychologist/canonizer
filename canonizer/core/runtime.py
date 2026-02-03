"""Transform runtime engine: validate → transform → validate."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, NamedTuple

from canonizer.core.jsonata_exec import JSONataExecutor
from canonizer.core.node_bridge import get_canonizer_core_bin
from canonizer.core.validator import SchemaValidator, load_schema_from_iglu_uri
from canonizer.registry.loader import TransformLoader


class TransformResult(NamedTuple):
    """Result of transform execution."""

    data: Any
    execution_time_ms: float
    runtime: str


class TransformRuntime:
    """
    Core runtime engine for executing transforms.

    Flow:
    1. Load transform (.meta.yaml + .jsonata)
    2. Validate checksum
    3. Validate input against from_schema
    4. Execute JSONata transform
    5. Validate output against to_schema
    """

    def __init__(self, schemas_dir: Path | str = "schemas"):
        """
        Initialize runtime.

        Args:
            schemas_dir: Base directory for schema files (default: "schemas")
        """
        self.schemas_dir = Path(schemas_dir)

    def execute(
        self,
        transform_meta_path: Path | str,
        input_data: Any,
        validate_input: bool = True,
        validate_output: bool = True,
    ) -> TransformResult:
        """
        Execute a transform end-to-end.

        Args:
            transform_meta_path: Path to .meta.yaml file
            input_data: Input data (JSON-serializable)
            validate_input: Whether to validate input against from_schema
            validate_output: Whether to validate output against to_schema

        Returns:
            TransformResult with output data

        Raises:
            FileNotFoundError: If transform or schema files not found
            ValueError: If checksum verification fails
            ValidationError: If input/output validation fails
            JSONataExecutionError: If transform execution fails
        """
        # 1. Load transform
        transform = TransformLoader.load(transform_meta_path)

        # 2. Validate checksum (prevents tampering)
        if not transform.meta.verify_checksum(transform.meta_path):
            raise ValueError(
                f"Checksum verification failed for {transform.jsonata_path}. "
                f"The .jsonata file may have been modified without updating .meta.yaml"
            )

        # 3. Validate input (optional but recommended)
        if validate_input:
            input_schema_path = load_schema_from_iglu_uri(
                transform.meta.from_schema, self.schemas_dir
            )
            input_validator = SchemaValidator(input_schema_path)
            input_validator.validate(input_data)

        # 4. Execute JSONata transform
        # If transform has extensions, use CLI run command which registers extensions
        # Otherwise use direct JSONata execution (faster for simple transforms)
        has_extensions = bool(transform.meta.extensions)
        if has_extensions:
            output, execution_time_ms, runtime = self._execute_with_cli(
                transform=transform, input_data=input_data
            )
        else:
            executor = JSONataExecutor(runtime=transform.meta.runtime)
            result = executor.execute(transform.jsonata, input_data)
            output = result.output
            execution_time_ms = result.execution_time_ms
            runtime = result.runtime

        # 5. Validate output (optional but recommended)
        if validate_output:
            output_schema_path = load_schema_from_iglu_uri(
                transform.meta.to_schema, self.schemas_dir
            )
            output_validator = SchemaValidator(output_schema_path)
            output_validator.validate(output)

        return TransformResult(
            data=output,
            execution_time_ms=execution_time_ms,
            runtime=runtime,
        )

    def _execute_with_cli(
        self, transform, input_data: Any
    ) -> tuple[Any, float, str]:
        """Execute transform via canonizer-core CLI run command.

        This method is used for transforms that require extensions (like htmlToMarkdown).
        The CLI run command properly registers extensions before execution.

        Uses temp files instead of pipes to avoid 65KB stdout buffer truncation.

        Args:
            transform: Loaded transform with meta and jsonata
            input_data: Input data to transform

        Returns:
            Tuple of (output_data, execution_time_ms, runtime)

        Raises:
            RuntimeError: If CLI execution fails
        """
        from canonizer.core.jsonata_exec import JSONataExecutionError

        bin_path = get_canonizer_core_bin()
        start = time.time()

        # Build transform_id: "domain/name@version"
        transform_id = f"{transform.meta.id}@{transform.meta.version}"

        # Determine registry root from schemas_dir parent
        # schemas_dir is typically registry/schemas, so parent is registry
        registry_root = self.schemas_dir.parent

        input_file = None
        output_file = None
        try:
            # Write input to temp file (avoids stdin pipe limits)
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".json", delete=False
            ) as f:
                f.write(json.dumps(input_data).encode("utf-8"))
                input_file = f.name

            # Create temp file for output (avoids stdout pipe limits)
            output_fd, output_file = tempfile.mkstemp(suffix=".json")
            os.close(output_fd)

            # Run CLI with file redirection to avoid 65KB pipe buffer truncation
            # Use --no-validate since we handle validation in Python
            with open(input_file, "rb") as stdin_fh, open(output_file, "wb") as stdout_fh:
                proc = subprocess.Popen(
                    [
                        bin_path,
                        "run",
                        "--transform", transform_id,
                        "--registry", str(registry_root),
                        "--no-validate",
                    ],
                    stdin=stdin_fh,
                    stdout=stdout_fh,
                    stderr=subprocess.PIPE,
                )
                _, stderr_bytes = proc.communicate(timeout=30)

            execution_time_ms = (time.time() - start) * 1000

            if proc.returncode != 0:
                stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""
                raise JSONataExecutionError(f"CLI execution failed: {stderr.strip()}")

            # Read output
            with open(output_file, "rb") as f:
                stdout_bytes = f.read()

            stdout = stdout_bytes.decode("utf-8")
            try:
                output = json.loads(stdout)
            except json.JSONDecodeError:
                # Output might be a primitive (string, number, etc.)
                output = stdout.strip()

            return output, execution_time_ms, "node"

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # Clean up
            raise JSONataExecutionError("CLI execution timed out (30s)")
        finally:
            # Clean up temp files
            if input_file and os.path.exists(input_file):
                os.unlink(input_file)
            if output_file and os.path.exists(output_file):
                os.unlink(output_file)

    def execute_safe(
        self,
        transform_meta_path: Path | str,
        input_data: Any,
        validate_input: bool = True,
        validate_output: bool = True,
    ) -> tuple[TransformResult | None, Exception | None]:
        """
        Execute transform with exception handling.

        Returns tuple of (result, error) where one is always None.

        Args:
            transform_meta_path: Path to .meta.yaml file
            input_data: Input data
            validate_input: Whether to validate input
            validate_output: Whether to validate output

        Returns:
            Tuple of (TransformResult, None) on success or (None, Exception) on failure
        """
        try:
            result = self.execute(
                transform_meta_path=transform_meta_path,
                input_data=input_data,
                validate_input=validate_input,
                validate_output=validate_output,
            )
            return (result, None)
        except Exception as e:
            return (None, e)
