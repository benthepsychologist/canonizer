# Canonizer API Reference

Canonizer is a pure JSON transformation library: `raw_json + transform_id → canonical_json`

## Core API

### `canonicalize()`

Transform raw JSON document to canonical format.

```python
def canonicalize(
    raw_document: dict,
    *,
    transform_id: str,
    schemas_dir: str | Path | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> dict
```

**Parameters:**
- `raw_document` (dict): Source JSON document
- `transform_id` (str): Transform to use
  - Registry-style: `"email/gmail_to_jmap_lite@1.0.0"`
  - Full path: `"transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"`
- `schemas_dir` (str | Path | None): Schema directory (default: "schemas")
- `validate_input` (bool): Validate against source schema (default: True)
- `validate_output` (bool): Validate against canonical schema (default: True)

**Returns:** dict - Canonical JSON document

**Raises:**
- `ValidationError` - If validation fails
- `FileNotFoundError` - If transform/schema not found
- `ValueError` - If checksum verification fails

**Example:**
```python
from canonizer import canonicalize

canonical = canonicalize(
    raw_gmail_message,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)
```

### `run_batch()`

Transform multiple documents in batch.

```python
def run_batch(
    documents: list[dict],
    *,
    transform_id: str,
    schemas_dir: str | Path | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> list[dict]
```

**Parameters:** Same as `canonicalize()` except first parameter is list of documents

**Returns:** list[dict] - List of canonical JSON documents

**Example:**
```python
from canonizer import run_batch

canonicals = run_batch(
    raw_emails,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)
```

## Convenience Functions

### `canonicalize_email_from_gmail()`

Transform Gmail API message to canonical JMAP format.

```python
def canonicalize_email_from_gmail(
    raw_email: dict,
    *,
    format: str = "lite",
    schemas_dir: str | Path | None = None,
) -> dict
```

**Parameters:**
- `raw_email` (dict): Raw Gmail API message (users.messages.get response)
- `format` (str): Canonical format - "full", "lite", or "minimal" (default: "lite")
- `schemas_dir` (str | Path | None): Schema directory (default: "schemas")

**Example:**
```python
from canonizer import canonicalize_email_from_gmail

canonical = canonicalize_email_from_gmail(raw_gmail_message, format="lite")
```

### `canonicalize_email_from_exchange()`

Transform Microsoft Graph API message to canonical JMAP format.

```python
def canonicalize_email_from_exchange(
    raw_email: dict,
    *,
    format: str = "lite",
    schemas_dir: str | Path | None = None,
) -> dict
```

**Parameters:** Same as `canonicalize_email_from_gmail()`

**Example:**
```python
from canonizer import canonicalize_email_from_exchange

canonical = canonicalize_email_from_exchange(raw_exchange_message, format="full")
```

### `canonicalize_form_response()`

Transform Google Forms response to canonical form_response format.

```python
def canonicalize_form_response(
    raw_form: dict,
    *,
    schemas_dir: str | Path | None = None,
) -> dict
```

**Parameters:**
- `raw_form` (dict): Raw Google Forms API response
- `schemas_dir` (str | Path | None): Schema directory (default: "schemas")

**Example:**
```python
from canonizer import canonicalize_form_response

canonical = canonicalize_form_response(raw_google_forms_response)
```

## Error Handling

```python
from canonizer import canonicalize
from canonizer.core.validator import ValidationError

try:
    canonical = canonicalize(raw_doc, transform_id="...")
except ValidationError as e:
    print(f"Validation failed: {e.errors}")
except FileNotFoundError as e:
    print(f"Transform not found: {e}")
except Exception as e:
    print(f"Transform failed: {e}")
```

## Batch Processing with Error Collection

```python
results = []
errors = []

for doc in documents:
    try:
        canonical = canonicalize(doc, transform_id=transform_id)
        results.append(canonical)
    except Exception as e:
        errors.append({"doc": doc, "error": str(e)})

print(f"Processed: {len(results)}, Failed: {len(errors)}")
```

## Integration with lorchestra

Canonizer is a pure transformation library. Orchestration (events, BigQuery, etc.) happens in lorchestra jobs:

```python
# In lorchestra job (separate package)
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event
from google.cloud import bigquery

def canonicalize_email_job():
    # 1. Query raw events from BQ
    bq = bigquery.Client()
    rows = bq.query("SELECT * FROM raw_events WHERE event_type = 'email.gmail.raw'").result()

    # 2. Transform each (pure function call)
    for row in rows:
        canonical = canonicalize(row.payload, transform_id="email/gmail_to_jmap_lite@1.0.0")

        # 3. Emit canonical event
        emit_event("email.canonicalized", payload=canonical, metadata={...})
```

## Available Transforms

| Transform ID | Source | Target | Format |
|--------------|--------|--------|--------|
| `email/gmail_to_jmap_full@1.0.0` | Gmail API | JMAP | Full (RFC 8621) |
| `email/gmail_to_jmap_lite@1.0.0` | Gmail API | JMAP | Lite (simplified) |
| `email/gmail_to_jmap_minimal@1.0.0` | Gmail API | JMAP | Minimal (metadata) |
| `email/exchange_to_jmap_full@1.0.0` | Graph API | JMAP | Full (RFC 8621) |
| `email/exchange_to_jmap_lite@1.0.0` | Graph API | JMAP | Lite (simplified) |
| `email/exchange_to_jmap_minimal@1.0.0` | Graph API | JMAP | Minimal (metadata) |
| `forms/google_forms_to_canonical@1.0.0` | Google Forms | form_response | Standard |

## See Also

- [README.md](../README.md) - Quick start and examples
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [Core Runtime](../canonizer/core/runtime.py) - Internal transform engine
