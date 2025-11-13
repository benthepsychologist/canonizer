"""Registry client for fetching transforms and schemas from remote registry."""

import hashlib
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

import httpx
import yaml

from canonizer.registry.loader import Transform
from canonizer.registry.transform_meta import TransformMeta


class RegistryClient:
    """
    Client for fetching transforms and schemas from a Git-based registry.

    Features:
    - Fetches REGISTRY_INDEX.json for efficient lookup
    - Resolves transform versions (latest, specific)
    - Caches downloaded files to ~/.cache/canonizer/registry/
    - Verifies checksums for integrity

    Examples:
        Basic usage with default registry:

        >>> from canonizer.registry import RegistryClient
        >>> client = RegistryClient()
        >>>
        >>> # List all available transforms
        >>> transforms = client.list_transforms()
        >>> for t in transforms:
        ...     print(f"{t['id']}: {len(t['versions'])} versions")
        >>>
        >>> # Fetch latest version of a transform
        >>> transform = client.fetch_transform("email/gmail_to_canonical")
        >>> print(transform.meta.version)  # "1.0.0"
        >>> print(transform.jsonata)  # JSONata source code
        >>>
        >>> # Fetch specific version
        >>> transform = client.fetch_transform("email/gmail_to_canonical", version="1.0.0")
        >>>
        >>> # Fetch a schema
        >>> schema = client.fetch_schema("iglu:org.canonical/email/jsonschema/1-0-0")
        >>> print(schema["type"])  # "object"

        Using a custom registry:

        >>> client = RegistryClient(
        ...     registry_url="https://example.com/my-registry/",
        ...     cache_dir="/tmp/my-cache"
        ... )
        >>> transforms = client.list_transforms()

        Cache management:

        >>> client = RegistryClient()
        >>> transform = client.fetch_transform("email/gmail_to_canonical")
        >>>
        >>> # Force fresh fetch (bypass cache)
        >>> transform = client.fetch_transform("email/gmail_to_canonical", use_cache=False)
        >>>
        >>> # Clear all cached files
        >>> client.clear_cache()
    """

    DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/benthepsychologist/canonizer-registry/main/"

    def __init__(
        self,
        registry_url: str | None = None,
        cache_dir: Path | str | None = None,
        http_client: httpx.Client | None = None,
    ):
        """
        Initialize registry client.

        Args:
            registry_url: Base URL for registry (defaults to official registry)
            cache_dir: Cache directory (defaults to ~/.cache/canonizer/registry/)
            http_client: Optional httpx.Client for testing
        """
        self.registry_url = registry_url or self.DEFAULT_REGISTRY_URL
        self.cache_dir = Path(cache_dir or Path.home() / ".cache" / "canonizer" / "registry")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._http_client = http_client or httpx.Client(timeout=30.0)
        self._index_cache: dict | None = None

    def _fetch_url(self, path: str) -> bytes:
        """
        Fetch a file from the registry.

        Args:
            path: Relative path from registry base URL

        Returns:
            File contents as bytes

        Raises:
            httpx.HTTPError: If fetch fails
        """
        url = urljoin(self.registry_url, path)
        response = self._http_client.get(url)
        response.raise_for_status()
        return response.content

    def _get_cached_path(self, path: str) -> Path:
        """
        Get cache file path for a registry file.

        Args:
            path: Relative path from registry base

        Returns:
            Absolute cache file path
        """
        # Create cache path with URL hash to handle different registries
        url_hash = hashlib.sha256(self.registry_url.encode()).hexdigest()[:8]
        cache_path = self.cache_dir / url_hash / path
        return cache_path

    def _cache_file(self, path: str, content: bytes) -> Path:
        """
        Cache a file locally.

        Args:
            path: Relative path from registry base
            content: File contents

        Returns:
            Path to cached file
        """
        cache_path = self._get_cached_path(path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(content)
        return cache_path

    def _fetch_or_cache(self, path: str, use_cache: bool = True) -> bytes:
        """
        Fetch a file from registry, using cache if available.

        Args:
            path: Relative path from registry base
            use_cache: Whether to use cached version if available

        Returns:
            File contents as bytes
        """
        cache_path = self._get_cached_path(path)

        if use_cache and cache_path.exists():
            return cache_path.read_bytes()

        content = self._fetch_url(path)
        self._cache_file(path, content)
        return content

    def fetch_index(self, use_cache: bool = True) -> dict:
        """
        Fetch REGISTRY_INDEX.json.

        Args:
            use_cache: Whether to use cached version

        Returns:
            Registry index as dict
        """
        if use_cache and self._index_cache is not None:
            return self._index_cache

        content = self._fetch_or_cache("REGISTRY_INDEX.json", use_cache=use_cache)
        index = json.loads(content)
        self._index_cache = index
        return index

    def list_transforms(self, use_cache: bool = True) -> list[dict]:
        """
        List all available transforms.

        Args:
            use_cache: Whether to use cached index

        Returns:
            List of transform entries from registry index
        """
        index = self.fetch_index(use_cache=use_cache)
        return index.get("transforms", [])

    def resolve_version(
        self,
        transform_id: str,
        version: str | Literal["latest"] = "latest",
        use_cache: bool = True,
    ) -> str | None:
        """
        Resolve a transform version.

        Args:
            transform_id: Transform identifier (e.g., "email/gmail_to_canonical")
            version: Version string or "latest"
            use_cache: Whether to use cached index

        Returns:
            Resolved version string, or None if not found
        """
        index = self.fetch_index(use_cache=use_cache)
        transforms = index.get("transforms", [])

        # Find transform by ID
        transform_entry = next((t for t in transforms if t["id"] == transform_id), None)
        if not transform_entry:
            return None

        versions = transform_entry.get("versions", [])
        if not versions:
            return None

        if version == "latest":
            # Return the first version (should be sorted, latest first)
            return versions[0]["version"]

        # Find exact version match
        version_entry = next((v for v in versions if v["version"] == version), None)
        return version_entry["version"] if version_entry else None

    def fetch_transform(
        self,
        transform_id: str,
        version: str | Literal["latest"] = "latest",
        use_cache: bool = True,
        verify_checksum: bool = True,
    ) -> Transform:
        """
        Fetch a transform from the registry.

        Args:
            transform_id: Transform identifier (e.g., "email/gmail_to_canonical")
            version: Version string or "latest"
            use_cache: Whether to use cached files
            verify_checksum: Whether to verify checksum

        Returns:
            Transform object with metadata and JSONata source

        Raises:
            ValueError: If transform not found or checksum verification fails
            httpx.HTTPError: If fetch fails
        """
        # Resolve version
        resolved_version = self.resolve_version(transform_id, version, use_cache=use_cache)
        if not resolved_version:
            raise ValueError(f"Transform not found: {transform_id} version {version}")

        # Construct paths
        base_path = f"transforms/{transform_id}/{resolved_version}/"
        meta_path = base_path + "spec.meta.yaml"
        jsonata_path = base_path + "spec.jsonata"

        # Fetch files
        meta_content = self._fetch_or_cache(meta_path, use_cache=use_cache)
        jsonata_content = self._fetch_or_cache(jsonata_path, use_cache=use_cache)

        # Parse metadata
        meta_dict = yaml.safe_load(meta_content)
        meta = TransformMeta(**meta_dict)

        # Verify checksum if requested
        if verify_checksum:
            computed = hashlib.sha256(jsonata_content).hexdigest()
            expected = meta.checksum.jsonata_sha256
            if computed != expected:
                raise ValueError(
                    f"Checksum verification failed for {transform_id}@{resolved_version}\n"
                    f"Expected: {expected}\n"
                    f"Computed: {computed}\n"
                    f"The transform may have been corrupted during download"
                )

        # Create cache paths for Transform object
        meta_cache_path = self._get_cached_path(meta_path)
        jsonata_cache_path = self._get_cached_path(jsonata_path)

        return Transform(
            meta=meta,
            jsonata=jsonata_content.decode("utf-8"),
            meta_path=meta_cache_path,
            jsonata_path=jsonata_cache_path,
        )

    def fetch_schema(
        self,
        schema_uri: str,
        use_cache: bool = True,
    ) -> dict:
        """
        Fetch a JSON schema from the registry.

        Args:
            schema_uri: Iglu schema URI (e.g., "iglu:org.canonical/email/jsonschema/1-0-0")
            use_cache: Whether to use cached files

        Returns:
            JSON schema as dict

        Raises:
            ValueError: If schema not found
            httpx.HTTPError: If fetch fails
        """
        # Fetch index to find schema path
        index = self.fetch_index(use_cache=use_cache)
        schemas = index.get("schemas", [])

        # Find schema by URI
        schema_entry = next((s for s in schemas if s["uri"] == schema_uri), None)
        if not schema_entry:
            raise ValueError(f"Schema not found: {schema_uri}")

        # Fetch schema file
        schema_path = schema_entry["path"]
        schema_content = self._fetch_or_cache(schema_path, use_cache=use_cache)
        return json.loads(schema_content)

    def clear_cache(self):
        """Clear all cached files for this registry."""
        import shutil

        url_hash = hashlib.sha256(self.registry_url.encode()).hexdigest()[:8]
        cache_path = self.cache_dir / url_hash
        if cache_path.exists():
            shutil.rmtree(cache_path)
        self._index_cache = None
