# Transform Design Decision Log

## Project
Dataverse to Canonical Transforms (Contact, Clinical Session, Report)

## Date
2025-11-17

## Context
Creating transforms for Dataverse entities (extracted via tap-dataverse) to canonical formats for the lorchestra PHI data pipeline.

---

## Decision 1: Directory Structure

**Decision:** Use flat directory structure for transform files

**Status:** Accepted

**Details:**
- Pattern: `transforms/{entity}/{source}_to_canonical_v1.jsonata`
- Example: `transforms/contact/dataverse_contact_to_canonical_v1.jsonata`

**Rationale:**
- Matches the existing pattern used in email transforms (e.g., `gmail_to_canonical_v1.jsonata`)
- Simpler structure than versioned subdirectories
- Easier to locate and maintain
- Version is encoded in filename (v1)

**Alternatives Considered:**
- Versioned structure: `transforms/contact/dataverse_to_canonical/1.0.0/spec.jsonata`
- Rejected: More complex, not needed for initial implementation

---

## Decision 2: Canonical Schema Structure

**Decision:** Use JSON Schema Draft 07 with Iglu URI identifiers

**Status:** Accepted

**Details:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "iglu:org.canonical/{entity}/jsonschema/1-0-0",
  ...
}
```

**Rationale:**
- Standard JSON Schema format ensures tooling compatibility
- Iglu URIs provide unique, versioned schema identifiers
- Matches pattern from existing transforms
- org.canonical namespace distinguishes these from source schemas

---

## Decision 3: Dataverse Field Naming

**Decision:** Assume standard Dataverse field names with provision for custom fields

**Status:** Accepted

**Details:**
- Standard fields: lowercase, no prefix (e.g., `contactid`, `firstname`)
- Custom fields: assumed `_ben_` prefix (e.g., `_ben_sessiontype_value`)
- Lookup fields: `_value` suffix for choice/lookup values

**Rationale:**
- Dataverse standard naming convention well-documented
- Custom publisher prefix common pattern in Dynamics 365
- Can be adjusted when actual data schema is available
- Lookup value fields follow Dataverse OData convention

**Risk:** Actual custom field prefixes may differ
**Mitigation:** Document assumption, plan to validate against real data

---

## Decision 4: Status Code Mapping

**Decision:** Map Dataverse integer status codes to human-readable strings

**Status:** Accepted

**Details:**
Clinical Session status mapping:
```jsonata
$lookup({
  "1": "scheduled",
  "2": "completed",
  "3": "cancelled",
  "4": "in_progress",
  "5": "no_show"
}, $string(statuscode))
```

**Rationale:**
- Canonical format should be human-readable
- Integer status codes are Dataverse-specific implementation detail
- Easier for downstream analytics and reporting
- Standard pattern used in other transform systems

**Trade-offs:**
- Requires maintaining mapping table
- Must handle unknown status codes gracefully (will return undefined)
- Status code values may vary by entity/deployment

---

## Decision 5: Date/Time Format

**Decision:** Use ISO 8601 format for all date and datetime fields

**Status:** Accepted

**Details:**
- Dates: YYYY-MM-DD format
- Datetimes: ISO 8601 with timezone (e.g., 2025-11-17T14:30:00Z)
- Store as strings in canonical format

**Rationale:**
- ISO 8601 is universal standard
- Dataverse already outputs in ISO format
- JSON doesn't have native date type
- String format is portable across systems

---

## Decision 6: Conditional Object Creation

**Decision:** Use conditional logic to omit empty nested objects

**Status:** Accepted

**Details:**
```jsonata
"address": (address1_line1 or address1_line2 or ... ) ? {
  "line1": address1_line1,
  ...
}
```

**Rationale:**
- Avoids creating objects with all null/undefined fields
- Cleaner canonical output
- Matches pattern from google_forms_to_canonical transform
- Easier to distinguish "no data" from "data exists but is empty"

**Trade-offs:**
- More complex JSONata expression
- Field may be completely absent vs. present but empty object

---

## Decision 7: Source Metadata

**Decision:** Include `source` object in all canonical outputs

**Status:** Accepted

**Details:**
```json
"source": {
  "platform": "dataverse",
  "platform_version": "v1"
}
```

**Rationale:**
- Enables data lineage tracking
- Distinguishes records from different sources in merged datasets
- Standard pattern across all transforms
- Version field allows for schema evolution

---

## Decision 8: GUID Handling

**Decision:** Store Dataverse GUIDs as strings with $string() coercion

**Status:** Accepted

**Details:**
```jsonata
"contact_id": $string(contactid)
```

**Rationale:**
- GUIDs may come as string or object from different Dataverse API versions
- Explicit string coercion ensures consistent output type
- JSON has no native GUID type
- String format is portable and readable

---

## Decision 9: Schema Validation Approach

**Decision:** Define canonical schemas but defer validation testing until sample data available

**Status:** Accepted

**Details:**
- Created JSON Schema definitions
- Validated schema structure and syntax
- Testing against real data deferred to data availability

**Rationale:**
- No Dataverse sample data currently in `/home/user/phi-data/vault/`
- Schema definitions stable enough to implement
- Real data validation more valuable than synthetic testing
- Reduces implementation timeline

**Follow-up:** Re-validate when tap-dataverse provides sample data

---

## Decision 10: Transform Metadata Files

**Decision:** Defer creation of `.meta.yaml` files to later phase

**Status:** Deferred

**Details:**
- `.meta.yaml` files define checksum, provenance, test fixtures
- Not required for initial transform functionality
- Can be added when test data available

**Rationale:**
- No sample data for test fixtures yet
- Checksums will change if transforms need adjustment after data validation
- Focus on core transform logic first
- Metadata can be added incrementally

---

## Open Questions

1. **Custom Field Prefixes**: Will actual Dataverse deployment use `_ben_` prefix or different publisher prefix?
   - **Resolution Path:** Check with Ben or inspect actual API response when available

2. **Entity Relationship IDs**: How are related entity IDs represented in OData output?
   - **Resolution Path:** Validate with sample data from tap-dataverse

3. **Status Code Values**: Do actual status codes match assumed mappings (1=scheduled, etc.)?
   - **Resolution Path:** Review Dataverse configuration or sample data

4. **Report Entity Type**: Is report data coming from Annotation entity or custom Report entity?
   - **Resolution Path:** Confirm with tap-dataverse schema output

---

## Review History

| Date | Reviewer | Status | Notes |
|------|----------|--------|-------|
| 2025-11-17 | Claude (AIP execution) | Initial | All decisions documented during implementation |

---

## References

- Microsoft Dataverse entity reference: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/
- Iglu schema format: http://iglucentral.com/
- JSONata documentation: https://jsonata.org/
- Existing transforms: `transforms/email/gmail_to_canonical_v1.jsonata`, `transforms/forms/google_forms_to_canonical/`
