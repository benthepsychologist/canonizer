---
version: "0.1"
tier: B
title: Email Canonicalization Standards (JMAP-based)
owner: benthepsychologist
goal: Establish Canonizer as the Rosetta Stone for email transformation with multiple source and target formats
labels: [email, jmap, schemas, transforms, registry]
project_slug: canonizer
spec_version: 1.0.0
created: 2025-11-13T11:48:38.721344+00:00
updated: 2025-11-13T11:52:00.000000+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/email-canonicalization-jmap"
---

# Email Canonicalization Standards (JMAP-based)

## Objective

Build comprehensive email transformation infrastructure with multiple source formats (Gmail, Exchange) and three canonical target formats based on RFC 8621 JMAP, enabling users to choose storage/complexity trade-offs.

**Vision:** Canonizer becomes the definitive standard for email JSON transformation with authoritative schemas, complete documentation, and production-ready transforms.

## Acceptance Criteria

### Source Schemas
- [ ] Gmail API schema (`com.google/gmail_email/jsonschema/1-0-0`) - validated against real API responses
- [ ] Microsoft Graph/Exchange schema (`com.microsoft/exchange_email/jsonschema/1-0-0`) - validated against real API responses

### Target Canonical Schemas (RFC 8621 JMAP-based)
- [ ] JMAP Full (`org.canonical/email_jmap_full/jsonschema/1-0-0`) - Complete RFC 8621 Email object
- [ ] JMAP Lite (`org.canonical/email_jmap_lite/jsonschema/1-0-0`) - 80% use cases, body content inline
- [ ] JMAP Minimal (`org.canonical/email_jmap_minimal/jsonschema/1-0-0`) - Metadata only, blob references

### Transforms (2 sources × 3 targets = 6 transforms)
- [ ] `email/gmail_to_jmap_full@1.0.0` - Gmail → JMAP Full
- [ ] `email/gmail_to_jmap_lite@1.0.0` - Gmail → JMAP Lite
- [ ] `email/gmail_to_jmap_minimal@1.0.0` - Gmail → JMAP Minimal
- [ ] `email/exchange_to_jmap_full@1.0.0` - Exchange → JMAP Full
- [ ] `email/exchange_to_jmap_lite@1.0.0` - Exchange → JMAP Lite
- [ ] `email/exchange_to_jmap_minimal@1.0.0` - Exchange → JMAP Minimal

### Documentation
- [ ] `docs/EMAIL_CANONICALIZATION.md` - Comprehensive guide covering:
  - What each canonical format is (JMAP Full/Lite/Minimal)
  - When to use each format (use cases, trade-offs)
  - Storage cost comparison (body inline vs blob references)
  - RFC 8621 references and links
  - Field mapping tables for each transform
  - Example workflows
- [ ] Each schema has rich descriptions and examples
- [ ] Each transform has detailed metadata explaining target choice

### Quality
- [ ] All schemas validate with jsonschema
- [ ] Golden tests for each of 6 transforms
- [ ] Integration tests for full pipeline
- [ ] Coverage ≥70% for new transform code
- [ ] Ruff checks pass
- [ ] Registry validation passes for all transforms

### Registry
- [ ] All schemas pushed to canonizer-registry
- [ ] All transforms pushed to canonizer-registry
- [ ] REGISTRY_INDEX.json regenerated
- [ ] CI validates all new content

## Context

### Background

**Current State:**
- Single minimal canonical email schema (`org.canonical/email/jsonschema/1-0-0`)
- One Gmail transform example
- No guidance on storage trade-offs or format choices

**Problem:**
Email is complex (MIME, encodings, attachments, threading). Different use cases need different levels of detail:
- **Full archival:** Need complete MIME structure, all headers, exact body content
- **App display:** Need text/HTML bodies, attachments metadata, basic headers
- **Search indexing:** Need metadata only, body stored separately in S3/blob storage

**Solution:**
Follow RFC 8621 JMAP (IETF Standards Track) as authoritative JSON email format, offer three canonical targets based on storage/complexity needs.

### Why JMAP?

**RFC 8621** (The JSON Meta Application Protocol for Mail, 2019) is the IETF-approved standard for representing emails as JSON:

- ✅ **IETF Standards Track** - Official internet standard
- ✅ **JSON-native** - Designed specifically for JSON APIs (vs MIME parsing)
- ✅ **Production-proven** - Used by Fastmail, growing adoption
- ✅ **Comprehensive** - Handles all email complexity (threading, MIME, encodings)
- ✅ **Future-proof** - Active IETF working group
- ✅ **Transformation-friendly** - Structured for machine processing

**Key JMAP Principles:**
1. Structured email addresses: `{"name": "John Doe", "email": "john@example.com"}`
2. ISO 8601 timestamps (not milliseconds)
3. Separation of structure (`bodyStructure`) from content (`bodyValues`)
4. IMAP keywords as object: `{"$seen": true, "$flagged": true}`
5. Arrays for all multi-value headers

### Three Canonical Targets

**1. JMAP Full** - `org.canonical/email_jmap_full/jsonschema/1-0-0`
- Complete RFC 8621 Email object
- Full MIME structure in `bodyStructure`
- All headers preserved
- Use case: Full archival, compliance, forensics
- Storage: ~50-200KB per email (bodies inline)

**2. JMAP Lite** - `org.canonical/email_jmap_lite/jsonschema/1-0-0`
- 80% of JMAP fields
- Simplified body: `body.text` and `body.html` strings
- Core headers + threading
- Attachments metadata (filename, size, type, blobId)
- Use case: Application display, most email clients
- Storage: ~10-50KB per email

**3. JMAP Minimal** - `org.canonical/email_jmap_minimal/jsonschema/1-0-0`
- Metadata only: ID, thread, from/to/cc, subject, dates, preview
- Body content referenced by blobId (not inline)
- Use case: Search indexes, analytics, high-volume processing
- Storage: ~1-5KB per email (bodies in S3)

### Source Formats

**Gmail API** (`com.google/gmail_email/jsonschema/1-0-0`)
- Gmail API v1 message resource
- Nested `payload.headers` array structure
- Base64url encoded body
- Reference: https://developers.google.com/gmail/api/reference/rest/v1/users.messages

**Microsoft Graph/Exchange** (`com.microsoft/exchange_email/jsonschema/1-0-0`)
- Microsoft Graph API message resource
- Direct property access (no nested payload)
- HTML body as string
- Reference: https://learn.microsoft.com/en-us/graph/api/resources/message

### Constraints

- Must follow RFC 8621 for JMAP schemas
- Must support "every email that was ever sent to anyone ever"
- Schemas must be additive-only after v1.0.0 (Iglu SchemaVer)
- No dependencies on external services (pure transformation)
- All body content in transforms must handle encoding properly

## Plan

### Step 1: Source Schemas (Gmail + Exchange) [G0: Schema Design]

**Prompt:**

Create JSON schemas for Gmail API v1 and Microsoft Graph API email message resources based on official API documentation. Validate against real API response examples.

1. Research Gmail API v1 users.messages resource structure
2. Research Microsoft Graph API message resource structure
3. Create `schemas/com.google/gmail_email/jsonschema/1-0-0.json` (update existing)
4. Create `schemas/com.microsoft/exchange_email/jsonschema/1-0-0.json` (new)
5. Add example API responses to `tests/fixtures/email/gmail/` and `tests/fixtures/email/exchange/`
6. Validate schemas parse fixture examples

**Outputs:**

- `schemas/com.google/gmail_email/jsonschema/1-0-0.json`
- `schemas/com.microsoft/exchange_email/jsonschema/1-0-0.json`
- `tests/fixtures/email/gmail/api_response_example.json`
- `tests/fixtures/email/exchange/api_response_example.json`

**Validation:**
- Schemas are valid JSON Schema draft-07
- Fixture examples validate against schemas
- All required fields documented

### Step 2: Target Canonical Schemas (JMAP Full/Lite/Minimal) [G0: Schema Design]

**Prompt:**

Create three JMAP-based canonical email schemas following RFC 8621 specification:

1. **JMAP Full** - Complete RFC 8621 Email object (use proposed schema as starting point)
2. **JMAP Lite** - Simplified with inline body strings instead of bodyStructure/bodyValues
3. **JMAP Minimal** - Metadata only with blobId references for body content

Each schema must have:
- Rich field descriptions
- Examples in schema
- Clear use case documentation in description
- Reference to RFC 8621 where applicable

**Outputs:**

- `schemas/org.canonical/email_jmap_full/jsonschema/1-0-0.json`
- `schemas/org.canonical/email_jmap_lite/jsonschema/1-0-0.json`
- `schemas/org.canonical/email_jmap_minimal/jsonschema/1-0-0.json`

**Validation:**
- All schemas valid JSON Schema draft-07
- JMAP Full follows RFC 8621 Email object structure
- JMAP Lite and Minimal are proper subsets
- Required fields clearly marked

### Step 3: Gmail Transforms (3 variants) [G1: Transform Implementation]

**Prompt:**

Create three JSONata transforms from Gmail API format to each canonical target:

1. `transforms/email/gmail_to_jmap_full/1.0.0/spec.jsonata`
2. `transforms/email/gmail_to_jmap_lite/1.0.0/spec.jsonata`
3. `transforms/email/gmail_to_jmap_minimal/1.0.0/spec.jsonata`

Each transform needs:
- `spec.jsonata` - JSONata transformation logic
- `spec.meta.yaml` - Metadata with provenance, checksums, status
- `tests/input.json` - Gmail API response example
- `tests/expected.json` - Expected canonical output
- Handle base64url decoding for body content
- Parse headers array into structured fields
- Convert internalDate to ISO 8601

**Outputs:**

- `transforms/email/gmail_to_jmap_full/1.0.0/*`
- `transforms/email/gmail_to_jmap_lite/1.0.0/*`
- `transforms/email/gmail_to_jmap_minimal/1.0.0/*`

**Validation:**
- Each transform passes golden tests
- Checksums in metadata match spec.jsonata
- All email addresses properly parsed into {name, email} objects
- Timestamps properly converted to ISO 8601

### Step 4: Exchange Transforms (3 variants) [G1: Transform Implementation]

**Prompt:**

Create three JSONata transforms from Microsoft Graph/Exchange format to each canonical target:

1. `transforms/email/exchange_to_jmap_full/1.0.0/spec.jsonata`
2. `transforms/email/exchange_to_jmap_lite/1.0.0/spec.jsonata`
3. `transforms/email/exchange_to_jmap_minimal/1.0.0/spec.jsonata`

Each transform needs same structure as Gmail transforms. Exchange API uses direct property access (simpler than Gmail's nested payload structure).

**Outputs:**

- `transforms/email/exchange_to_jmap_full/1.0.0/*`
- `transforms/email/exchange_to_jmap_lite/1.0.0/*`
- `transforms/email/exchange_to_jmap_minimal/1.0.0/*`

**Validation:**
- Each transform passes golden tests
- Checksums valid
- Email addresses properly structured
- Handle Exchange-specific fields (categories, importance, etc.)

### Step 5: Comprehensive Documentation [G2: Documentation Review]

**Prompt:**

Create `docs/EMAIL_CANONICALIZATION.md` - the definitive guide to email transformation in Canonizer.

Must include:

1. **Overview** - Why email canonicalization, why JMAP
2. **RFC 8621 JMAP Explanation** - What it is, why authoritative
3. **Canonical Formats Comparison Table**
   - JMAP Full vs Lite vs Minimal
   - Storage costs, use cases, field counts
4. **Source Format Documentation**
   - Gmail API structure explanation
   - Exchange API structure explanation
5. **Transform Matrix** - 2×3 grid showing all transforms
6. **Usage Examples** - Complete workflows for each use case
7. **Field Mapping Tables** - Detailed mappings for each transform
8. **Storage Strategy Guide** - When to use blob refs vs inline
9. **Links & References** - RFC 8621, API docs, JMAP.io

Also update:
- `README.md` - Add email canonicalization section
- Each schema file - Add rich descriptions and examples

**Outputs:**

- `docs/EMAIL_CANONICALIZATION.md`
- Updated `README.md`
- Enhanced schema descriptions

**Validation:**
- All links valid
- Examples are correct
- Tables complete
- Clear for new users

### Step 6: Integration Testing [G2: Pre-Release]

**Prompt:**

Create comprehensive integration tests for the full email transformation pipeline:

1. Test each of 6 transforms end-to-end
2. Test transform chaining (if applicable)
3. Test error handling (invalid input, missing fields)
4. Test encoding edge cases (UTF-8, special chars, base64)
5. Test attachment handling
6. Validate all outputs against target schemas

**Outputs:**

- `tests/integration/test_email_transforms.py`
- Additional golden test fixtures as needed

**Commands:**

```bash
pytest tests/integration/test_email_transforms.py -v
pytest tests/ --cov=canonizer --cov-report=term-missing
ruff check canonizer/
```

**Validation:**
- All tests pass
- Coverage ≥70%
- No ruff errors

### Step 7: Registry Updates & CI [G3: Registry Publication]

**Prompt:**

Push all new schemas and transforms to canonizer-registry repository:

1. Copy schemas to registry repo structure
2. Copy transforms to registry repo structure
3. Run `tools/validate.py` on all new content
4. Run `tools/generate_index.py` to update REGISTRY_INDEX.json
5. Commit and push to registry repo
6. Verify CI passes

**Outputs:**

- Updated canonizer-registry repository
- Regenerated `REGISTRY_INDEX.json`
- CI passing on registry repo

**Commands:**

```bash
# In canonizer-registry repo
python tools/validate.py schemas/
python tools/validate.py transforms/
python tools/generate_index.py
git add .
git commit -m "feat: Add JMAP-based email canonicalization (6 transforms, 5 schemas)"
git push
```

**Validation:**
- Registry CI validates all content
- `can registry list` shows new transforms
- `can registry pull email/gmail_to_jmap_lite@1.0.0` works
- REGISTRY_INDEX.json includes all new transforms

### Step 8: Final Validation & Release [G4: Release Approval]

**Prompt:**

Final end-to-end validation and release preparation:

1. Test all 6 transforms via registry commands
2. Run full test suite
3. Update CHANGELOG.md with email canonicalization feature
4. Create release notes
5. Tag version if appropriate

**Outputs:**

- `CHANGELOG.md` updated
- All tests passing
- Documentation complete
- Registry validated

**Commands:**

```bash
pytest tests/ -v --cov=canonizer
ruff check canonizer/
can registry list --refresh
can registry info email/gmail_to_jmap_lite@latest
```

**Validation:**
- Full test suite passes
- Registry contains all transforms
- Documentation is complete
- Ready for production use

## Models & Tools

**Tools:**
- `pytest` - Test runner with coverage
- `ruff` - Linting and formatting
- `jsonschema` - Schema validation
- `can` - Canonizer CLI for testing transforms
- `bash` - Shell commands for git, registry operations

**External Resources:**
- RFC 8621: https://datatracker.ietf.org/doc/html/rfc8621
- JMAP.io: https://jmap.io/spec.html
- Gmail API: https://developers.google.com/gmail/api/reference/rest/v1/users.messages
- Microsoft Graph: https://learn.microsoft.com/en-us/graph/api/resources/message

**Models:** Sonnet 4.5 for implementation, Haiku for validation

## Repository

**Main Repo:** https://github.com/benthepsychologist/canonizer
**Registry Repo:** https://github.com/benthepsychologist/canonizer-registry

**Branch:** `feat/email-canonicalization-jmap`

**Merge Strategy:** squash

## Deliverables Summary

**Schemas:** 5 total (2 source + 3 target)
- Gmail API schema
- Exchange API schema
- JMAP Full canonical schema
- JMAP Lite canonical schema
- JMAP Minimal canonical schema

**Transforms:** 6 total (2 sources × 3 targets)
- gmail → jmap_full
- gmail → jmap_lite
- gmail → jmap_minimal
- exchange → jmap_full
- exchange → jmap_lite
- exchange → jmap_minimal

**Documentation:** 1 comprehensive guide + README updates
- docs/EMAIL_CANONICALIZATION.md (authoritative guide)
- Updated README.md with email section
- Enhanced schema descriptions

**Tests:** Integration tests + golden tests for each transform
- 6 transform test suites
- Integration test pipeline
- Edge case coverage

## Success Metrics

- ✅ 5 schemas validate with jsonschema
- ✅ 6 transforms pass golden tests
- ✅ All transforms available in registry
- ✅ Documentation is comprehensive and clear
- ✅ Test coverage ≥70%
- ✅ CI passes on both repos
- ✅ Users can discover and use transforms via `can registry` commands

## Post-Implementation

**Future Work:**
- Add more source formats (Outlook, Yahoo Mail, IMAP)
- Add email threading visualization
- Add email attachment extraction utilities
- LLM-assisted transform generation for new providers
- Performance benchmarks for large-scale transformation

**Registry Promotion:**
- Blog post about JMAP-based email canonicalization
- Example Jupyter notebooks for common workflows
- Integration examples with data pipelines (Airflow, Dagster)