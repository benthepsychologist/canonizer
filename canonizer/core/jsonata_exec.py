"""JSONata execution via Node.js subprocess (primary) or Python (fallback)."""

import json
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class JSONataExecutionError(Exception):
    """Raised when JSONata execution fails."""

    pass


class JSONataResult(BaseModel):
    """Result of JSONata execution."""

    output: Any
    runtime: Literal["node", "python"]
    execution_time_ms: float


class JSONataExecutor:
    """Executes JSONata transforms using Node.js (primary) or Python (fallback)."""

    def __init__(self, runtime: Literal["node", "python", "auto"] = "auto"):
        """
        Initialize executor.

        Args:
            runtime: Runtime to use ("node", "python", or "auto" for detection)
        """
        self.runtime = runtime

        if runtime == "auto":
            # Auto-detect: prefer Node, fallback to Python
            self.runtime = "node" if self._is_node_available() else "python"

    @staticmethod
    def _is_node_available() -> bool:
        """Check if Node.js is available."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

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
        if self.runtime == "node":
            return self._execute_node(jsonata_expr, input_data)
        else:
            return self._execute_python(jsonata_expr, input_data)

    def _execute_node(self, jsonata_expr: str, input_data: Any) -> JSONataResult:
        """
        Execute JSONata using Node.js subprocess.

        This is the official, correct implementation.
        """
        import time

        # Create Node.js script
        node_script = f"""
const jsonata = require('jsonata');

const expression = {json.dumps(jsonata_expr)};
const data = {json.dumps(input_data)};

(async () => {{
  try {{
    const compiled = jsonata(expression);
    const result = await compiled.evaluate(data);
    console.log(JSON.stringify({{success: true, result: result}}));
  }} catch (error) {{
    console.log(JSON.stringify({{success: false, error: error.message}}));
  }}
}})();
"""

        start = time.time()

        try:
            result = subprocess.run(
                ["node", "-e", node_script],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            execution_time_ms = (time.time() - start) * 1000

            if result.returncode != 0:
                raise JSONataExecutionError(
                    f"Node.js execution failed: {result.stderr}"
                )

            output = json.loads(result.stdout)

            if not output.get("success"):
                raise JSONataExecutionError(
                    f"JSONata evaluation failed: {output.get('error', 'Unknown error')}"
                )

            return JSONataResult(
                output=output["result"],
                runtime="node",
                execution_time_ms=execution_time_ms,
            )

        except subprocess.TimeoutExpired:
            raise JSONataExecutionError("Node.js execution timed out (30s)")
        except json.JSONDecodeError as e:
            raise JSONataExecutionError(f"Failed to parse Node.js output: {e}")
        except FileNotFoundError:
            raise JSONataExecutionError(
                "Node.js not found. Install Node.js or use runtime='python'"
            )

    def _execute_python(self, jsonata_expr: str, input_data: Any) -> JSONataResult:
        """
        Execute JSONata using Python jsonata-python library (fast-path fallback).

        Note: This may not have 100% parity with official Node implementation.
        """
        import time

        try:
            from jsonata import Jsonata
        except ImportError:
            raise JSONataExecutionError(
                "jsonata-python not installed. Install with: pip install jsonata-python"
            )

        start = time.time()

        try:
            compiled = Jsonata(jsonata_expr)
            result = compiled.evaluate(input_data)
            execution_time_ms = (time.time() - start) * 1000

            return JSONataResult(
                output=result,
                runtime="python",
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            raise JSONataExecutionError(f"Python JSONata execution failed: {e}")


def execute_jsonata_file(
    jsonata_file: Path, input_data: Any, runtime: Literal["node", "python", "auto"] = "auto"
) -> JSONataResult:
    """
    Execute JSONata from a .jsonata file.

    Args:
        jsonata_file: Path to .jsonata file
        input_data: Input data
        runtime: Runtime to use

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
