# Changelog

All notable changes to Canonizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-13

### Added

#### Core Features
- Initial release of Canonizer - Pure JSON transformation tool
- JSONata-based transformation engine with dual runtime support (Node.js + Python)
- Schema validation with Iglu SchemaVer format support
- Transform metadata model with Pydantic validation
- Checksum verification for transform integrity

#### Transform Registry (AIP-canonizer-2025-11-12-001)
- **Git-based transform registry** with HTTP discovery
- **Registry CLI commands:**
  - `can registry list` - List all available transforms
  - `can registry search` - Search by schema URIs, ID, or status
  - `can registry pull` - Download transforms to local cache
  - `can registry info` - Display transform metadata
  - `can registry validate` - Validate transform directories locally
- **Registry client (`RegistryClient`):**
  - Fetch transforms and schemas from GitHub-based registry
  - Local caching at `~/.cache/canonizer/registry/`
  - Automatic checksum verification
  - Index-based efficient discovery
- **Transform validation module:**
  - Directory structure validation
  - Metadata validation with Pydantic
  - Checksum integrity verification
  - Golden test execution
  - Detailed error reporting
- **Official registry** at https://github.com/benthepsychologist/canonizer-registry
  - CI-driven validation on PRs
  - Automatic index generation on merge
  - Initial transform: `email/gmail_to_canonical@1.0.0`

#### CLI Commands
- `can transform run` - Execute JSON transformations
- `can transform list` - List local transforms
- `can validate run` - Validate JSON against schemas
- `can diff run` - Compare schemas and detect changes
- `can patch run` - Apply mechanical updates to transforms

#### Schema Evolution
- Schema differ with change classification (ADD, RENAME, REMOVE, TYPE_CHANGE, COMPLEX)
- Transform patcher for mechanical updates
- Levenshtein distance-based rename detection
- Conservative patching approach (fails safe for complex changes)

#### Documentation
- Comprehensive README with Quick Start guide
- Registry contribution guide (`docs/REGISTRY.md`)
  - Usage instructions for all CLI commands
  - Contribution workflow with examples
  - Versioning policy (SemVer + Iglu SchemaVer)
  - Security and governance model
  - Example workflows
- API documentation with docstrings
- AIP execution summary with full audit trail

### Technical Details

#### Models
- `TransformMeta` - Transform metadata with Pydantic validation
  - `Checksum` model with SHA256 integrity
  - `Provenance` model for authorship tracking
  - `Compat` model for schema version ranges
  - `TestFixture` model for golden tests
- `Transform` - Complete transform with metadata and JSONata source

#### Architecture
- Pure function design (no side effects)
- Portable `.jsonata` files (language-agnostic)
- Minimal `.meta.yaml` sidecars
- Local-first with optional registry
- CLI-first design for composability

### Quality Metrics
- 68 unit and integration tests passing
- 43% overall code coverage (96-100% on registry core modules)
- Ruff linting checks passing
- Type hints with mypy support
- Comprehensive error handling

### Repository Structure
```
canonizer/
├── canonizer/           # Main package
│   ├── cli/            # Typer-based CLI
│   ├── core/           # Transform runtime and evolution
│   └── registry/       # Registry client and validation
├── docs/               # Documentation
├── tests/              # Unit and integration tests
└── transforms/         # Local transform examples
```

### Known Limitations
- CLI commands have 0% test coverage (only manually tested)
- Node.js JSONata runtime requires `npm install jsonata` separately
- Coverage goal of 70% not met (43% overall, but core modules are 96-100%)
- `can registry publish` command not implemented (deferred to v0.2)

### Dependencies
- Python 3.11+
- jsonata-python 0.6+ (Python runtime)
- pydantic 2.5+
- jsonschema 4.20+
- typer 0.9+
- rich 13.7+
- httpx 0.27+
- PyYAML 6.0+

### Migration Notes
This is the initial release. No migration required.

### Credits
- Developed by Ben Machina
- Built with Claude Code (Anthropic Sonnet 4.5)
- Follows AIP (Agentic Implementation Plan) methodology
- Inspired by Snowplow's Iglu schema registry

### Links
- **Main Repository:** https://github.com/benthepsychologist/canonizer
- **Registry Repository:** https://github.com/benthepsychologist/canonizer-registry
- **Documentation:** [docs/REGISTRY.md](docs/REGISTRY.md)
- **AIP:** AIP-canonizer-2025-11-12-001

---

## [0.2.0] - 2025-11-13

### Added

#### Email Canonicalization (AIP-canonizer-2025-11-13-001)
- **6 production email transforms:**
  - `email/gmail_to_jmap_full@1.0.0` - Gmail → JMAP Full (RFC 8621 complete)
  - `email/gmail_to_jmap_lite@1.0.0` - Gmail → JMAP Lite (simplified inline body)
  - `email/gmail_to_jmap_minimal@1.0.0` - Gmail → JMAP Minimal (metadata only)
  - `email/exchange_to_jmap_full@1.0.0` - Exchange → JMAP Full
  - `email/exchange_to_jmap_lite@1.0.0` - Exchange → JMAP Lite
  - `email/exchange_to_jmap_minimal@1.0.0` - Exchange → JMAP Minimal

- **4 new canonical schemas:**
  - `com.microsoft/exchange_email@1-0-0` - Microsoft Graph API Message Resource
  - `org.canonical/email_jmap_full@1-0-0` - RFC 8621 complete (~50-200KB per email)
  - `org.canonical/email_jmap_lite@1-0-0` - Simplified inline body (~10-50KB per email)
  - `org.canonical/email_jmap_minimal@1-0-0` - Metadata only (~1-5KB per email)

- **Comprehensive documentation:**
  - `docs/EMAIL_CANONICALIZATION.md` - Architecture and design decisions
  - Three-tier canonical format strategy (Full/Lite/Minimal)
  - Storage vs. functionality trade-off analysis
  - Use case mapping for each canonical format

- **19 integration tests** covering:
  - Golden test validation for all 6 transforms
  - Invalid input handling
  - Null value handling
  - Schema validation (input and output)
  - Runtime assertions (Node.js JSONata)

### Technical Details
- All transforms use Python jsonata runtime (no Node.js dependency for validation)
- All transforms published to canonizer-registry with CI passing
- Array constructor pattern for JSONata `$map()` single-item compatibility
- Comprehensive email header mapping (from, to, cc, bcc, replyTo, sender)
- Thread tracking support (messageId, inReplyTo, references)
- Attachment handling across all format levels

### Quality Metrics
- 94 total tests passing (up from 68)
- 44% overall code coverage (up from 43%)
- 100% test pass rate for email transforms
- Registry CI validation passing with Python jsonata

## [0.3.0] - 2025-11-17

### Added

#### Dataverse Canonicalization (AIP-canonizer-2025-11-17-001)
- **3 canonical JSON schemas:**
  - `transforms/schemas/canonical/contact_v1-0-0.json` - Contact/person data schema
  - `transforms/schemas/canonical/clinical_session_v1-0-0.json` - Clinical appointment/session schema
  - `transforms/schemas/canonical/report_v1-0-0.json` - Clinical report/document schema

- **3 Dataverse transforms:**
  - `transforms/contact/dataverse_contact_to_canonical_v1.jsonata` - Dataverse Contact → Canonical
  - `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata` - Dataverse Session → Canonical
  - `transforms/report/dataverse_report_to_canonical_v1.jsonata` - Dataverse Report → Canonical

- **Comprehensive governance documentation:**
  - `artifacts/governance/decision-log.md` - 10 design decisions with rationale
  - `artifacts/governance/transform-mappings.md` - Complete field mapping reference for all 3 transforms
  - `artifacts/test/test-pass-confirmation.md` - Test results and validation status

### Technical Details
- **Contact Transform Features:**
  - Standard Dataverse field mapping (contactid, firstname, lastname, etc.)
  - Conditional address object creation (only when data present)
  - Support for email, phone, mobile fields
  - Birth date and timestamp handling

- **Clinical Session Transform Features:**
  - Status code mapping (integer → readable strings: scheduled/completed/cancelled/in_progress/no_show)
  - Fallback handling for field name variations (sessionid/appointmentid)
  - Custom field support with `_ben_` prefix assumption
  - Duration and scheduling metadata

- **Report Transform Features:**
  - Dual entity type support (custom Report entity or standard Annotation entity)
  - Fallback chaining for flexible field mapping
  - Status enumeration (draft/final/amended/archived)
  - Content handling for text and binary documents

- **Design Patterns:**
  - ISO 8601 date/datetime formats for portability
  - GUID string coercion with `$string()` for consistency
  - Source metadata injection (`platform: "dataverse", platform_version: "v1"`)
  - Conditional object creation to avoid empty nested objects

### Quality Metrics
- 94 total tests passing (maintained from v0.2)
- 44% overall code coverage (maintained)
- Ruff linting: All checks passed
- No regressions introduced

### Known Limitations
- No Dataverse sample data available for validation yet (pending tap-dataverse output)
- Field names based on standard Dataverse schema (may need adjustment for custom deployments)
- Test coverage remains at 44% (target: 70%+)
- `.meta.yaml` metadata files deferred until real data validation

### Next Steps
- Validate transforms against real Dataverse data when available from tap-dataverse
- Create `.meta.yaml` metadata files with checksums
- Add integration tests for new transforms
- Consider publishing to canonizer-registry

## [Unreleased]

### Planned for v0.4
- `can registry publish` - Open PR via GitHub API
- Auto-bump version based on diff/patch
- Compatibility matrix validation
- LLM-assisted transform scaffolding
- Increased CLI test coverage (target: 70%+)
- Calendar event canonicalization
- Additional healthcare data transforms (HL7, FHIR)

---

*This changelog follows the [Keep a Changelog](https://keepachangelog.com/) format.*
