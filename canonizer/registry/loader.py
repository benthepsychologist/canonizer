"""Transform registry loader: loads .meta.yaml + corresponding .jsonata file."""

from pathlib import Path
from typing import NamedTuple

import yaml

from canonizer.registry.transform_meta import TransformMeta


class Transform(NamedTuple):
    """Complete transform: metadata + JSONata source."""

    meta: TransformMeta
    jsonata: str
    meta_path: Path
    jsonata_path: Path


class TransformLoader:
    """Loads transforms from .meta.yaml + .jsonata file pairs."""

    @staticmethod
    def load(meta_yaml_path: Path | str) -> Transform:
        """
        Load a transform from its .meta.yaml file.

        Args:
            meta_yaml_path: Path to .meta.yaml file

        Returns:
            Transform object with metadata and JSONata source

        Raises:
            FileNotFoundError: If .meta.yaml or .jsonata file not found
            ValueError: If checksum verification fails
            yaml.YAMLError: If .meta.yaml is invalid YAML
        """
        meta_path = Path(meta_yaml_path)
        if not meta_path.exists():
            raise FileNotFoundError(f"Transform metadata not found: {meta_path}")

        # Load and parse metadata
        with open(meta_path) as f:
            meta_dict = yaml.safe_load(f)

        meta = TransformMeta(**meta_dict)

        # Load JSONata source
        jsonata_path = meta_path.parent / meta.spec_path
        if not jsonata_path.exists():
            raise FileNotFoundError(f"Transform file not found: {jsonata_path}")

        jsonata_source = jsonata_path.read_text()

        # Verify checksum
        if not meta.verify_checksum(meta_path):
            computed = meta.compute_checksum(meta_path)
            raise ValueError(
                f"Checksum verification failed for {jsonata_path}\n"
                f"Expected: {meta.checksum}\n"
                f"Computed: {computed}\n"
                f"The .jsonata file may have been modified without updating .meta.yaml"
            )

        return Transform(
            meta=meta,
            jsonata=jsonata_source,
            meta_path=meta_path,
            jsonata_path=jsonata_path,
        )

    @staticmethod
    def discover(base_dir: Path | str, pattern: str = "**/*.meta.yaml") -> list[Path]:
        """
        Discover all .meta.yaml files in a directory tree.

        Args:
            base_dir: Root directory to search
            pattern: Glob pattern for finding metadata files

        Returns:
            List of paths to .meta.yaml files
        """
        base = Path(base_dir)
        if not base.exists():
            raise FileNotFoundError(f"Directory not found: {base}")

        return sorted(base.glob(pattern))
