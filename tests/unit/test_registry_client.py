"""Unit tests for RegistryClient."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
import yaml

from canonizer.registry.client import RegistryClient
from canonizer.registry.transform_meta import Checksum, Provenance


@pytest.fixture
def mock_registry_index():
    """Mock REGISTRY_INDEX.json content."""
    return {
        "version": "1.0.0",
        "generated_at": "2025-11-12T00:00:00+00:00",
        "transforms": [
            {
                "id": "email/gmail_to_canonical",
                "versions": [
                    {
                        "version": "1.0.0",
                        "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
                        "to_schema": "iglu:org.canonical/email/jsonschema/1-0-0",
                        "status": "stable",
                        "path": "transforms/email/gmail_to_canonical/1.0.0/",
                        "checksum": {
                            "jsonata_sha256": "abc123" + "0" * 58,
                        },
                        "author": "Test <test@example.com>",
                        "created_utc": "2025-11-09T00:00:00Z",
                    }
                ],
            }
        ],
        "schemas": [
            {
                "uri": "iglu:com.google/gmail_email/jsonschema/1-0-0",
                "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
            },
            {
                "uri": "iglu:org.canonical/email/jsonschema/1-0-0",
                "path": "schemas/org.canonical/email/jsonschema/1-0-0.json",
            },
        ],
    }


@pytest.fixture
def mock_transform_meta():
    """Mock transform metadata."""
    return {
        "id": "email/gmail_to_canonical",
        "version": "1.0.0",
        "engine": "jsonata",
        "runtime": "python",
        "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/email/jsonschema/1-0-0",
        "spec_path": "spec.jsonata",
        "checksum": {
            "jsonata_sha256": "abc123" + "0" * 58,
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": "2025-11-09T00:00:00Z",
        },
        "status": "stable",
    }


@pytest.fixture
def mock_jsonata_content():
    """Mock JSONata transform content."""
    content = '{"message_id": payload.id}'
    # Return content with matching checksum
    return content


@pytest.fixture
def mock_schema():
    """Mock JSON schema."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
        },
    }


@pytest.fixture
def mock_http_client(mock_registry_index, mock_transform_meta, mock_jsonata_content, mock_schema):
    """Mock httpx.Client for testing."""
    client = Mock(spec=httpx.Client)

    def mock_get(url: str):
        """Mock HTTP GET requests."""
        response = Mock()
        response.raise_for_status = Mock()

        if url.endswith("REGISTRY_INDEX.json"):
            response.content = json.dumps(mock_registry_index).encode()
        elif url.endswith("spec.meta.yaml"):
            response.content = yaml.dump(mock_transform_meta).encode()
        elif url.endswith("spec.jsonata"):
            # Need to compute proper checksum
            response.content = mock_jsonata_content.encode()
        elif url.endswith("1-0-0.json"):
            response.content = json.dumps(mock_schema).encode()
        else:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=Mock(status_code=404)
            )

        return response

    client.get = Mock(side_effect=mock_get)
    return client


@pytest.fixture
def registry_client(tmp_path, mock_http_client):
    """Create a RegistryClient with mocked HTTP and temp cache."""
    return RegistryClient(
        registry_url="https://example.com/registry/",
        cache_dir=tmp_path / "cache",
        http_client=mock_http_client,
    )


def test_fetch_index(registry_client, mock_registry_index):
    """Test fetching registry index."""
    index = registry_client.fetch_index(use_cache=False)

    assert index["version"] == "1.0.0"
    assert len(index["transforms"]) == 1
    assert len(index["schemas"]) == 2


def test_fetch_index_caching(registry_client, mock_http_client):
    """Test that index is cached in memory."""
    # First fetch
    index1 = registry_client.fetch_index(use_cache=False)
    assert mock_http_client.get.call_count == 1

    # Second fetch should use in-memory cache
    index2 = registry_client.fetch_index(use_cache=True)
    assert mock_http_client.get.call_count == 1  # No additional call
    assert index1 is index2


def test_list_transforms(registry_client):
    """Test listing transforms."""
    transforms = registry_client.list_transforms()

    assert len(transforms) == 1
    assert transforms[0]["id"] == "email/gmail_to_canonical"
    assert len(transforms[0]["versions"]) == 1


def test_resolve_version_latest(registry_client):
    """Test resolving 'latest' version."""
    version = registry_client.resolve_version("email/gmail_to_canonical", "latest")

    assert version == "1.0.0"


def test_resolve_version_specific(registry_client):
    """Test resolving specific version."""
    version = registry_client.resolve_version("email/gmail_to_canonical", "1.0.0")

    assert version == "1.0.0"


def test_resolve_version_not_found(registry_client):
    """Test resolving non-existent transform."""
    version = registry_client.resolve_version("nonexistent/transform", "latest")

    assert version is None


def test_resolve_version_not_found_version(registry_client):
    """Test resolving non-existent version."""
    version = registry_client.resolve_version("email/gmail_to_canonical", "2.0.0")

    assert version is None


def test_fetch_transform(registry_client, tmp_path):
    """Test fetching a transform."""
    # First, need to update mock to return proper checksum
    jsonata_content = '{"message_id": payload.id}'
    expected_checksum = hashlib.sha256(jsonata_content.encode()).hexdigest()

    # Update mock transform meta with correct checksum
    mock_meta = {
        "id": "email/gmail_to_canonical",
        "version": "1.0.0",
        "engine": "jsonata",
        "runtime": "python",
        "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
        "to_schema": "iglu:org.canonical/email/jsonschema/1-0-0",
        "spec_path": "spec.jsonata",
        "checksum": {
            "jsonata_sha256": expected_checksum,
        },
        "provenance": {
            "author": "Test <test@example.com>",
            "created_utc": "2025-11-09T00:00:00Z",
        },
        "status": "stable",
    }

    # Create new client with updated mock
    mock_client = Mock(spec=httpx.Client)

    def mock_get(url: str):
        response = Mock()
        response.raise_for_status = Mock()

        if url.endswith("REGISTRY_INDEX.json"):
            response.content = json.dumps(
                {
                    "version": "1.0.0",
                    "transforms": [
                        {
                            "id": "email/gmail_to_canonical",
                            "versions": [{"version": "1.0.0"}],
                        }
                    ],
                    "schemas": [],
                }
            ).encode()
        elif url.endswith("spec.meta.yaml"):
            response.content = yaml.dump(mock_meta).encode()
        elif url.endswith("spec.jsonata"):
            response.content = jsonata_content.encode()
        else:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=Mock(status_code=404)
            )

        return response

    mock_client.get = Mock(side_effect=mock_get)

    client = RegistryClient(
        registry_url="https://example.com/registry/",
        cache_dir=tmp_path / "cache",
        http_client=mock_client,
    )

    transform = client.fetch_transform("email/gmail_to_canonical", version="latest")

    assert transform.meta.id == "email/gmail_to_canonical"
    assert transform.meta.version == "1.0.0"
    assert transform.jsonata == jsonata_content
    assert transform.meta.checksum.jsonata_sha256 == expected_checksum


def test_fetch_transform_checksum_verification_failure(registry_client):
    """Test that checksum verification catches tampering."""
    # The mock has mismatched checksum, so this should fail
    with pytest.raises(ValueError, match="Checksum verification failed"):
        registry_client.fetch_transform(
            "email/gmail_to_canonical", version="latest", verify_checksum=True
        )


def test_fetch_transform_skip_checksum(registry_client):
    """Test fetching transform without checksum verification."""
    # Should succeed even with mismatched checksum
    transform = registry_client.fetch_transform(
        "email/gmail_to_canonical", version="latest", verify_checksum=False
    )

    assert transform.meta.id == "email/gmail_to_canonical"


def test_fetch_transform_not_found(registry_client):
    """Test fetching non-existent transform."""
    with pytest.raises(ValueError, match="Transform not found"):
        registry_client.fetch_transform("nonexistent/transform", version="latest")


def test_fetch_schema(registry_client, mock_schema):
    """Test fetching a schema."""
    schema = registry_client.fetch_schema("iglu:com.google/gmail_email/jsonschema/1-0-0")

    assert schema["type"] == "object"
    assert "message_id" in schema["properties"]


def test_fetch_schema_not_found(registry_client):
    """Test fetching non-existent schema."""
    with pytest.raises(ValueError, match="Schema not found"):
        registry_client.fetch_schema("iglu:nonexistent/schema/jsonschema/1-0-0")


def test_caching_to_disk(registry_client, tmp_path):
    """Test that files are cached to disk."""
    # Fetch index (which caches to disk)
    registry_client.fetch_index(use_cache=False)

    # Check cache directory exists
    url_hash = hashlib.sha256(b"https://example.com/registry/").hexdigest()[:8]
    cache_dir = tmp_path / "cache" / url_hash
    assert cache_dir.exists()

    # Check index file cached
    index_cache = cache_dir / "REGISTRY_INDEX.json"
    assert index_cache.exists()


def test_clear_cache(registry_client, tmp_path):
    """Test clearing cache."""
    # Fetch something to populate cache
    registry_client.fetch_index(use_cache=False)

    url_hash = hashlib.sha256(b"https://example.com/registry/").hexdigest()[:8]
    cache_dir = tmp_path / "cache" / url_hash
    assert cache_dir.exists()

    # Clear cache
    registry_client.clear_cache()

    # Cache should be gone
    assert not cache_dir.exists()
    assert registry_client._index_cache is None


def test_default_registry_url():
    """Test that default registry URL is set."""
    client = RegistryClient()

    assert client.registry_url == RegistryClient.DEFAULT_REGISTRY_URL
    assert "canonizer-registry" in client.registry_url


def test_custom_cache_dir(tmp_path):
    """Test using custom cache directory."""
    custom_cache = tmp_path / "custom_cache"
    client = RegistryClient(cache_dir=custom_cache, http_client=Mock(spec=httpx.Client))

    assert client.cache_dir == custom_cache
