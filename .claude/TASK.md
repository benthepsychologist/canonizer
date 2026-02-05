---
tier: B
title: "e005b-09c: Canonizer — Derived Schema Transforms (Formation + Projection)"
owner: benthepsychologist
goal: "Define and test the canonizer transforms used by formation (09a) and projection (09b) for schema/shape conversions"
epic: e005b-command-plane-and-performance
repo:
  name: canonizer
  working_branch: feat/canonizer-derived-transforms
created: 2026-02-04T00:00:00Z
---

# e005b-09c — Canonizer: Derived-Schema Transforms (Formation + Projection)

## Status: planned

## Problem

Gate 9 removes “fat” lorchestra callables by pushing all **schema/shape transforms** into canonizer.

Formation (09a) and projection (09b) both need versioned json-in/json-out transforms with stable IDs and testable contracts.

This spec defines the authoritative transform IDs, required config, I/O shapes, and golden fixtures.

---

## Scope

- Repo: canonizer
- Adds transforms only (no changes to storacle, finalform, or lorchestra beyond wiring)
- Transform runtime: existing canonizer callable (`callable: canonizer`) using jsonata-based transforms with semver.

---

## Transform Set

### Formation transforms (used by 09a)

1. `formation/form_response_to_measurement_event@1.0.0`
2. `formation/measurement_event_to_finalform_input@1.0.0`
3. `formation/finalform_event_to_observation_row@1.0.0`

### Projection transforms (used by 09b)

4. `projection/bq_rows_to_sqlite_sync@1.0.0`
5. `projection/bq_rows_to_sheets_write_table@1.0.0`

---

## Contracts

### 1) `formation/form_response_to_measurement_event@1.0.0`

**Purpose**
- Convert canonical `form_response` objects into a derived `measurement_events` row.
- Copy the minimum scoring payload into `measurement_events.metadata` to avoid canonical re-reads during scoring.

**Required config keys**
- `binding_id` (e.g. `intake_01`)
- `source_system` (e.g. `google_forms`)
- `source_entity` (e.g. `form_response`)

**Input item (from storacle.query canonical_objects)**
```json
{
	"idem_key": "...",
	"connection_name": "google-forms-intake-01",
	"canonical_schema": "iglu:org.canonical/form_response/jsonschema/1-0-0",
	"payload": {
		"respondent": {"id": "...", "email": "..."},
		"submitted_at": "...",
		"form_id": "...",
		"answers": []
	},
	"correlation_id": "..."
}
```

**Output item (measurement_events row)**
```json
{
	"idem_key": "...",
	"measurement_event_id": "...",
	"canonical_object_id": "...",
	"subject_id": "...",
	"event_type": "form",
	"event_subtype": "intake_01",
	"binding_id": "intake_01",
	"source_system": "google_forms",
	"source_entity": "form_response",
	"form_id": "...",
	"occurred_at": "...",
	"correlation_id": "...",
	"metadata": {
		"answers": [],
		"submitted_at": "..."
	}
}
```

**Invariants**
- Deterministic keys: `idem_key`, `measurement_event_id`, and `canonical_object_id` must be stable per submission.
- `metadata` must contain what Stage 2 needs to produce finalform input without BQ joins.

---

### 2) `formation/measurement_event_to_finalform_input@1.0.0`

**Purpose**
- Convert a `measurement_events` row into the input dict expected by the finalform callable.

**Required config keys**
- `instrument` (e.g. `intake_01`)

**Input item (measurement_events row)**
```json
{
	"measurement_event_id": "...",
	"subject_id": "...",
	"occurred_at": "...",
	"binding_id": "intake_01",
	"correlation_id": "...",
	"metadata": {"answers": []}
}
```

**Output item (finalform callable input)**
```json
{
	"form_id": "...",
	"form_submission_id": "...",
	"subject_id": "...",
	"timestamp": "...",
	"form_correlation_id": "...",
	"items": [{"question_id": "...", "answer_value": "..."}]
}
```

**Invariants**
- `form_correlation_id` must preserve the submission-level ID (used later to derive observation keys).
- Output must be valid for the configured instrument.

---

### 3) `formation/finalform_event_to_observation_row@1.0.0`

**Purpose**
- Convert finalform output into one or more rows for the `observations` table.

**Input item (from finalform callable output)**
```json
{
	"measurement_event_id": "...",
	"subject_id": "...",
	"timestamp": "...",
	"observations": [{"measure_id": "phq9", "components": []}],
	"source": {"form_correlation_id": "..."}
}
```

**Output items (observations rows; 1+ rows per finalform event)**
```json
{
	"idem_key": "${source.form_correlation_id}:${measure_id}",
	"observation_id": "...",
	"measurement_event_id": "...",
	"subject_id": "...",
	"measure_code": "phq9",
	"occurred_at": "...",
	"components": [],
	"correlation_id": "..."
}
```

**Invariants**
- Output may be 1:N per input; canonizer must return a list of rows.
- `idem_key` must be deterministic for idempotent upsert.

---

### 4) `projection/bq_rows_to_sqlite_sync@1.0.0`

**Purpose**
- Package BQ rows into a single `sqlite.sync` op payload.
- Add timestamps (e.g. `projected_at`) and column list.

**Required config keys**
- `sqlite_path`
- `table`

**Optional config keys**
- `auto_timestamp_columns` (default: `[]`)

**Input items (BQ rows)**
```json
[{"client_id": "123", "name": "..."}]
```

**Output item (sqlite.sync op params)**
```json
{
	"sqlite_path": "~/clinical-vault/local.db",
	"table": "clients",
	"columns": ["client_id", "name", "projected_at"],
	"rows": [{"client_id": "123", "name": "...", "projected_at": "2026-02-04T12:00:00Z"}]
}
```

**Invariants**
- Output is a single dict representing op params (wrapped by plan.build later).
- Column ordering must be deterministic.

---

### 5) `projection/bq_rows_to_sheets_write_table@1.0.0`

**Purpose**
- Package BQ rows into a single `sheets.write_table` op payload.
- Build a 2D `values` matrix: header row + data rows.

**Required config keys**
- `spreadsheet_id`
- `sheet_name`

**Optional config keys**
- `strategy` (default: `replace`)
- `account`
- `column_order` (if absent, use deterministic ordering)

**Input items (BQ rows)**
```json
[{"client_id": "123", "name": "..."}]
```

**Output item (sheets.write_table op params)**
```json
{
	"spreadsheet_id": "...",
	"sheet_name": "clients",
	"strategy": "replace",
	"account": "acct1",
	"values": [
		["client_id", "name"],
		["123", "..."]
	]
}
```

**Invariants**
- Output is a single dict representing op params (wrapped by plan.build later).
- Header row and column ordering must be deterministic.

---

## Test Expectations

For each transform above:

- A golden fixture pair: `input.json` + `expected.json`
- A unit test that:
	1. runs the transform by ID with config,
	2. asserts structural equality of output (and stable ordering where applicable),
	3. covers at least one “missing optional field” case (e.g., respondent.id missing, uses respondent.email).

Minimum fixture set:
- Formation: intake-style form_response with respondent.id, respondent.email, answers array.
- Projection: small 2-row dataset to validate stable column ordering + 2D sheet matrix.