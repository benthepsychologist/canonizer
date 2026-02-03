"""JSONata execution via Node.js canonizer-core CLI."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from canonizer.core.node_bridge import get_canonizer_core_bin


class JSONataExecutionError(Exception):
    """Raised when JSONata execution fails."""

    pass


class JSONataResult(BaseModel):
    """Result of JSONata execution."""

    output: Any
    runtime: Literal["node"]
    execution_time_ms: float


class JSONataExecutor:
    """Executes JSONata transforms using Node.js canonizer-core."""

    def __init__(self, runtime: Literal["node", "auto"] = "auto"):
        """
        Initialize executor.

        Args:
            runtime: Runtime to use ("node" or "auto" - both use Node.js)
        """
        # Always use Node.js - no Python fallback
        self.runtime = "node"

    def execute(self, jsonata_expr: str, input_data: Any) -> JSONataResult:
        """
        Execute JSONata expression on input data.

        Args:
            jsonata_expr: JSONata expression as string
            input_data: Input data (JSON-serializable)

        Returns:
            JSONataResult with output and metadata

        Raises:
            JSONataExecutionError: If execution fails
        """
        return self._execute_node(jsonata_expr, input_data)

    def _execute_node(self, jsonata_expr: str, input_data: Any) -> JSONataResult:
        """Execute JSONata using canonizer-core CLI."""
        bin_path = get_canonizer_core_bin()

        start = time.time()

        # Use temp files for stdin/stdout to avoid pipe buffer truncation.
        # Python's subprocess PIPE has issues with outputs > 64KB on some systems
        # (seen in Python 3.14 on Linux ARM64). Using temp files is more reliable.
        input_file = None
        output_file = None
        try:
            # Write input to temp file
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".json", delete=False
            ) as f:
                f.write(json.dumps(input_data).encode("utf-8"))
                input_file = f.name

            # Create output temp file
            output_fd, output_file = tempfile.mkstemp(suffix=".json")
            os.close(output_fd)

            with open(input_file, "rb") as stdin_fh, open(output_file, "wb") as stdout_fh:
                proc = subprocess.Popen(
                    [bin_path, "jsonata", "--expr", jsonata_expr],
                    stdin=stdin_fh,
                    stdout=stdout_fh,
                    stderr=subprocess.PIPE,
                )
                _, stderr_bytes = proc.communicate(timeout=30)

            execution_time_ms = (time.time() - start) * 1000

            if proc.returncode != 0:
                stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""
                raise JSONataExecutionError(
                    f"JSONata execution failed: {stderr.strip()}"
                )

            # Read output
            with open(output_file, "rb") as f:
                stdout_bytes = f.read()

            stdout = stdout_bytes.decode("utf-8")
            try:
                output = json.loads(stdout)
            except json.JSONDecodeError:
                # Output might be a primitive (string, number, etc.)
                output = stdout.strip()

            return JSONataResult(
                output=output,
                runtime="node",
                execution_time_ms=execution_time_ms,
            )

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # Clean up
            raise JSONataExecutionError("JSONata execution timed out (30s)")
        except FileNotFoundError:
            raise JSONataExecutionError(
                "canonizer-core not found. Run 'npm install && npm run build' in packages/canonizer-core/"
            )
        finally:
            # Clean up temp files
            if input_file and os.path.exists(input_file):
                os.unlink(input_file)
            if output_file and os.path.exists(output_file):
                os.unlink(output_file)


def execute_jsonata_file(
    jsonata_file: Path, input_data: Any, runtime: Literal["node", "auto"] = "auto"
) -> JSONataResult:
    """
    Execute JSONata from a .jsonata file.

    Args:
        jsonata_file: Path to .jsonata file
        input_data: Input data
        runtime: Runtime to use (always Node.js)

    Returns:
        JSONataResult

    Raises:
        FileNotFoundError: If .jsonata file doesn't exist
        JSONataExecutionError: If execution fails
    """
    if not jsonata_file.exists():
        raise FileNotFoundError(f"JSONata file not found: {jsonata_file}")

    jsonata_expr = jsonata_file.read_text()

    executor = JSONataExecutor(runtime=runtime)
    return executor.execute(jsonata_expr, input_data)
