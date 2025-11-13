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


class Compat(BaseModel):
    """Compatibility information for schema version ranges."""

    from_schema_range: str | None = Field(
        None,
        description="Compatible input schema version range (Iglu format, e.g., '1-0-0 .. 1-2-x')",
    )


class Provenance(BaseModel):
    """Provenance information for transform authorship and creation."""

    author: str = Field(..., description="Author name and email (e.g., 'Name <email@example.com>')")
    created_utc: datetime = Field(..., description="Creation timestamp (ISO 8601 UTC)")

    @field_validator("created_utc")
    @classmethod
    def validate_utc_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            raise ValueError("created_utc must include timezone information (UTC)")
        return v


class Checksum(BaseModel):
    """Checksum information for integrity verification."""

    jsonata_sha256: str = Field(
        ...,
        description="SHA256 hex digest of spec.jsonata file",
        pattern=r"^[a-f0-9]{64}$",
    )


class TransformMeta(BaseModel):
    """
    Transform metadata sidecar (.meta.yaml).

    This model defines the minimal metadata required for transform registry.
    The actual transform logic lives in a separate .jsonata file.
    """

    id: str = Field(
        ...,
        description="Unique transform identifier (e.g., 'email/gmail_to_canonical')",
        pattern=r"^[a-z0-9_]+(/[a-z0-9_]+)?$",
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
        default="python",
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
    checksum: Checksum = Field(..., description="Checksum information for integrity verification")
    compat: Compat | None = Field(None, description="Compatibility information (optional)")
    provenance: Provenance = Field(..., description="Provenance information (author, creation date)")
    status: Literal["draft", "stable", "deprecated"] = Field(
        default="draft", description="Transform lifecycle status"
    )

    # Legacy fields for backwards compatibility (deprecated)
    author: str | None = Field(None, description="DEPRECATED: Use provenance.author instead")
    created: datetime | None = Field(None, description="DEPRECATED: Use provenance.created_utc instead")

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
            Hex digest string (without prefix)
        """
        jsonata_path = meta_yaml_path.parent / self.spec_path
        if not jsonata_path.exists():
            raise FileNotFoundError(f"Transform file not found: {jsonata_path}")

        sha256 = hashlib.sha256()
        sha256.update(jsonata_path.read_bytes())
        return sha256.hexdigest()

    def verify_checksum(self, meta_yaml_path: Path) -> bool:
        """
        Verify that the .jsonata file matches the stored checksum.

        Args:
            meta_yaml_path: Path to the .meta.yaml file

        Returns:
            True if checksum matches, False otherwise
        """
        computed = self.compute_checksum(meta_yaml_path)
        return computed == self.checksum.jsonata_sha256
