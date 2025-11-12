"""Transform metadata model (.meta.yaml sidecar format)."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TestFixture(BaseModel):
    """Golden test fixture reference."""

    input: str = Field(..., description="Relative path to input JSON file")
    expect: str = Field(..., description="Relative path to expected output JSON file")


class TransformMeta(BaseModel):
    """
    Transform metadata sidecar (.meta.yaml).

    This model defines the minimal metadata required for transform registry.
    The actual transform logic lives in a separate .jsonata file.
    """

    id: str = Field(
        ...,
        description="Unique transform identifier (e.g., 'gmail_to_canonical_email')",
        pattern=r"^[a-z0-9_]+$",
    )
    version: str = Field(
        ...,
        description="SemVer version (MAJOR.MINOR.PATCH)",
        pattern=r"^\d+\.\d+\.\d+$",
    )
    engine: Literal["jsonata"] = Field(
        default="jsonata", description="Transform engine (currently only jsonata)"
    )
    runtime: Literal["node", "python"] = Field(
        default="node",
        description="Runtime to use (node=official, python=fast-path fallback)",
    )
    from_schema: str = Field(
        ...,
        description="Input schema URI (Iglu format: iglu:vendor/name/format/version)",
        pattern=r"^iglu:[a-z0-9._-]+/[a-z0-9._-]+/jsonschema/\d+-\d+-\d+$",
    )
    to_schema: str = Field(
        ...,
        description="Output schema URI (Iglu format: iglu:vendor/name/format/version)",
        pattern=r"^iglu:[a-z0-9._-]+/[a-z0-9._-]+/jsonschema/\d+-\d+-\d+$",
    )
    spec_path: str = Field(
        ..., description="Relative path to .jsonata file from this .meta.yaml file"
    )
    tests: list[TestFixture] = Field(
        default_factory=list, description="Golden test fixtures"
    )
    checksum: str = Field(
        ...,
        description="SHA256 checksum of .jsonata file (format: sha256:hexdigest)",
        pattern=r"^sha256:[a-f0-9]{64}$",
    )
    status: Literal["draft", "stable", "deprecated"] = Field(
        default="draft", description="Transform lifecycle status"
    )
    author: str = Field(..., description="Author email")
    created: datetime = Field(..., description="Creation timestamp (ISO 8601)")

    @field_validator("spec_path")
    @classmethod
    def validate_spec_path(cls, v: str) -> str:
        """Ensure spec_path points to a .jsonata file."""
        if not v.endswith(".jsonata"):
            raise ValueError("spec_path must point to a .jsonata file")
        return v

    def compute_checksum(self, meta_yaml_path: Path) -> str:
        """
        Compute SHA256 checksum of the .jsonata file.

        Args:
            meta_yaml_path: Path to the .meta.yaml file

        Returns:
            Checksum in format "sha256:hexdigest"
        """
        jsonata_path = meta_yaml_path.parent / self.spec_path
        if not jsonata_path.exists():
            raise FileNotFoundError(f"Transform file not found: {jsonata_path}")

        sha256 = hashlib.sha256()
        sha256.update(jsonata_path.read_bytes())
        return f"sha256:{sha256.hexdigest()}"

    def verify_checksum(self, meta_yaml_path: Path) -> bool:
        """
        Verify that the .jsonata file matches the stored checksum.

        Args:
            meta_yaml_path: Path to the .meta.yaml file

        Returns:
            True if checksum matches, False otherwise
        """
        computed = self.compute_checksum(meta_yaml_path)
        return computed == self.checksum
