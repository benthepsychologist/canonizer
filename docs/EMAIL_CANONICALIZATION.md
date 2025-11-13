# Email Canonicalization Standards (JMAP-based)

**The Definitive Guide to Email Transformation in Canonizer**

Version: 1.0
Last Updated: 2025-11-13
Status: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Why JMAP? (RFC 8621)](#why-jmap-rfc-8621)
3. [Canonical Formats Comparison](#canonical-formats-comparison)
4. [Source Formats](#source-formats)
5. [Transform Matrix](#transform-matrix)
6. [Usage Examples](#usage-examples)
7. [Field Mapping Tables](#field-mapping-tables)
8. [Storage Strategy Guide](#storage-strategy-guide)
9. [Links & References](#links--references)

---

## Overview

### What is Email Canonicalization?

Email canonicalization is the process of transforming emails from provider-specific formats (Gmail, Exchange, etc.) into standardized canonical formats. This enables:

- **Interoperability**: Work with emails from any provider using one standard
- **Storage Optimization**: Choose storage format based on your needs
- **Data Portability**: Move data between systems without vendor lock-in
- **Analytics**: Query emails consistently regardless of source

### The Problem

Different email providers use different JSON structures:

- **Gmail API**: Nested `payload.headers` arrays, base64url encoded bodies, MIME parts
- **Microsoft Graph**: Direct properties, HTML/text body objects, flat structure
- **Others**: Each with their own quirks

Applications need to handle all these formats, leading to:
- Duplicate transformation logic
- Provider-specific code paths
- Inconsistent data models
- Difficult migrations

### The Solution

**Canonizer provides:**

1. **Source Schemas**: Accurate representations of provider APIs (Gmail, Exchange)
2. **Canonical Targets**: Three JMAP-based formats for different use cases
3. **Transforms**: Vetted JSONata transforms (2 sources × 3 targets = 6 transforms)
4. **Registry**: Discoverable, versioned, with CI validation

---

## Why JMAP? (RFC 8621)

### What is JMAP?

**JMAP** (JSON Meta Application Protocol) is an **IETF Standards Track** specification (RFC 8621, published 2019) that defines how to represent emails as JSON.

**Key Facts:**
- **Authority**: Internet Engineering Task Force (IETF)
- **Status**: Standards Track (consensus of IETF community)
- **Adoption**: Fastmail, growing adoption across email infrastructure
- **Specification**: https://datatracker.ietf.org/doc/html/rfc8621

### Why JMAP is Authoritative

1. **IETF Standards Track** - Official internet standard, not vendor-specific
2. **JSON-native** - Designed specifically for JSON APIs (vs retrofitting MIME)
3. **Production-proven** - Battle-tested by Fastmail and others
4. **Comprehensive** - Handles all email complexity (MIME, encodings, threading, attachments)
5. **Future-proof** - Active working group, ongoing updates
6. **Transformation-friendly** - Structured for machine processing, not just display

### JMAP vs Alternatives

| Standard | Format | Use Case | Limitation |
|----------|--------|----------|------------|
| **RFC 5322** | Text (MIME) | Email transmission | Not JSON, requires parsing |
| **Schema.org EmailMessage** | JSON-LD | Gmail action buttons | Limited to UI enhancements |
| **JMAP (RFC 8621)** | JSON | Full email representation | None - perfect for canonicalization |

### JMAP Design Principles

1. **Structured Email Addresses**
   ```json
   {"name": "John Doe", "email": "john@example.com"}
   ```
   Instead of `"John Doe <john@example.com>"` strings

2. **ISO 8601 Timestamps**
   ```json
   "receivedAt": "2023-11-09T20:00:15Z"
   ```
   Not epoch milliseconds

3. **Keywords as Objects**
   ```json
   {"$seen": true, "$flagged": false, "work": true}
   ```
   Standard IMAP flags + custom labels

4. **Separation of Structure from Content**
   - `bodyStructure`: MIME tree structure
   - `bodyValues`: Decoded text content map
   - `textBody` / `htmlBody`: References to parts

---

## Canonical Formats Comparison

Canonizer provides **three JMAP-based canonical formats** optimized for different use cases.

### Quick Comparison Table

| Format | Properties | Storage | Use Case | Body Content |
|--------|-----------|---------|----------|--------------|
| **JMAP Full** | 26 | ~50-200KB | Full archival, compliance, forensics | Complete MIME structure inline |
| **JMAP Lite** | 22 | ~10-50KB | App display, most email clients | text/html inline |
| **JMAP Minimal** | 21 | ~1-5KB | Search indexes, analytics, warehouses | Referenced by blobId |

### Format Details

#### 1. JMAP Full (`org.canonical/email_jmap_full/jsonschema/1-0-0`)

**Complete RFC 8621 Email object** with full MIME structure preservation.

**Includes:**
- All RFC 8621 Email fields
- Complete `bodyStructure` (MIME tree)
- `bodyValues` map (partId → decoded content)
- `textBody`, `htmlBody`, `attachments` arrays
- All headers preserved
- Full threading (messageId, inReplyTo, references)
- Keywords and mailboxIds

**Use For:**
- ✅ Full email archival
- ✅ Compliance / legal hold
- ✅ Forensics and auditing
- ✅ Complete message reconstruction
- ✅ Advanced MIME processing

**Trade-offs:**
- ✅ Most complete representation
- ⚠️ Largest storage footprint
- ⚠️ Most complex structure

**Storage:** ~50-200KB per email (bodies inline)

**Schema:** `schemas/org.canonical/email_jmap_full/jsonschema/1-0-0.json`

---

#### 2. JMAP Lite (`org.canonical/email_jmap_lite/jsonschema/1-0-0`)

**Simplified JMAP format for 80% of use cases** with inline body content.

**Includes:**
- Core email metadata (from, to, subject, dates)
- Simplified `body` object: `{text, html}`
- Attachments metadata (filename, size, mimeType, blobId)
- Threading fields (messageId, inReplyTo, references)
- Keywords and labels
- Importance field

**Excludes:**
- Complex MIME structure (bodyStructure)
- bodyValues map
- Full headers array
- mailboxIds (uses labels instead)

**Use For:**
- ✅ Email client display
- ✅ Mobile apps
- ✅ Web interfaces
- ✅ Most business applications
- ✅ 80% of email processing needs

**Trade-offs:**
- ✅ Simpler structure, easier to work with
- ✅ Much smaller than Full
- ⚠️ Can't reconstruct exact MIME structure
- ⚠️ Limited header access

**Storage:** ~10-50KB per email

**Schema:** `schemas/org.canonical/email_jmap_lite/jsonschema/1-0-0.json`

---

#### 3. JMAP Minimal (`org.canonical/email_jmap_minimal/jsonschema/1-0-0`)

**Metadata-only format** with body content referenced separately.

**Includes:**
- All email metadata (from, to, subject, dates, preview)
- Threading fields
- Keywords and labels
- Importance
- `blobId` for fetching full message from blob storage
- Attachment count (not full metadata)

**Excludes:**
- Body content (inline text/html)
- Full attachment metadata
- MIME structure
- Headers

**Use For:**
- ✅ Search indexes (Elasticsearch, etc.)
- ✅ Data warehouses / analytics
- ✅ High-volume processing
- ✅ Systems where body is stored separately (S3, object storage)
- ✅ Metadata-only queries

**Trade-offs:**
- ✅ Smallest storage footprint
- ✅ Fastest to process
- ✅ Perfect for indexing
- ⚠️ Requires separate body retrieval
- ⚠️ Can't display email without additional fetch

**Storage:** ~1-5KB per email (bodies in S3/blob storage)

**Schema:** `schemas/org.canonical/email_jmap_minimal/jsonschema/1-0-0.json`

---

## Source Formats

### Gmail API v1 (`com.google/gmail_email/jsonschema/1-0-0`)

**Structure:**
```json
{
  "id": "string",
  "threadId": "string",
  "labelIds": ["INBOX", "STARRED"],
  "snippet": "preview text",
  "internalDate": "1699545600000",
  "payload": {
    "headers": [
      {"name": "From", "value": "sender@example.com"},
      {"name": "To", "value": "recipient@example.com"}
    ],
    "mimeType": "multipart/alternative",
    "parts": [
      {
        "partId": "0",
        "mimeType": "text/plain",
        "body": {"data": "base64url encoded content"}
      }
    ]
  }
}
```

**Key Characteristics:**
- Nested `payload.headers` array structure
- Base64url encoded body content
- MIME parts hierarchy
- Epoch milliseconds timestamps (string format)
- Label-based organization

**Documentation:** https://developers.google.com/gmail/api/reference/rest/v1/users.messages

**Schema:** `schemas/com.google/gmail_email/jsonschema/1-0-0.json`

---

### Microsoft Graph API (`com.microsoft/exchange_email/jsonschema/1-0-0`)

**Structure:**
```json
{
  "id": "AAMkAGI2THVSAAA=",
  "subject": "Email subject",
  "from": {
    "emailAddress": {
      "name": "Sender Name",
      "address": "sender@example.com"
    }
  },
  "toRecipients": [
    {"emailAddress": {"name": "Recipient", "address": "recipient@example.com"}}
  ],
  "receivedDateTime": "2023-11-09T20:00:15Z",
  "body": {
    "contentType": "html",
    "content": "<html>...</html>"
  },
  "internetMessageHeaders": [
    {"name": "From", "value": "sender@example.com"}
  ]
}
```

**Key Characteristics:**
- Direct property access (flatter structure)
- Already ISO 8601 timestamps
- Structured recipient objects
- Body with contentType (text vs html)
- Categories instead of labels

**Documentation:** https://learn.microsoft.com/en-us/graph/api/resources/message

**Schema:** `schemas/com.microsoft/exchange_email/jsonschema/1-0-0.json`

---

## Transform Matrix

Canonizer provides **6 transforms** covering all combinations:

| Source ↓ / Target → | JMAP Full | JMAP Lite | JMAP Minimal |
|---------------------|-----------|-----------|--------------|
| **Gmail API** | `email/gmail_to_jmap_full@1.0.0` | `email/gmail_to_jmap_lite@1.0.0` | `email/gmail_to_jmap_minimal@1.0.0` |
| **Exchange/Graph** | `email/exchange_to_jmap_full@1.0.0` | `email/exchange_to_jmap_lite@1.0.0` | `email/exchange_to_jmap_minimal@1.0.0` |

### Transform Features

All transforms handle:
- ✅ Email address parsing (`"Name <email>"` → `{name, email}`)
- ✅ Timestamp conversion (epoch ms or ISO 8601 → ISO 8601)
- ✅ Header extraction and parsing
- ✅ Threading fields (messageId, inReplyTo, references)
- ✅ Keywords/flags mapping (IMAP standard + custom)
- ✅ Attachment handling
- ✅ Body encoding (base64url decoding for Gmail)

### Using Transforms

#### From Registry
```bash
# List available email transforms
can registry search --id email/

# Pull a transform
can registry pull email/gmail_to_jmap_lite@1.0.0

# Use it
can transform run \
  --meta ~/.cache/canonizer/registry/.../spec.meta.yaml \
  --input gmail_message.json \
  --output canonical_email.json
```

#### Locally
```bash
can transform run \
  --meta transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml \
  --input gmail_message.json \
  --output canonical_email.json
```

---

## Usage Examples

### Example 1: Email Client (JMAP Lite)

**Scenario:** Building an email client that displays emails from Gmail and Exchange.

**Recommended Format:** JMAP Lite

**Why:** Need body content for display, don't need full MIME structure.

**Workflow:**

1. **Fetch from Gmail:**
   ```bash
   # Gmail API returns message
   curl 'https://gmail.googleapis.com/gmail/v1/users/me/messages/18c5f2e8a9b4d7f3' \
     > gmail_message.json

   # Transform to JMAP Lite
   can transform run \
     --meta transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml \
     --input gmail_message.json \
     --output canonical.json

   # Store in your database
   psql -c "INSERT INTO emails ..." canonical.json
   ```

2. **Fetch from Exchange:**
   ```bash
   # Graph API returns message
   curl 'https://graph.microsoft.com/v1.0/me/messages/AAMkAGI2THVSAAA=' \
     > exchange_message.json

   # Transform to JMAP Lite (same target format!)
   can transform run \
     --meta transforms/email/exchange_to_jmap_lite/1.0.0/spec.meta.yaml \
     --input exchange_message.json \
     --output canonical.json

   # Store in same table - identical schema
   psql -c "INSERT INTO emails ..." canonical.json
   ```

3. **Display in UI:**
   ```javascript
   // All emails have same structure now
   const email = await db.emails.findById(id);

   return (
     <Email>
       <From>{email.from[0].name} &lt;{email.from[0].email}&gt;</From>
       <Subject>{email.subject}</Subject>
       <Body dangerouslySetInnerHTML={{__html: email.body.html || email.body.text}} />
       <Attachments>{email.attachments.map(att => <Attachment {...att} />)}</Attachments>
     </Email>
   );
   ```

**Storage:** ~10-50KB per email in database

---

### Example 2: Search Index (JMAP Minimal)

**Scenario:** Building email search with Elasticsearch, bodies stored in S3.

**Recommended Format:** JMAP Minimal

**Why:** Only need metadata for search index. Store full body in blob storage separately.

**Workflow:**

1. **Transform to JMAP Minimal:**
   ```bash
   can transform run \
     --meta transforms/email/gmail_to_jmap_minimal/1.0.0/spec.meta.yaml \
     --input gmail_message.json \
     --output minimal.json
   ```

2. **Store Body in S3:**
   ```bash
   # Extract blobId from minimal.json
   BLOB_ID=$(jq -r '.blobId' minimal.json)

   # Upload original to S3
   aws s3 cp gmail_message.json s3://email-blobs/${BLOB_ID}.json
   ```

3. **Index Metadata in Elasticsearch:**
   ```bash
   curl -X POST 'http://localhost:9200/emails/_doc' \
     -H 'Content-Type: application/json' \
     -d @minimal.json
   ```

4. **Search:**
   ```json
   GET /emails/_search
   {
     "query": {
       "bool": {
         "must": [
           {"match": {"subject": "Q4 report"}},
           {"term": {"from.email": "sarah.smith@company.com"}}
         ],
         "filter": {
           "range": {"receivedAt": {"gte": "2023-11-01"}}
         }
       }
     }
   }
   ```

5. **Retrieve Full Email:**
   ```bash
   # Get minimal metadata from search results
   BLOB_ID=$(echo $search_result | jq -r '.blobId')

   # Fetch full body from S3
   aws s3 cp s3://email-blobs/${BLOB_ID}.json email.json
   ```

**Storage:** ~1-5KB per email in Elasticsearch + full email in S3

---

### Example 3: Compliance Archive (JMAP Full)

**Scenario:** Legal hold / compliance archival with exact message reconstruction.

**Recommended Format:** JMAP Full

**Why:** Need complete MIME structure, all headers, exact representation.

**Workflow:**

1. **Transform to JMAP Full:**
   ```bash
   can transform run \
     --meta transforms/email/gmail_to_jmap_full/1.0.0/spec.meta.yaml \
     --input gmail_message.json \
     --output archive.json
   ```

2. **Validate Completeness:**
   ```bash
   can validate run \
     --schema schemas/org.canonical/email_jmap_full/jsonschema/1-0-0.json \
     --data archive.json
   ```

3. **Store in Immutable Archive:**
   ```python
   # Python example
   import json
   import hashlib
   from datetime import datetime

   with open('archive.json') as f:
       email = json.load(f)

   # Calculate content hash for integrity
   content_hash = hashlib.sha256(json.dumps(email, sort_keys=True).encode()).hexdigest()

   # Store with metadata
   archive_record = {
       "email_id": email['id'],
       "archived_at": datetime.utcnow().isoformat() + 'Z',
       "content_hash": content_hash,
       "jmap_full": email
   }

   # Write to immutable storage (WORM, S3 Glacier, etc.)
   db.legal_hold.insert_one(archive_record)
   ```

**Storage:** ~50-200KB per email

---

## Field Mapping Tables

### Gmail → JMAP Full

| Gmail Field | JMAP Full Field | Transformation |
|-------------|----------------|----------------|
| `id` | `id` | Direct copy |
| `threadId` | `threadId` | Direct copy |
| `internalDate` | `receivedAt` | Epoch ms → ISO 8601 |
| `payload.headers[name="Date"]` | `sentAt` | Parse → ISO 8601 |
| `payload.headers[name="From"]` | `from` | Parse `"Name <email>"` → `[{name, email}]` |
| `payload.headers[name="To"]` | `to` | Parse list → array of `{name, email}` |
| `payload.headers[name="Subject"]` | `subject` | Direct copy |
| `payload.headers[name="Message-ID"]` | `messageId` | Wrap in array: `[value]` |
| `payload` | `bodyStructure` | Convert MessagePart tree → EmailBodyPart |
| `payload.parts[mimeType="text/*"].body.data` | `bodyValues[partId]` | Base64url decode → `{value, ...}` |
| `labelIds` | `keywords` | Map to `{$seen, $flagged, ...}` |
| `labelIds` | `mailboxIds` | Array → object `{label: true}` |

### Exchange → JMAP Full

| Exchange Field | JMAP Full Field | Transformation |
|----------------|----------------|----------------|
| `id` | `id` | Direct copy |
| `conversationId` | `threadId` | Direct copy |
| `receivedDateTime` | `receivedAt` | Direct copy (already ISO 8601) |
| `sentDateTime` | `sentAt` | Direct copy |
| `from.emailAddress` | `from` | Convert `{name, address}` → `[{name, email}]` |
| `toRecipients` | `to` | Map array, rename `address` → `email` |
| `subject` | `subject` | Direct copy |
| `internetMessageId` | `messageId` | Wrap in array |
| `body` | `bodyStructure` | Build EmailBodyPart from body object |
| `body.content` | `bodyValues["0"]` | Wrap in `{value, ...}` object |
| `isRead` | `keywords.$seen` | Direct copy |
| `categories` | `mailboxIds` | Array → object `{cat: true}` |

### Common Transformations

#### Email Address Parsing
```
Input:  "Sarah Smith <sarah.smith@company.com>"
Output: {"name": "Sarah Smith", "email": "sarah.smith@company.com"}
```

#### Timestamp Conversion (Gmail)
```
Input:  "1699545600000" (string epoch ms)
Output: "2023-11-09T20:00:00Z" (ISO 8601)
```

#### Keywords Mapping (Gmail)
```
Input:  ["INBOX", "STARRED", "UNREAD"]
Output: {"$seen": false, "$flagged": true}

Logic:
- UNREAD in labels → $seen: false
- NOT UNREAD → $seen: true
- STARRED → $flagged: true
- DRAFT → $draft: true
```

---

## Storage Strategy Guide

### When to Use Each Format

#### Use JMAP Full When:
- ✅ **Legal/compliance requirements** - Need exact message reconstruction
- ✅ **Long-term archival** - Messages won't change, completeness matters
- ✅ **Forensic analysis** - Need all headers, exact MIME structure
- ✅ **Migration** - Moving between systems, can't lose data
- ✅ **Audit trails** - Need to prove exact message content

**Don't use when:**
- ❌ High-volume systems (storage costs)
- ❌ Real-time processing (complexity overhead)
- ❌ Display-only applications (overkill)

---

#### Use JMAP Lite When:
- ✅ **Email clients** - Display messages to users
- ✅ **Web/mobile apps** - Need body + attachments
- ✅ **Business applications** - Most email processing
- ✅ **Moderate volume** - Thousands to millions of emails
- ✅ **Quick access** - Body content inline, no extra fetch

**Don't use when:**
- ❌ Need exact MIME reconstruction
- ❌ Very high volume (billions of emails)
- ❌ Metadata-only queries (wasted storage)

---

#### Use JMAP Minimal When:
- ✅ **Search indexes** - Elasticsearch, Solr, etc.
- ✅ **Data warehouses** - Analytics on metadata
- ✅ **High volume** - Billions of emails
- ✅ **Separate body storage** - Bodies in S3/blob storage
- ✅ **Fast queries** - Metadata-only, no body parsing

**Don't use when:**
- ❌ Need to display email immediately
- ❌ Body content required for processing
- ❌ Can't do additional fetches

---

### Hybrid Storage Strategies

#### Strategy 1: Hot/Cold Storage
```
Recent emails (< 30 days):  JMAP Lite in PostgreSQL
Archive (> 30 days):         JMAP Minimal in DB, bodies in S3 Glacier
```

#### Strategy 2: Tiered by Importance
```
Starred/Important:  JMAP Full
Regular:            JMAP Lite
Bulk/Automated:     JMAP Minimal
```

#### Strategy 3: Use Case Split
```
Display layer:      JMAP Lite in PostgreSQL
Search index:       JMAP Minimal in Elasticsearch
Compliance:         JMAP Full in S3 + DynamoDB
```

### Storage Cost Comparison

For 1 million emails:

| Format | Avg Size | Total Storage | Annual Cost (S3 Standard) |
|--------|----------|---------------|---------------------------|
| JMAP Full | 100 KB | 100 GB | ~$276/year |
| JMAP Lite | 25 KB | 25 GB | ~$69/year |
| JMAP Minimal | 3 KB | 3 GB | ~$8/year |

*Note: Costs vary by provider and region. S3 Standard pricing ~$0.023/GB/month as of 2023.*

---

## Links & References

### Standards & Specifications

- **RFC 8621 (JMAP for Mail)**: https://datatracker.ietf.org/doc/html/rfc8621
  - The authoritative JMAP specification

- **RFC 5322 (Internet Message Format)**: https://datatracker.ietf.org/doc/html/rfc5322
  - Email message structure standard

- **JMAP Official Site**: https://jmap.io/spec.html
  - Spec overview and resources

### Provider APIs

- **Gmail API v1**: https://developers.google.com/gmail/api/reference/rest/v1/users.messages
  - users.messages resource documentation

- **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/api/resources/message
  - message resource type reference

### Canonizer Resources

- **Registry**: https://github.com/benthepsychologist/canonizer-registry
  - Official transform and schema registry

- **Main Repository**: https://github.com/benthepsychologist/canonizer
  - Canonizer CLI and core library

- **Registry Guide**: [REGISTRY.md](REGISTRY.md)
  - How to contribute transforms

### Related Tools

- **JSONata**: https://jsonata.org/
  - Transform expression language

- **Iglu**: https://github.com/snowplow/iglu
  - Schema registry inspiration (SchemaVer)

---

## Contributing

### Adding New Source Formats

Want to add support for Outlook, Yahoo Mail, or IMAP? See [REGISTRY.md](REGISTRY.md) for contribution guidelines.

**Steps:**
1. Create source schema (e.g., `schemas/com.yahoo/yahoo_email/jsonschema/1-0-0.json`)
2. Create 3 transforms (to Full, Lite, Minimal)
3. Add golden tests
4. Submit PR to registry

### Improving Existing Transforms

Found a bug or edge case? Transforms are versioned using SemVer:
- **Patch (1.0.1)**: Bug fixes
- **Minor (1.1.0)**: Additive changes
- **Major (2.0.0)**: Breaking changes

---

## FAQ

**Q: Which format should I use?**
A: Most applications should use **JMAP Lite**. Use Full for compliance, Minimal for search indexes.

**Q: Can I convert between canonical formats?**
A: Yes! You can transform from Full → Lite → Minimal (lossy), but not backwards.

**Q: Does this replace my email client?**
A: No, Canonizer is a transformation tool, not a client. Your orchestrator (Airflow, etc.) calls Canonizer.

**Q: What about attachments?**
A: Attachment *metadata* is in all formats. Attachment *content* is referenced by blobId (fetch separately).

**Q: Is JMAP widely adopted?**
A: Growing adoption. Fastmail uses it in production. It's an IETF standard, not vendor-specific.

**Q: Can I use JMAP with other email protocols?**
A: Yes! JMAP is just a JSON format. You can transform from IMAP, POP3, etc. to JMAP.

---

**Last Updated:** 2025-11-13
**Version:** 1.0
**Maintainer:** Ben Machina <ben@therapyai.com>
