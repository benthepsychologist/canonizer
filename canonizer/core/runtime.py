"""Transform runtime engine: validate → transform → validate."""

from pathlib import Path
from typing import Any, NamedTuple

from canonizer.core.jsonata_exec import JSONataExecutor
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
        executor = JSONataExecutor(runtime=transform.meta.runtime)
        result = executor.execute(transform.jsonata, input_data)

        # 5. Validate output (optional but recommended)
        if validate_output:
            output_schema_path = load_schema_from_iglu_uri(
                transform.meta.to_schema, self.schemas_dir
            )
            output_validator = SchemaValidator(output_schema_path)
            output_validator.validate(result.output)

        return TransformResult(
            data=result.output,
            execution_time_ms=result.execution_time_ms,
            runtime=result.runtime,
        )

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
