"""Lock file models for local .canonizer/ directory.

The lock.json file pins specific versions of schemas and transforms
with their content hashes for reproducibility and integrity verification.

Example lock.json:
```json
{
  "version": "1",
  "schemas": {
    "iglu:com.google/gmail_email/jsonschema/1-0-0": {
      "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
      "hash": "sha256:abc123..."
    }
  },
  "transforms": {
    "email/gmail_to_jmap_lite@1.0.0": {
      "path": "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
      "hash": "sha256:def456..."
    }
  }
}
```
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class SchemaLock(BaseModel):
    """Lock entry for a schema."""

    path: str = Field(description="Relative path to schema file within registry/")
    hash: str = Field(description="Content hash in format 'sha256:<hex>'")

    @field_validator("hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Ensure hash is in correct format."""
        if not v.startswith("sha256:"):
            raise ValueError("Hash must start with 'sha256:'")
        hex_part = v[7:]
        if len(hex_part) != 64:
            raise ValueError("SHA256 hash must be 64 hex characters")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Hash must be valid hexadecimal")
        return v


class TransformLock(BaseModel):
    """Lock entry for a transform."""

    path: str = Field(description="Relative path to transform meta.yaml within registry/")
    hash: str = Field(description="Content hash of spec.jsonata in format 'sha256:<hex>'")

    @field_validator("hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Ensure hash is in correct format."""
        if not v.startswith("sha256:"):
            raise ValueError("Hash must start with 'sha256:'")
        hex_part = v[7:]
        if len(hex_part) != 64:
            raise ValueError("SHA256 hash must be 64 hex characters")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Hash must be valid hexadecimal")
        return v


class LockFile(BaseModel):
    """Root model for .canonizer/lock.json."""

    version: str = Field(
        default="1",
        description="Lock file format version",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last update",
    )
    schemas: Dict[str, SchemaLock] = Field(
        default_factory=dict,
        description="Map of schema refs to lock entries",
    )
    transforms: Dict[str, TransformLock] = Field(
        default_factory=dict,
        description="Map of transform refs to lock entries",
    )

    @classmethod
    def load(cls, lock_path: Path) -> "LockFile":
        """Load lock file from JSON.

        Args:
            lock_path: Path to lock.json file

        Returns:
            Parsed LockFile

        Raises:
            FileNotFoundError: If lock file doesn't exist
            ValueError: If lock file is invalid
        """
        if not lock_path.exists():
            raise FileNotFoundError(f"Lock file not found: {lock_path}")

        with open(lock_path) as f:
            data = json.load(f)

        return cls.model_validate(data)

    @classmethod
    def empty(cls) -> "LockFile":
        """Create an empty lock file."""
        return cls(
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def save(self, lock_path: Path) -> None:
        """Save lock file to JSON.

        Args:
            lock_path: Path to write lock.json
        """
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        self.updated_at = datetime.now(timezone.utc).isoformat()
        data = self.model_dump(mode="json")

        with open(lock_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def add_schema(
        self,
        schema_ref: str,
        path: str,
        content: bytes,
    ) -> None:
        """Add or update a schema entry.

        Args:
            schema_ref: Schema reference (e.g., "iglu:com.google/gmail_email/jsonschema/1-0-0")
            path: Relative path within registry
            content: File content for hashing
        """
        hash_value = f"sha256:{hashlib.sha256(content).hexdigest()}"
        self.schemas[schema_ref] = SchemaLock(path=path, hash=hash_value)

    def add_transform(
        self,
        transform_ref: str,
        path: str,
        jsonata_content: bytes,
    ) -> None:
        """Add or update a transform entry.

        Args:
            transform_ref: Transform reference (e.g., "email/gmail_to_jmap_lite@1.0.0")
            path: Relative path to meta.yaml within registry
            jsonata_content: Content of spec.jsonata for hashing
        """
        hash_value = f"sha256:{hashlib.sha256(jsonata_content).hexdigest()}"
        self.transforms[transform_ref] = TransformLock(path=path, hash=hash_value)

    def get_schema_path(self, schema_ref: str) -> Optional[str]:
        """Get the path for a schema reference.

        Args:
            schema_ref: Schema reference

        Returns:
            Relative path or None if not found
        """
        entry = self.schemas.get(schema_ref)
        return entry.path if entry else None

    def get_transform_path(self, transform_ref: str) -> Optional[str]:
        """Get the path for a transform reference.

        Args:
            transform_ref: Transform reference

        Returns:
            Relative path or None if not found
        """
        entry = self.transforms.get(transform_ref)
        return entry.path if entry else None

    def verify_schema(self, schema_ref: str, content: bytes) -> bool:
        """Verify a schema's content matches its locked hash.

        Args:
            schema_ref: Schema reference
            content: File content to verify

        Returns:
            True if hash matches, False otherwise
        """
        entry = self.schemas.get(schema_ref)
        if not entry:
            return False

        actual_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
        return entry.hash == actual_hash

    def verify_transform(self, transform_ref: str, jsonata_content: bytes) -> bool:
        """Verify a transform's jsonata content matches its locked hash.

        Args:
            transform_ref: Transform reference
            jsonata_content: Content of spec.jsonata to verify

        Returns:
            True if hash matches, False otherwise
        """
        entry = self.transforms.get(transform_ref)
        if not entry:
            return False

        actual_hash = f"sha256:{hashlib.sha256(jsonata_content).hexdigest()}"
        return entry.hash == actual_hash


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hash in format 'sha256:<hex>'
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
