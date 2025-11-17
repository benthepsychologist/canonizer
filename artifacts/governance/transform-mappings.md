# Dataverse Transform Field Mappings

## Overview
Complete field mapping reference for all three Dataverse to Canonical transforms.

---

## Transform 1: Contact

**File:** `transforms/contact/dataverse_contact_to_canonical_v1.jsonata`

**Source Schema:** Microsoft Dynamics 365 Contact entity (Dataverse)
**Target Schema:** `iglu:org.canonical/contact/jsonschema/1-0-0`

### Field Mappings

| Canonical Field | Dataverse Source Field | Data Type | Transform Logic | Notes |
|----------------|----------------------|-----------|----------------|-------|
| `contact_id` | `contactid` | string (GUID) | Direct mapping | Primary identifier |
| `first_name` | `firstname` | string | Direct mapping | |
| `last_name` | `lastname` | string | Direct mapping | |
| `email` | `emailaddress1` | string | Direct mapping | Primary email |
| `phone` | `telephone1` | string | Direct mapping | Primary phone |
| `mobile` | `mobilephone` | string | Direct mapping | Mobile phone |
| `birth_date` | `birthdate` | string (ISO date) | Direct mapping | Format: YYYY-MM-DD |
| `address` | multiple fields | object | Conditional creation | Only created if any address field present |
| `address.line1` | `address1_line1` | string | Direct mapping | |
| `address.line2` | `address1_line2` | string | Direct mapping | |
| `address.city` | `address1_city` | string | Direct mapping | |
| `address.state` | `address1_stateorprovince` | string | Direct mapping | |
| `address.postal_code` | `address1_postalcode` | string | Direct mapping | |
| `address.country` | `address1_country` | string | Direct mapping | |
| `created_at` | `createdon` | string (ISO datetime) | Direct mapping | Record creation timestamp |
| `updated_at` | `modifiedon` | string (ISO datetime) | Direct mapping | Last modification timestamp |
| `source.platform` | (static) | string | `"dataverse"` | Data lineage tracking |
| `source.platform_version` | (static) | string | `"v1"` | API version tracking |

### Conditional Logic

```jsonata
"address": (address1_line1 or address1_line2 or address1_city or
            address1_stateorprovince or address1_postalcode or address1_country) ? {
  // address fields only if at least one is present
}
```

### Unmapped Source Fields
The following Dataverse contact fields are **not** mapped (may be added in future versions):
- `emailaddress2`, `emailaddress3` (additional emails)
- `telephone2`, `telephone3` (additional phones)
- `fax` (fax number)
- `jobtitle`, `department` (employment info)
- `gendercode`, `familystatuscode` (demographic codes)
- `preferredcontactmethodcode` (contact preference)
- `address2_*`, `address3_*` (additional addresses)

---

## Transform 2: Clinical Session

**File:** `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata`

**Source Schema:** Custom Dynamics 365 Appointment/Session entity
**Target Schema:** `iglu:org.canonical/clinical_session/jsonschema/1-0-0`

### Field Mappings

| Canonical Field | Dataverse Source Field | Data Type | Transform Logic | Notes |
|----------------|----------------------|-----------|----------------|-------|
| `session_id` | `sessionid` or `appointmentid` | string (GUID) | `$string(sessionid ? sessionid : appointmentid)` | Fallback to appointmentid if sessionid not present |
| `scheduled_start` | `scheduledstart` | string (ISO datetime) | Direct mapping | Planned start time |
| `scheduled_end` | `scheduledend` | string (ISO datetime) | Direct mapping | Planned end time |
| `actual_start` | `actualstart` | string (ISO datetime) | Direct mapping | Actual start time (may be null) |
| `actual_end` | `actualend` | string (ISO datetime) | Direct mapping | Actual end time (may be null) |
| `subject` | `subject` | string | Direct mapping | Session title |
| `description` | `description` | string | Direct mapping | Session notes/description |
| `status` | `statuscode` | string (enum) | Status code lookup | Maps integer to string |
| `contact_id` | `regardingobjectid` or `_ben_contactid_value` | string (GUID) | `$string(regardingobjectid ? regardingobjectid : _ben_contactid_value)` | Related patient/contact |
| `session_type` | `_ben_sessiontype_value` | string | Direct mapping | Custom field (type of session) |
| `duration_minutes` | `scheduleddurationminutes` | number | Direct mapping | Session duration |
| `created_at` | `createdon` | string (ISO datetime) | Direct mapping | Record creation timestamp |
| `updated_at` | `modifiedon` | string (ISO datetime) | Direct mapping | Last modification timestamp |
| `source.platform` | (static) | string | `"dataverse"` | Data lineage tracking |
| `source.platform_version` | (static) | string | `"v1"` | API version tracking |

### Status Code Mapping

```jsonata
$lookup({
  "1": "scheduled",
  "2": "completed",
  "3": "cancelled",
  "4": "in_progress",
  "5": "no_show"
}, $string(statuscode))
```

| Status Code | Canonical Status | Meaning |
|-------------|-----------------|---------|
| 1 | scheduled | Session is scheduled/upcoming |
| 2 | completed | Session occurred and was completed |
| 3 | cancelled | Session was cancelled |
| 4 | in_progress | Session is currently happening |
| 5 | no_show | Patient did not attend scheduled session |

**Note:** Unknown status codes will result in `undefined` (field will be omitted).

### Custom Field Assumptions

- `_ben_sessiontype_value`: Assumes custom choice field with publisher prefix `_ben_`
- `_ben_contactid_value`: Custom lookup to contact entity (fallback if `regardingobjectid` not used)

### Unmapped Source Fields
The following potential session fields are **not** mapped:
- `location` (session location)
- `requiredattendees` (participants)
- `optionalattendees` (optional participants)
- `activityid` (if session extends activity entity)
- Custom billing/payment fields

---

## Transform 3: Report

**File:** `transforms/report/dataverse_report_to_canonical_v1.jsonata`

**Source Schema:** Custom Dynamics 365 Report/Annotation entity
**Target Schema:** `iglu:org.canonical/report/jsonschema/1-0-0`

### Field Mappings

| Canonical Field | Dataverse Source Field | Data Type | Transform Logic | Notes |
|----------------|----------------------|-----------|----------------|-------|
| `report_id` | `reportid` or `annotationid` | string (GUID) | `$string(reportid ? reportid : annotationid)` | Fallback to annotationid if custom reportid not present |
| `title` | `subject` or `filename` | string | Conditional: `subject ? subject : filename` | Fallback to filename if subject not present |
| `report_type` | `_ben_reporttype_value` | string | Direct mapping | Custom field for report categorization |
| `report_date` | `reportdate` or `createdon` | string (ISO datetime) | `$string(reportdate ? reportdate : createdon)` | Fallback to creation date |
| `content` | `notetext` or `documentbody` | string | `notetext ? notetext : documentbody` | Report text content (may be base64 if binary) |
| `contact_id` | `_ben_contactid_value` or `objectid` | string (GUID) | `$string(_ben_contactid_value ? _ben_contactid_value : objectid)` | Related patient/contact |
| `session_id` | `_ben_sessionid_value` | string (GUID) | `$string(_ben_sessionid_value)` | Related clinical session (may be null) |
| `status` | `statuscode` | string (enum) | Status code lookup | Maps integer to string |
| `created_at` | `createdon` | string (ISO datetime) | Direct mapping | Record creation timestamp |
| `updated_at` | `modifiedon` | string (ISO datetime) | Direct mapping | Last modification timestamp |
| `source.platform` | (static) | string | `"dataverse"` | Data lineage tracking |
| `source.platform_version` | (static) | string | `"v1"` | API version tracking |

### Status Code Mapping

```jsonata
$lookup({
  "1": "draft",
  "2": "final",
  "3": "amended",
  "4": "archived"
}, $string(statuscode))
```

| Status Code | Canonical Status | Meaning |
|-------------|-----------------|---------|
| 1 | draft | Report is in draft state |
| 2 | final | Report is finalized |
| 3 | amended | Report has been amended/revised |
| 4 | archived | Report is archived |

### Entity Type Assumptions

The report transform assumes one of two possible Dataverse entity types:

1. **Custom Report Entity**
   - Fields: `reportid`, `subject`, `reportdate`, etc.
   - Purpose-built for clinical reports

2. **Standard Annotation Entity**
   - Fields: `annotationid`, `filename`, `notetext`, `documentbody`
   - Repurposed for document/report storage

The transform handles both by checking for existence of custom fields first, falling back to annotation fields.

### Content Handling

- Text reports: Stored directly in `content` field
- Binary documents: May be base64-encoded in `documentbody`
- Large documents: May be references/URLs rather than full content

**Note:** Binary document handling may require additional processing in the pipeline.

### Unmapped Source Fields
The following potential report fields are **not** mapped:
- `mimetype` (document type)
- `filesize` (document size)
- `isdocument` (boolean flag)
- `objecttypecode` (related entity type code)
- Custom approval workflow fields

---

## Cross-Transform Patterns

### Common Patterns Used in All Transforms

1. **GUID String Coercion**
   ```jsonata
   $string(guidField)
   ```
   Ensures GUIDs are consistently output as strings.

2. **Conditional Field Creation**
   ```jsonata
   fieldValue ? { "nested": fieldValue }
   ```
   Only creates nested objects when source data exists.

3. **Fallback Chaining**
   ```jsonata
   primaryField ? primaryField : fallbackField
   ```
   Gracefully handles field name variations.

4. **Static Source Metadata**
   ```jsonata
   "source": {
     "platform": "dataverse",
     "platform_version": "v1"
   }
   ```
   Consistent data lineage tracking.

5. **Status Code Lookups**
   ```jsonata
   $lookup({ "1": "value", ... }, $string(statuscode))
   ```
   Converts integer codes to readable strings.

---

## Validation Checklist

When validating these transforms against real data:

- [ ] Verify GUID fields are properly stringified
- [ ] Check ISO datetime format is correct
- [ ] Confirm status code mappings match Dataverse configuration
- [ ] Validate custom field prefixes match actual schema
- [ ] Test conditional logic with missing/null fields
- [ ] Verify lookup field naming (e.g., `_value` suffix)
- [ ] Check address object only created when data exists
- [ ] Confirm all required canonical fields are populated
- [ ] Test relationship IDs (contact_id, session_id) are correct
- [ ] Validate content field handles both text and binary data

---

## Maintenance Notes

### When to Update These Mappings

1. **Dataverse Schema Changes**
   - Custom field additions
   - Field renames
   - New status codes

2. **Canonical Schema Evolution**
   - New required fields
   - Deprecated fields
   - Schema version increments

3. **Data Quality Issues**
   - Discovered field name mismatches
   - Missing critical data
   - Format incompatibilities

### Version Control

Current transform version: **v1**

For breaking changes, create new versioned transforms:
- `dataverse_contact_to_canonical_v2.jsonata`
- Update `to_schema` Iglu URI to `1-1-0` or `2-0-0` as appropriate

---

## References

- [Microsoft Dataverse Web API](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview)
- [Contact Entity Reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/contact)
- [Appointment Entity Reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/appointment)
- [Annotation Entity Reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/annotation)
- [JSONata Expression Language](https://docs.jsonata.org/)
