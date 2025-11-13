"""Comprehensive integration tests for email transformation pipeline.

Tests all 6 email transforms (Gmail + Exchange → JMAP Full/Lite/Minimal):
- End-to-end transform execution
- Schema validation (input → output)
- Error handling and edge cases
- Encoding (UTF-8, special characters, base64)
- Attachment handling
"""

import json
from pathlib import Path

import pytest

from canonizer.core.runtime import TransformRuntime
from canonizer.core.validator import ValidationError


@pytest.fixture
def project_root():
    """Return path to project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def schemas_dir(project_root):
    """Return path to schemas directory."""
    return project_root / "schemas"


@pytest.fixture
def transforms_dir(project_root):
    """Return path to transforms directory."""
    return project_root / "transforms" / "email"


@pytest.fixture
def fixtures_dir(project_root):
    """Return path to test fixtures directory."""
    return project_root / "tests" / "fixtures" / "email"


@pytest.fixture
def runtime(schemas_dir):
    """Create TransformRuntime instance."""
    return TransformRuntime(schemas_dir=schemas_dir)


# ============================================================================
# Gmail → JMAP Full Tests
# ============================================================================


def test_gmail_to_jmap_full_end_to_end(runtime, transforms_dir, fixtures_dir):
    """Test Gmail → JMAP Full transform end-to-end with validation."""
    transform_meta = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify core fields match expected
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]
    assert result.data["from"] == expected_data["from"]
    assert result.data["to"] == expected_data["to"]
    # Normalize timestamp comparison (ignore millisecond precision differences)
    assert result.data["sentAt"].replace(".000Z", "Z") == expected_data["sentAt"].replace(".000Z", "Z")

    # Verify bodyStructure exists (Full format)
    assert "bodyStructure" in result.data
    assert result.data["bodyStructure"] is not None

    # Verify bodyValues exists
    assert "bodyValues" in result.data
    assert len(result.data["bodyValues"]) > 0

    # Verify execution metadata
    assert result.runtime == "node"
    assert result.execution_time_ms > 0


def test_gmail_to_jmap_full_with_attachments(runtime, transforms_dir):
    """Test Gmail → JMAP Full with email containing attachments."""
    transform_meta = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "spec.meta.yaml"

    # Gmail message with attachment
    input_data = {
        "id": "test123",
        "threadId": "thread123",
        "labelIds": ["INBOX"],
        "snippet": "Test with attachment",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test with attachment"},
                {"name": "Date", "value": "Thu, 9 Nov 2023 12:00:00 -0800"},
                {"name": "Message-ID", "value": "<test123@example.com>"}
            ],
            "parts": [
                {
                    "partId": "0",
                    "mimeType": "text/plain",
                    "body": {
                        "size": 13,
                        "data": "SGVsbG8gV29ybGQh"  # "Hello World!" in base64
                    }
                },
                {
                    "partId": "1",
                    "mimeType": "application/pdf",
                    "filename": "document.pdf",
                    "body": {
                        "attachmentId": "ANGjdJ8w",
                        "size": 102400
                    }
                }
            ]
        }
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify attachments array exists
    assert "attachments" in result.data
    assert len(result.data["attachments"]) == 1
    assert result.data["attachments"][0]["type"] == "application/pdf"
    assert result.data["attachments"][0]["name"] == "document.pdf"
    assert result.data["hasAttachment"] is True


def test_gmail_to_jmap_full_multipart_alternative(runtime, transforms_dir):
    """Test Gmail → JMAP Full with multipart/alternative (text + HTML)."""
    transform_meta = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "test456",
        "threadId": "thread456",
        "labelIds": ["INBOX"],
        "snippet": "Test multipart",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Multipart"},
                {"name": "Date", "value": "Thu, 9 Nov 2023 12:00:00 -0800"},
                {"name": "Message-ID", "value": "<test456@example.com>"}
            ],
            "parts": [
                {
                    "partId": "0",
                    "mimeType": "text/plain",
                    "body": {
                        "size": 10,
                        "data": "VGV4dCBib2R5"  # "Text body" in base64
                    }
                },
                {
                    "partId": "1",
                    "mimeType": "text/html",
                    "body": {
                        "size": 20,
                        "data": "PGh0bWw-SFRNTCBib2R5PC9odG1sPg=="  # "<html>HTML body</html>"
                    }
                }
            ]
        }
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify both text and HTML parts exist
    assert len(result.data["textBody"]) >= 1
    assert len(result.data["htmlBody"]) >= 1
    assert result.data["textBody"][0]["type"] == "text/plain"
    assert result.data["htmlBody"][0]["type"] == "text/html"


# ============================================================================
# Gmail → JMAP Lite Tests
# ============================================================================


def test_gmail_to_jmap_lite_end_to_end(runtime, transforms_dir):
    """Test Gmail → JMAP Lite transform end-to-end."""
    transform_meta = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify core fields
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]

    # Verify Lite format has inline body (not bodyStructure)
    assert "body" in result.data
    assert isinstance(result.data["body"], dict)
    assert "text" in result.data["body"] or "html" in result.data["body"]

    # Verify NO bodyStructure (Lite format)
    assert "bodyStructure" not in result.data


def test_gmail_to_jmap_lite_utf8_handling(runtime, transforms_dir):
    """Test Gmail → JMAP Lite with UTF-8 and special characters."""
    transform_meta = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "utf8test",
        "threadId": "thread_utf8",
        "labelIds": ["INBOX"],
        "snippet": "UTF-8 test",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "José García <jose@example.com>"},
                {"name": "To", "value": "François Müller <francois@example.com>"},
                {"name": "Subject", "value": "Test émojis 🚀 and symbols €£¥"},
                {"name": "Date", "value": "Thu, 9 Nov 2023 12:00:00 -0800"},
                {"name": "Message-ID", "value": "<utf8test@example.com>"}
            ],
            "body": {
                "size": 30,
                "data": "SGVsbG8g8J+agCDwn5GN4oCN8J+SuyBXb3JsZCE="  # "Hello 🚀 👍‍💻 World!"
            }
        }
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify UTF-8 characters preserved
    assert "José García" in result.data["from"][0]["name"]
    assert "François Müller" in result.data["to"][0]["name"]
    assert "émojis 🚀" in result.data["subject"]
    assert "€" in result.data["subject"]


# ============================================================================
# Gmail → JMAP Minimal Tests
# ============================================================================


def test_gmail_to_jmap_minimal_end_to_end(runtime, transforms_dir):
    """Test Gmail → JMAP Minimal transform end-to-end."""
    transform_meta = transforms_dir / "gmail_to_jmap_minimal" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "gmail_to_jmap_minimal" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "gmail_to_jmap_minimal" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify core metadata fields
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]
    assert result.data["from"] == expected_data["from"]

    # Verify NO body content (Minimal format)
    assert "body" not in result.data
    assert "bodyStructure" not in result.data
    assert "bodyValues" not in result.data

    # Verify blobId exists for external body reference
    assert "blobId" in result.data
    assert result.data["blobId"] is not None


# ============================================================================
# Exchange → JMAP Full Tests
# ============================================================================


def test_exchange_to_jmap_full_end_to_end(runtime, transforms_dir):
    """Test Exchange → JMAP Full transform end-to-end."""
    transform_meta = transforms_dir / "exchange_to_jmap_full" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "exchange_to_jmap_full" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "exchange_to_jmap_full" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify core fields
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]
    assert result.data["from"] == expected_data["from"]
    assert result.data["to"] == expected_data["to"]

    # Verify Full format fields
    assert "bodyStructure" in result.data
    assert "bodyValues" in result.data


def test_exchange_to_jmap_full_with_categories(runtime, transforms_dir):
    """Test Exchange → JMAP Full with categories and flags."""
    transform_meta = transforms_dir / "exchange_to_jmap_full" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "exchange_test",
        "conversationId": "AAQkAGI2TAABj5P2QAAA=",
        "subject": "Test Categories",
        "bodyPreview": "Test",
        "from": {
            "emailAddress": {
                "name": "Test User",
                "address": "test@example.com"
            }
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "name": "Recipient",
                    "address": "recipient@example.com"
                }
            }
        ],
        "sentDateTime": "2023-11-09T20:00:00Z",
        "receivedDateTime": "2023-11-09T20:00:15Z",
        "body": {
            "contentType": "html",
            "content": "<html><body>Test</body></html>"
        },
        "internetMessageId": "<test@example.com>",
        "internetMessageHeaders": [
            {"name": "From", "value": "test@example.com"},
            {"name": "To", "value": "recipient@example.com"}
        ],
        "isRead": True,
        "isDraft": False,
        "flag": {
            "flagStatus": "flagged"
        },
        "importance": "high",
        "categories": ["Work", "Important", "Follow-up"]
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify flags mapped to keywords
    assert result.data["keywords"]["$seen"] is True
    assert result.data["keywords"]["$flagged"] is True
    assert result.data["keywords"]["$draft"] is False

    # Verify mailboxIds from categories
    assert "Work" in result.data["mailboxIds"]
    assert "Important" in result.data["mailboxIds"]


# ============================================================================
# Exchange → JMAP Lite Tests
# ============================================================================


def test_exchange_to_jmap_lite_end_to_end(runtime, transforms_dir):
    """Test Exchange → JMAP Lite transform end-to-end."""
    transform_meta = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify core fields
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]

    # Verify Lite format
    assert "body" in result.data
    assert isinstance(result.data["body"], dict)
    assert "bodyStructure" not in result.data


def test_exchange_to_jmap_lite_html_vs_text(runtime, transforms_dir):
    """Test Exchange → JMAP Lite with both text and HTML bodies."""
    transform_meta = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    # Test with HTML body
    input_html = {
        "id": "html_test",
        "conversationId": "conv123",
        "subject": "HTML Test",
        "bodyPreview": "Preview",
        "from": {"emailAddress": {"name": "Sender", "address": "sender@example.com"}},
        "toRecipients": [{"emailAddress": {"name": "Recipient", "address": "recipient@example.com"}}],
        "sentDateTime": "2023-11-09T20:00:00Z",
        "receivedDateTime": "2023-11-09T20:00:15Z",
        "body": {
            "contentType": "html",
            "content": "<html><body><p>HTML content</p></body></html>"
        },
        "internetMessageId": "<html_test@example.com>",
        "internetMessageHeaders": []
    }

    result_html = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_html,
        validate_input=True,
        validate_output=True,
    )

    assert "html" in result_html.data["body"]
    assert "HTML content" in result_html.data["body"]["html"]

    # Test with text body
    input_text = {
        **input_html,
        "id": "text_test",
        "body": {
            "contentType": "text",
            "content": "Plain text content"
        }
    }

    result_text = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_text,
        validate_input=True,
        validate_output=True,
    )

    assert "text" in result_text.data["body"]
    assert "Plain text content" in result_text.data["body"]["text"]


# ============================================================================
# Exchange → JMAP Minimal Tests
# ============================================================================


def test_exchange_to_jmap_minimal_end_to_end(runtime, transforms_dir):
    """Test Exchange → JMAP Minimal transform end-to-end."""
    transform_meta = transforms_dir / "exchange_to_jmap_minimal" / "1.0.0" / "spec.meta.yaml"
    input_file = transforms_dir / "exchange_to_jmap_minimal" / "1.0.0" / "tests" / "input.json"
    expected_file = transforms_dir / "exchange_to_jmap_minimal" / "1.0.0" / "tests" / "expected.json"

    with open(input_file) as f:
        input_data = json.load(f)

    with open(expected_file) as f:
        expected_data = json.load(f)

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify metadata only
    assert result.data["id"] == expected_data["id"]
    assert result.data["subject"] == expected_data["subject"]

    # Verify NO body content
    assert "body" not in result.data
    assert "bodyStructure" not in result.data

    # Verify blobId for external reference
    assert "blobId" in result.data


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_gmail_invalid_input_missing_required_field(runtime, transforms_dir):
    """Test Gmail transform fails gracefully with missing required field."""
    transform_meta = transforms_dir / "gmail_to_jmap_full" / "1.0.0" / "spec.meta.yaml"

    # Missing required 'payload' field
    invalid_input = {
        "id": "test123",
        "threadId": "thread123"
        # Missing 'payload' field
    }

    with pytest.raises(ValidationError) as exc_info:
        runtime.execute(
            transform_meta_path=transform_meta,
            input_data=invalid_input,
            validate_input=True,
        )

    # Check the detailed errors attribute which contains validation messages
    assert any("required" in str(err).lower() for err in exc_info.value.errors)


def test_exchange_invalid_input_wrong_type(runtime, transforms_dir):
    """Test Exchange transform fails with wrong field type."""
    transform_meta = transforms_dir / "exchange_to_jmap_full" / "1.0.0" / "spec.meta.yaml"

    # Wrong type for 'toRecipients' (should be array)
    invalid_input = {
        "id": "test123",
        "subject": "Test",
        "from": {"emailAddress": {"name": "Sender", "address": "sender@example.com"}},
        "toRecipients": "not-an-array",  # Wrong type
        "sentDateTime": "2023-11-09T20:00:00Z",
        "receivedDateTime": "2023-11-09T20:00:15Z",
        "body": {"contentType": "text", "content": "Test"},
        "internetMessageId": "<test@example.com>",
        "internetMessageHeaders": []
    }

    with pytest.raises(ValidationError):
        runtime.execute(
            transform_meta_path=transform_meta,
            input_data=invalid_input,
            validate_input=True,
        )


def test_transform_with_malformed_base64(runtime, transforms_dir):
    """Test Gmail transform handles malformed base64 gracefully."""
    transform_meta = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "test123",
        "threadId": "thread123",
        "labelIds": ["INBOX"],
        "snippet": "Test",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test"},
                {"name": "Date", "value": "Thu, 9 Nov 2023 12:00:00 -0800"},
                {"name": "Message-ID", "value": "<test@example.com>"}
            ],
            "body": {
                "size": 10,
                "data": "not-valid-base64!!!"  # Malformed base64
            }
        }
    }

    # Should either fail gracefully or handle the error
    try:
        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=True,
            validate_output=False,  # Don't validate output since transform may fail
        )
        # If it succeeds, body should be present (even if empty or error message)
        assert "body" in result.data
    except Exception as e:
        # Acceptable to fail on malformed input
        assert "base64" in str(e).lower() or "decode" in str(e).lower()


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_gmail_empty_headers_array(runtime, transforms_dir):
    """Test Gmail transform with empty headers array."""
    transform_meta = transforms_dir / "gmail_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "test123",
        "threadId": "thread123",
        "labelIds": ["INBOX"],
        "snippet": "Test",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [],  # Empty headers
            "body": {
                "size": 4,
                "data": "VGVzdA=="  # "Test"
            }
        }
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Should still produce valid output with null/empty values
    assert result.data["id"] == "test123"
    assert result.data["from"] is None or result.data["from"] == []
    assert result.data["to"] is None or result.data["to"] == []


def test_exchange_null_recipients(runtime, transforms_dir):
    """Test Exchange transform with empty recipient arrays."""
    transform_meta = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    input_data = {
        "id": "test123",
        "conversationId": "conv123",
        "subject": "Test",
        "bodyPreview": "Preview",
        "from": {"emailAddress": {"name": "Sender", "address": "sender@example.com"}},
        "toRecipients": [],  # Empty array instead of null (schema requires array type)
        "ccRecipients": [],
        "bccRecipients": [],
        "sentDateTime": "2023-11-09T20:00:00Z",
        "receivedDateTime": "2023-11-09T20:00:15Z",
        "body": {"contentType": "text", "content": "Test"},
        "internetMessageId": "<test@example.com>",
        "internetMessageHeaders": []
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Should handle empty recipient arrays gracefully
    assert result.data["to"] is None or result.data["to"] == []
    assert result.data["cc"] is None or result.data["cc"] == []


def test_gmail_very_long_subject(runtime, transforms_dir):
    """Test Gmail transform with very long subject line (edge case)."""
    transform_meta = transforms_dir / "gmail_to_jmap_minimal" / "1.0.0" / "spec.meta.yaml"

    long_subject = "A" * 10000  # 10KB subject line

    input_data = {
        "id": "test123",
        "threadId": "thread123",
        "labelIds": ["INBOX"],
        "snippet": "Test",
        "internalDate": "1699564800000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": long_subject},
                {"name": "Date", "value": "Thu, 9 Nov 2023 12:00:00 -0800"},
                {"name": "Message-ID", "value": "<test@example.com>"}
            ],
            "body": {
                "size": 4,
                "data": "VGVzdA=="
            }
        }
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Should preserve long subject
    assert len(result.data["subject"]) == 10000
    assert result.data["subject"] == long_subject


# ============================================================================
# Performance / Stress Tests
# ============================================================================


def test_transform_with_many_recipients(runtime, transforms_dir):
    """Test Exchange transform with large number of recipients."""
    transform_meta = transforms_dir / "exchange_to_jmap_lite" / "1.0.0" / "spec.meta.yaml"

    # Create 100 recipients
    recipients = [
        {"emailAddress": {"name": f"User{i}", "address": f"user{i}@example.com"}}
        for i in range(100)
    ]

    input_data = {
        "id": "test_many_recipients",
        "conversationId": "conv123",
        "subject": "Mass email",
        "bodyPreview": "Test",
        "from": {"emailAddress": {"name": "Sender", "address": "sender@example.com"}},
        "toRecipients": recipients,
        "sentDateTime": "2023-11-09T20:00:00Z",
        "receivedDateTime": "2023-11-09T20:00:15Z",
        "body": {"contentType": "text", "content": "Test"},
        "internetMessageId": "<test@example.com>",
        "internetMessageHeaders": []
    }

    result = runtime.execute(
        transform_meta_path=transform_meta,
        input_data=input_data,
        validate_input=True,
        validate_output=True,
    )

    # Verify all recipients transformed
    assert len(result.data["to"]) == 100
    assert result.data["to"][0]["email"] == "user0@example.com"
    assert result.data["to"][99]["email"] == "user99@example.com"


# ============================================================================
# Summary Statistics
# ============================================================================


def test_all_transforms_summary(runtime, transforms_dir):
    """Summary test: Verify all 6 transforms can execute successfully."""
    transforms = [
        "gmail_to_jmap_full",
        "gmail_to_jmap_lite",
        "gmail_to_jmap_minimal",
        "exchange_to_jmap_full",
        "exchange_to_jmap_lite",
        "exchange_to_jmap_minimal",
    ]

    results = {}

    for transform_id in transforms:
        transform_meta = transforms_dir / transform_id / "1.0.0" / "spec.meta.yaml"
        input_file = transforms_dir / transform_id / "1.0.0" / "tests" / "input.json"

        with open(input_file) as f:
            input_data = json.load(f)

        result = runtime.execute(
            transform_meta_path=transform_meta,
            input_data=input_data,
            validate_input=True,
            validate_output=True,
        )

        results[transform_id] = {
            "success": True,
            "execution_time_ms": result.execution_time_ms,
            "output_size": len(json.dumps(result.data)),
        }

    # Verify all 6 transforms succeeded
    assert len(results) == 6
    for transform_id, result_info in results.items():
        assert result_info["success"] is True
        assert result_info["execution_time_ms"] > 0

    # Print summary (for debugging)
    print("\n=== Transform Execution Summary ===")
    for transform_id, info in results.items():
        print(f"{transform_id}: {info['execution_time_ms']:.2f}ms, {info['output_size']} bytes")
