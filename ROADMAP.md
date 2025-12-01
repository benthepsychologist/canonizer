# Canonizer Roadmap

> **Source of Truth:** `.specwright/specs/` directory contains detailed specifications for each feature.

## Philosophy

Canonizer is a **pure JSON transformation library**. It does one thing well: `raw_json + transform_id → canonical_json`.

- No ingestion
- No storage
- No orchestration
- Just transforms

Your orchestrator (Airflow, Dagster, Snowplow) calls Canonizer. Canonizer doesn't call anything.

## Value Proposition

**The problem:** API schemas drift. Gmail, Exchange, Stripe, Salesforce — they all change their JSON structures without warning. Your pipelines break. You scramble to fix transforms.

**The solution (ecosystem):**
1. **Canonizer** (this package) — validates, transforms, diffs, pulls from registry
2. **Canonizer Registry** — versioned schemas and transforms with CI validation
3. **Drift Detection Service** (separate) — monitors API endpoints, detects changes, notifies subscribers

**Medium-term goal:** When an API schema changes, transforms are available in the registry *before* your pipeline breaks.

---

## Completed (v0.1 - v0.4)

### v0.1 - Core Runtime
**Spec:** `canonizer-aip-v0.md`

- Transform registry with `.jsonata` files + `.meta.yaml` sidecars
- Python JSONata runtime engine
- Schema validation (Iglu SchemaVer format)
- CLI: `can transform`, `can validate`, `can diff`, `can patch`
- Schema differ/patcher for mechanical evolution
- Gmail→Canonical email transform example

### v0.1+ - Remote Registry
**Spec:** `canonizer-aip-v01-registry.md`

- Git-based registry: https://github.com/benthepsychologist/canonizer-registry
- CI-driven validation on PRs
- HTTP-based discovery via `REGISTRY_INDEX.json`
- Registry CLI: `can registry list`, `search`, `pull`, `info`, `validate`
- Local cache at `~/.cache/canonizer/registry/`

### v0.2 - Email Canonicalization
**Spec:** `email-formats-and-registry-update.md`

- 6 production email transforms (Gmail + Exchange → JMAP Full/Lite/Minimal)
- RFC 8621 JMAP-based canonical schemas
- Three-tier format strategy:
  - **JMAP Full:** Complete archival (~50-200KB)
  - **JMAP Lite:** Application display (~10-50KB)
  - **JMAP Minimal:** Search indexes (~1-5KB)
- `docs/EMAIL_CANONICALIZATION.md`

### v0.2+ - Form Response Canonicalization
**Spec:** `register-and-canonize-questionnaires.md`

- Google Forms source schema
- Canonical `form_response` schema
- `forms/google_forms_to_canonical@1.0.0` transform

### v0.3 - Dataverse Transforms
**Spec:** `dataverse-contacts-sessions-reports.md`

- 3 Dataverse transforms for clinical/CRM data:
  - Contact → Canonical Contact
  - Clinical Session → Canonical Session
  - Report → Canonical Report
- Canonical schemas for contact, clinical_session, report

### v0.4 - Pure Transformation Library
**Spec:** `refactor-to-python-package.md`

- Programmatic API: `canonicalize()`, `run_batch()`
- Convenience wrappers: `canonicalize_email_from_gmail()`, etc.
- CLI moved to optional `[cli]` extra
- Library-first, CLI-second design
- 115 tests, 46% coverage

---

## Completed (v0.5)

### Local Registry MVP
**Spec:** `local-registry-mvp.md` (status: complete)

Each project gets a `.canonizer/` directory:

```
myproject/
├── .canonizer/
│   ├── config.yaml          # Registry config
│   ├── lock.json            # Pinned refs + hashes
│   └── registry/            # Local copies
│       ├── schemas/
│       └── transforms/
└── ...
```

**Deliverables:**
- [x] `canonizer init` creates `.canonizer/` directory structure
- [x] `config.yaml` format for local mode
- [x] `lock.json` format for dependency pinning
- [x] `resolve_schema()` and `resolve_transform()` functions
- [x] Wire `validate_payload()` and `canonicalize()` to local resolution
- [x] No more CWD or env var dependency
- [x] `canonizer import run` - import single schema/transform from registry clone
- [x] `canonizer import all` - bulk import with filters (--category, --schemas-only, --transforms-only)
- [x] `canonizer import list` - list available items in a registry

---

## Next Up (v0.6)

### Remote Registry Infrastructure
**Spec:** `remote-registry.md` (status: stub, depends on local-registry-mvp)

**Prerequisites:** Local Registry MVP completed

**Deliverables:**
- [ ] Static file hosting (GitHub Pages or Cloudflare R2)
- [ ] `canonizer registry pull <ref>` - fetch from remote
- [ ] `canonizer registry sync` - sync all lock.json dependencies
- [ ] Hash verification on pull
- [ ] CI publishes to static host on merge
- [ ] `index.json` generation for discovery

### LLM Scaffolding
**Spec:** Deferred from `canonizer-aip-v0.md`

- `can scaffold transform` command
- Generate transforms from schema pairs using LLM
- Interactive mode for ambiguity resolution
- Tier-2 evolution (when diff/patch insufficient)

### Additional Transforms
- Calendar events (Google Calendar, Microsoft Graph)
- Healthcare data (HL7 FHIR mappings)
- CRM data (Salesforce, HubSpot)

### Performance & Scale
- Async API: `canonicalize_async()`
- Streaming batch API for large datasets
- Performance profiling

### Registry Publishing
- `can registry publish` - Open PR via GitHub API
- Auto-bump version based on diff/patch
- Compatibility matrix validation

### Schema Freshness Checks
- `can registry check <schema-ref>` - Check if local schema matches latest registry version
- `can registry check --all` - Check all pinned schemas for drift
- Integrate with `canonicalize()` - optional warning when using outdated schema
- Return metadata: `{is_latest: bool, latest_version: "1-0-2", current_version: "1-0-0"}`

---

## Long-Term (v1.0+)

### Submit Detected Drift
- `can registry submit-diff` - Submit schema diff to registry as PR
- Workflow: detect drift in your pipeline → generate diff → submit for community review
- Auto-generate transform patch proposals for simple changes (adds/renames)
- Enables crowdsourced schema tracking

---

## Related: Drift Detection Service (Out of Scope)

> This is a **separate service**, not part of the Canonizer package. Mentioned here for ecosystem context.

A future drift detection service would:
- Monitor sandbox accounts (Google Workspace test domain, Microsoft dev tenant, Stripe test mode)
- Periodically fetch sample payloads from API endpoints
- Diff against known schemas in the registry
- Notify subscribers when drift is detected
- Auto-generate schema update PRs to canonizer-registry

**What Canonizer provides for this service:**
- Schema diffing (`can diff run`)
- Transform patching (`can patch run`)
- Registry schema freshness checks (`can registry check`)
- Diff submission (`can registry submit-diff`)

The detection, monitoring, and notification logic lives elsewhere.

---

## Out of Scope (Forever)

These are explicitly **not** Canonizer features:

- Data ingestion/connectors (use Airbyte/Meltano)
- Storage layers (GCS, BigQuery, databases)
- Data pipelines and orchestration
- Event bus or Pub/Sub integration
- Web UI or dashboard
- Multi-tenant SaaS platform

Canonizer is a **pure function**. The orchestrator handles everything else.

---

## Contributing

See `.specwright/specs/` for detailed specifications. Each spec follows the standard format:
- Objective and acceptance criteria
- Context and constraints
- Step-by-step implementation plan
- Status tracking

To propose new features, create a spec in `.specwright/specs/` following the existing pattern.

---

## Broad Strategy (Ecosystem Notes)

> These are strategic notes about the broader ecosystem direction, not implementation specs. When work begins on any of these areas, proper specs will be created in `.specwright/specs/`.

### The Drift Detection Loop

The long-term vision is a closed loop:

```
API endpoints → Sandbox monitoring → Drift detection → Registry update → Transforms available
     ↑                                                                            │
     └────────────────────── Your pipeline stays healthy ←────────────────────────┘
```

**Phase 1: Internal-first**
- Use Canonizer in your own ingestion pipelines
- Detect drift reactively (validation failures in production)
- Fix transforms manually, contribute back to registry

**Phase 2: Sandbox monitoring**
- Create sandbox accounts for major providers (Google Workspace test domain, Microsoft dev tenant, Stripe test mode)
- Low-volume polling (5-20 calls/endpoint/day) via official SDKs
- Store sample payloads, diff against known schemas
- Private drift inbox (local directory or private repo)

**Phase 3: Registry integration**
- Drift detection submits PRs to canonizer-registry automatically
- Schema updates reviewed and merged by maintainers
- Transforms patched mechanically where possible
- Community notified of breaking changes

**Phase 4: Public drift feed (optional)**
- Publish anonymized drift digests (no customer data)
- RSS/JSON feed of detected changes
- Subscribers get early warning before their pipelines break

### Sandbox Account Strategy

For credible drift detection, maintain sandbox accounts with:

| Provider | Account Type | Purpose |
|----------|--------------|---------|
| Google | Workspace test domain | Gmail, Calendar, Drive, Forms |
| Microsoft | Developer tenant | Graph API (Exchange, OneDrive, Teams) |
| Stripe | Test mode | Payments, Subscriptions, Invoices |
| Salesforce | Developer org | CRM objects |
| HubSpot | Developer account | Marketing, CRM |

These are low-risk (no production data), low-cost (free tiers), and provide real API responses for schema validation.

### What Lives Where

| Concern | Location | Notes |
|---------|----------|-------|
| Transform logic | Canonizer package | `canonicalize()`, `diff`, `patch` |
| Versioned schemas | canonizer-registry | Git repo with CI validation |
| Transform definitions | canonizer-registry | `.jsonata` + `.meta.yaml` |
| Sandbox polling | Separate service | Not in Canonizer |
| Drift detection | Separate service | Uses Canonizer for diffing |
| Notifications | Separate service | Email, Slack, webhooks |
| Public drift feed | Registry sidecar | Static JSON/RSS files |

Canonizer stays focused on transformation. Everything else is ecosystem.
