---
version: "0.1"
tier: C
title: Source ID Schema Update (2-0-0)
owner: benthepsychologist
goal: Add source_id and client_type to canonical schemas for writeback support
labels: [schemas, breaking-change, dataverse]
project_slug: canonizer
spec_version: 1.1.0
created: 2025-12-04T15:00:00.000000+00:00
updated: 2025-12-04T16:00:00.000000+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/source-id-2-0-0"
---

# Source ID Schema Update (2-0-0)

## Objective

> Add `source_id` and `source_entity` to all Dataverse-derived canonical schemas, plus `client_type_code`/`client_type_label` to contact schema. This is a breaking change (2-0-0) requiring full re-canonization.

## Acceptance Criteria

- [ ] `contact` schema 2-0-0 includes `source_id`, `source_entity`, `client_type_code`, and `client_type_label`
- [ ] `clinical_session` schema 2-0-0 includes `source_id` and `source_entity`
- [ ] `clinical_document` schema 2-0-0 includes `source_id`, `source_entity`, and `session_source_id`
- [ ] `session_transcript` schema 2-0-0 includes `source_id`, `source_entity`, and `session_source_id`
- [ ] All transforms updated to 2-0-0 and populate new fields
- [ ] Lorchestra job definitions updated to use 2-0-0 schemas
- [ ] All affected records re-canonized
- [ ] CI green (ruff + pytest)

## Context

### Background

We need writeback capability from local projections back to Dataverse. The canonical layer currently strips the source system IDs during transformation, making it impossible to update the original records.

Additionally, we need `client_type` on contacts to filter therapy clients from other contact types (supervisors, vendors, etc.). This filtering is a **projection concern**, not a canonical concern—canonical stores both the raw code and label, and projections decide what to surface.

### Key Invariants

All canonical schemas carry two source-tracking fields:

- **`source_id`** (string, required): The primary key of the upstream record, or a synthetic stable key for derived/synthesized records
- **`source_entity`** (string, required): The upstream entity/table name that `source_id` refers to

For schemas that map directly from a Dataverse entity, `source_id` is the upstream primary key. For synthesized schemas with no upstream record (e.g., `session_transcript`), `source_id` is a synthetic, stable key in that schema's namespace, and `source_entity` indicates the synthesis.

### What's changing

| Schema | New Fields | Source |
|--------|-----------|--------|
| `contact` | `source_id`, `source_entity`, `client_type_code`, `client_type_label` | `contactid`, `"contact"`, `cre92_clienttype` (raw), formatted value |
| `clinical_session` | `source_id`, `source_entity` | `cre92_clientsessionid`, `"cre92_clientsession"` |
| `clinical_document` | `source_id`, `source_entity`, `session_source_id` | `cre92_clientreportid` or `annotationid`, `"cre92_clientreport"` or `"annotation"`, `_cre92_session_value` |
| `session_transcript` | `source_id`, `source_entity`, `session_source_id` | `{session_source_id}#transcript-v1`, `"synthetic:transcript"`, `cre92_clientsessionid` |

### Why 2-0-0

This is a MODEL bump because:
1. **New canonical invariants**: Dataverse-derived objects must now carry `source_id` fields for writeback
2. **New required fields**: A 2-0-0 payload would not validate against 1-0-0; the schemas' invariants changed
3. **Downstream consumers must update**: to the new URIs and field set

### source_id + source_entity by Schema

| Schema | source_id | source_entity | Notes |
|--------|-----------|---------------|-------|
| `contact` | `contactid` | `"contact"` | Direct DV entity |
| `clinical_session` | `cre92_clientsessionid` | `"cre92_clientsession"` | Direct DV entity |
| `clinical_document` | `cre92_clientreportid` or `annotationid` | `"cre92_clientreport"` or `"annotation"` | Varies by upstream entity type |
| `session_transcript` | `{session_source_id}#transcript-v1` | `"synthetic:transcript"` | Synthesized, not a real DV record |

### client_type Design

The formatted label (`cre92_clienttype@OData.Community.Display.V1.FormattedValue`) is:
- Localized
- Admin-renameable
- Not stable over time

Therefore, canonical stores **both**:
- `client_type_code` (string, from raw `cre92_clienttype`) — stable, for durable logic
- `client_type_label` (string, nullable) — human-readable, for display and quick filters

Filtering for "therapy clients only" is a **projection concern**:
- Projections can filter by `client_type_label = 'Therapy'` (quick and dirty)
- Or by `client_type_code IN (...)` (robust, config-driven)
- Projections can derive `is_therapy_client` boolean for downstream use

## Plan

### Step 1: Update Contact Schema and Transform [G0: Plan Approval]

**Prompt:**

Create `schemas/org.canonical/contact/jsonschema/2-0-0.json`:
- Copy from 1-0-0
- Add `source_id` (string, required) - the Dataverse `contactid`
- Add `source_entity` (string, required) - always `"contact"` for this schema
- Add `client_type_code` (string, nullable) - raw value from `cre92_clienttype`
- Add `client_type_label` (string, nullable) - from `cre92_clienttype@OData.Community.Display.V1.FormattedValue`

Create `transforms/contact/dataverse_to_canonical/2-0-0/`:
- Copy from 1-0-0
- Update `spec.jsonata` to include:
  ```jsonata
  "source_id": contactid,
  "source_entity": "contact",
  "client_type_code": $string(cre92_clienttype),
  "client_type_label": `cre92_clienttype@OData.Community.Display.V1.FormattedValue`
  ```
- Update `spec.meta.yaml` with new version and to_schema
- Ensure tests cover the "no client type set" scenario (both fields should be null)

**Outputs:**

- `schemas/org.canonical/contact/jsonschema/2-0-0.json`
- `transforms/contact/dataverse_to_canonical/2-0-0/spec.jsonata`
- `transforms/contact/dataverse_to_canonical/2-0-0/spec.meta.yaml`
- `transforms/contact/dataverse_to_canonical/2-0-0/tests/input.json`
- `transforms/contact/dataverse_to_canonical/2-0-0/tests/expected.json`

---

### Step 2: Update Clinical Session Schema and Transform [G1: Code Readiness]

**Prompt:**

Create `schemas/org.canonical/clinical_session/jsonschema/2-0-0.json`:
- Copy from 1-0-0
- Add `source_id` (string, required) - the Dataverse `cre92_clientsessionid`
- Add `source_entity` (string, required) - always `"cre92_clientsession"` for this schema

Create `transforms/clinical_session/dataverse_to_canonical/2-0-0/`:
- Copy from 1-0-0
- Update `spec.jsonata`:
  ```jsonata
  "source_id": cre92_clientsessionid,
  "source_entity": "cre92_clientsession",
  "session_id": cre92_clientsessionid
  ```
- Update `spec.meta.yaml`

**Note on session_id vs source_id:** Both fields hold the same value (`cre92_clientsessionid`) for Dataverse-derived sessions. `session_id` is the canonical session identifier; `source_id` is the upstream primary key. For this source system, they are identical. For a future EHR source, `session_id` might equal `source_id`, but `source_entity` would differ.

**Outputs:**

- `schemas/org.canonical/clinical_session/jsonschema/2-0-0.json`
- `transforms/clinical_session/dataverse_to_canonical/2-0-0/spec.jsonata`
- `transforms/clinical_session/dataverse_to_canonical/2-0-0/spec.meta.yaml`
- `transforms/clinical_session/dataverse_to_canonical/2-0-0/tests/`

---

### Step 3: Update Clinical Document Schema and Transform [G1: Code Readiness]

**Prompt:**

Create `schemas/org.canonical/clinical_document/jsonschema/2-0-0.json`:
- Copy from 1-0-0
- Add `source_id` (string, required) - the Dataverse report/annotation ID
- Add `source_entity` (string, required) - `"cre92_clientreport"` or `"annotation"`
- Add `session_source_id` (string, required) - the parent session's `cre92_clientsessionid`

Create `transforms/clinical_document/dataverse_to_canonical/2-0-0/`:
- Update `spec.jsonata`:
  ```jsonata
  "source_id": cre92_clientreportid ? cre92_clientreportid : annotationid,
  "source_entity": cre92_clientreportid ? "cre92_clientreport" : "annotation",
  "session_source_id": `_cre92_session_value`
  ```

**source_entity enables writeback:** With `source_entity`, you know which upstream table to target. Without it, you'd have to infer entity type from shape or feed—fragile.

**session_source_id is required:** If every document you care about is session-attached, make this required and let upstream validation fail loudly on data quality issues.

**Join pattern:** `clinical_document.session_source_id` → `clinical_session.source_id`

**Outputs:**

- `schemas/org.canonical/clinical_document/jsonschema/2-0-0.json`
- `transforms/clinical_document/dataverse_to_canonical/2-0-0/spec.jsonata`
- `transforms/clinical_document/dataverse_to_canonical/2-0-0/spec.meta.yaml`
- `transforms/clinical_document/dataverse_to_canonical/2-0-0/tests/`

---

### Step 4: Update Session Transcript Schema and Transform [G1: Code Readiness]

**Prompt:**

Create `schemas/org.canonical/session_transcript/jsonschema/2-0-0.json`:
- Copy from 1-0-0
- Add `source_id` (string, required) - synthetic, stable key in the transcript namespace
- Add `source_entity` (string, required) - always `"synthetic:transcript"` for this schema
- Add `session_source_id` (string, required) - the parent session's `cre92_clientsessionid`

**source_id semantics:** Transcripts are not real upstream Dataverse records—they are synthesized (one transcript per session). The `source_id` is a **synthetic, stable key**: `{session_source_id}#transcript-v1`. The `source_entity` of `"synthetic:transcript"` makes it explicit this is not a real Dataverse record.

Create `transforms/session_transcript/dataverse_to_canonical/2-0-0/` if it doesn't exist, or update existing:
  ```jsonata
  (
    $sid := cre92_clientsessionid;
    {
      "session_source_id": $sid,
      "source_id": $sid & "#transcript-v1",
      "source_entity": "synthetic:transcript"
    }
  )
  ```

**Join pattern:** `session_transcript.session_source_id` → `clinical_session.source_id`

**Outputs:**

- `schemas/org.canonical/session_transcript/jsonschema/2-0-0.json`
- `transforms/session_transcript/dataverse_to_canonical/2-0-0/` (if applicable)

---

### Step 5: Update Lorchestra Job Definitions [G1: Code Readiness]

**Prompt:**

Update job definitions in `/workspace/lorchestra/lorchestra/jobs/definitions/` to use 2-0-0 schemas:

- `canonize_dataverse_contacts.json`: schema_out → `iglu:org.canonical/contact/jsonschema/2-0-0`
- `canonize_dataverse_sessions.json`: schema_out → `iglu:org.canonical/clinical_session/jsonschema/2-0-0`
- `canonize_dataverse_reports.json`: schema_out → `iglu:org.canonical/clinical_document/jsonschema/2-0-0`
- Any transcript jobs: schema_out → `iglu:org.canonical/session_transcript/jsonschema/2-0-0`

Also update transform_ref to point to 2-0-0 transforms.

**Outputs:**

- Updated job definition files in lorchestra

---

### Step 6: Run Tests and Lint Checks [G2: Pre-Release]

**Prompt:**

Run canonizer tests to verify transforms work:

```bash
cd /workspace/canonizer
pytest tests/ -v
```

Verify each 2-0-0 transform produces expected output with source_id fields.

**Commands:**

```bash
pytest tests/ -v
ruff check .
```

**Outputs:**

- All tests passing

---

### Step 7: Re-canonize All Records [G2: Pre-Release]

**Prompt:**

Run re-canonization jobs in lorchestra for all affected record types:

```bash
# Contacts
lorchestra run canonize_dataverse_contacts

# Sessions
lorchestra run canonize_dataverse_sessions

# Documents/Reports
lorchestra run canonize_dataverse_reports

# Transcripts (if separate job exists)
lorchestra run canonize_dataverse_transcripts
```

Verify records in BQ now have `source_id` populated in payload.

**Commands:**

```bash
lorchestra run canonize_dataverse_contacts
lorchestra run canonize_dataverse_sessions
lorchestra run canonize_dataverse_reports
```

**Outputs:**

- All records re-canonized with source_id fields

## Architecture Summary

```
schemas/org.canonical/
  contact/jsonschema/2-0-0.json           # +source_id, +source_entity, +client_type_code, +client_type_label
  clinical_session/jsonschema/2-0-0.json  # +source_id, +source_entity
  clinical_document/jsonschema/2-0-0.json # +source_id, +source_entity, +session_source_id
  session_transcript/jsonschema/2-0-0.json # +source_id, +source_entity, +session_source_id

transforms/
  contact/dataverse_to_canonical/2-0-0/
  clinical_session/dataverse_to_canonical/2-0-0/
  clinical_document/dataverse_to_canonical/2-0-0/
  session_transcript/dataverse_to_canonical/2-0-0/  # if exists
```

### Field Mappings

| Canonical Field | Dataverse Source | Notes |
|----------------|------------------|-------|
| `contact.source_id` | `contactid` | Primary key |
| `contact.source_entity` | `"contact"` | Always this value |
| `contact.client_type_code` | `cre92_clienttype` | Raw value (stable) |
| `contact.client_type_label` | `cre92_clienttype@OData...FormattedValue` | Display label (mutable) |
| `clinical_session.source_id` | `cre92_clientsessionid` | Primary key |
| `clinical_session.source_entity` | `"cre92_clientsession"` | Always this value |
| `clinical_document.source_id` | `cre92_clientreportid` or `annotationid` | Depends on entity type |
| `clinical_document.source_entity` | `"cre92_clientreport"` or `"annotation"` | Enables targeted writeback |
| `clinical_document.session_source_id` | `_cre92_session_value` | FK to session |
| `session_transcript.source_id` | `{session_source_id}#transcript-v1` | Synthetic key |
| `session_transcript.source_entity` | `"synthetic:transcript"` | Indicates not a real DV record |
| `session_transcript.session_source_id` | `cre92_clientsessionid` | FK to session |

### Join Graph

```
clinical_session.source_id
    ↑
    ├── clinical_document.session_source_id
    └── session_transcript.session_source_id
```

### Projection Filtering (Future)

For therapy-only surfaces, projections can:

```sql
-- Option A: Quick filter by label
WHERE client_type_label = 'Therapy'

-- Option B: Robust filter by code
WHERE client_type_code IN (SELECT code FROM therapy_client_types)

-- Option C: Derived boolean
SELECT
  *,
  CASE WHEN client_type_code IN (...) THEN TRUE ELSE FALSE END AS is_therapy_client
FROM canonical_contacts
```

## Models & Tools

**Tools:** bash, pytest, ruff, lorchestra

**Dependencies:** None

## Repository

**Branch:** `feat/source-id-2-0-0`

**Merge Strategy:** squash
