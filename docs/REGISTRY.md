# Canonizer Registry Guide

The Canonizer Registry is a Git-based repository of versioned JSON transforms with CI-driven validation and HTTP-based discovery.

## Overview

- **Repository**: [benthepsychologist/canonizer-registry](https://github.com/benthepsychologist/canonizer-registry)
- **Registry Type**: Git-based with PR workflow
- **Validation**: Automated CI checks on every PR
- **Discovery**: HTTP-based via `REGISTRY_INDEX.json`
- **Governance**: Apache-2.0 license with CODEOWNERS

## Using the Registry

### 1. List Available Transforms

```bash
# List all transforms
can registry list

# List only stable transforms
can registry list --status stable

# Force refresh from registry
can registry list --refresh
```

### 2. Search for Transforms

```bash
# Find transforms from a specific source schema
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0

# Find transforms to a canonical schema
can registry search --to iglu:org.canonical/email/jsonschema/1-0-0

# Search by transform ID
can registry search --id email/gmail_to_canonical

# Combine filters
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0 --status stable
```

### 3. Get Transform Information

```bash
# Get detailed info about a transform
can registry info email/gmail_to_canonical@1.0.0

# Get info about latest version
can registry info email/gmail_to_canonical@latest
```

### 4. Pull and Use a Transform

```bash
# Pull a specific version
can registry pull email/gmail_to_canonical@1.0.0

# Pull latest version
can registry pull email/gmail_to_canonical@latest

# Transform downloaded to: ~/.cache/canonizer/registry/<hash>/transforms/<id>/<version>/
```

### 5. Use a Pulled Transform

```bash
# After pulling, use the transform
can transform run \
  --meta ~/.cache/canonizer/registry/.../email/gmail_to_canonical/1.0.0/spec.meta.yaml \
  --input gmail_message.json \
  --output canonical_email.json
```

## Contributing Transforms

### Transform Structure

Each transform version lives in its own directory:

```
transforms/
  <domain>/
    <transform_id>/
      <version>/
        spec.jsonata        # Transform logic (source of truth)
        spec.meta.yaml      # Metadata sidecar
        tests/
          input.json        # Golden test input
          expected.json     # Expected output
```

### Metadata Format

`spec.meta.yaml` example:

```yaml
# Transform identity
id: email/gmail_to_canonical
version: 1.0.0
engine: jsonata

# Schema contracts
from_schema: iglu:com.google/gmail_email/jsonschema/1-0-0
to_schema: iglu:org.canonical/email/jsonschema/1-0-0

# Transform file
spec_path: spec.jsonata

# Golden tests (required)
tests:
  - input: tests/input.json
    expect: tests/expected.json

# Integrity
checksum:
  jsonata_sha256: "<hex>"

# Provenance
provenance:
  author: "Your Name <you@example.com>"
  created_utc: "2025-11-13T00:00:00Z"

# Lifecycle
status: stable  # draft | stable | deprecated
```

### Contribution Workflow

1. **Fork the registry repository**
   ```bash
   gh repo fork benthepsychologist/canonizer-registry
   cd canonizer-registry
   ```

2. **Create your transform**
   ```bash
   mkdir -p transforms/your_domain/your_transform/1.0.0/tests

   # Create spec.jsonata with your transform logic
   vim transforms/your_domain/your_transform/1.0.0/spec.jsonata

   # Create spec.meta.yaml with metadata
   vim transforms/your_domain/your_transform/1.0.0/spec.meta.yaml

   # Create golden tests
   vim transforms/your_domain/your_transform/1.0.0/tests/input.json
   vim transforms/your_domain/your_transform/1.0.0/tests/expected.json
   ```

3. **Compute checksum**
   ```bash
   shasum -a 256 transforms/your_domain/your_transform/1.0.0/spec.jsonata
   # Add this hex value to spec.meta.yaml checksum.jsonata_sha256
   ```

4. **Validate locally**
   ```bash
   python tools/validate.py transforms/your_domain/your_transform/1.0.0/
   ```

5. **Commit and push**
   ```bash
   git add transforms/your_domain/
   git commit -m "Add your_transform v1.0.0"
   git push origin main
   ```

6. **Open a Pull Request**
   - Use the PR template
   - Explain the use case
   - Provide sample input/output
   - Link to source schema documentation
   - CI will validate your submission

7. **CI Validation**
   - Directory structure checks
   - Metadata validation (Pydantic)
   - Checksum verification
   - Golden tests execution
   - Schema references validation
   - Unique (id, version) constraint

8. **Merge and Index Generation**
   - Upon merge, CI generates updated `REGISTRY_INDEX.json`
   - Transform becomes available via `can registry` commands

## Versioning Policy

### Transform Versions (SemVer)

- **MAJOR** (X.0.0): Breaking changes (different output schema, incompatible input)
- **MINOR** (x.Y.0): New features (support for new input schema version, new optional fields)
- **PATCH** (x.y.Z): Bug fixes (same I/O contracts, improved logic)

### Schema Versions (Iglu SchemaVer)

- **MODEL-REVISION-ADDITION** format (e.g., `1-0-0`)
- **MODEL**: Breaking changes (remove field, change type)
- **REVISION**: Non-breaking changes (modify description)
- **ADDITION**: Additive changes (new optional field)

### Compatibility

Transforms declare:
- **Exact `to_schema`**: Strict output contract
- **Exact `from_schema`** by default: Single input schema version
- **Optional `compat.from_schema_range`**: Support for multiple input versions
  - Example: `"1-0-0 .. 1-2-x"` means MODEL=1, REVISION=0-2, any ADDITION

## Security & Governance

### Security Model

- **No code execution in registry**: JSONata only, no eval/exec
- **Checksum verification**: Prevents tampering
- **PR review required**: No direct commits to main
- **Provenance tracking**: Author and timestamp in metadata
- **Sandboxed CI execution**: Isolated runner, no network access

### Governance

- **License**: Apache-2.0 (permissive, community-friendly)
- **CODEOWNERS**: Namespace ownership for critical schemas
- **Review process**: Maintainer approval required for canonical schemas
- **No PII in fixtures**: Test data must be anonymized

### Pull Request Template

Required information:
- Transform ID and version
- Source and target schemas
- Rationale (use case)
- Sample input/output (anonymized)
- Link to official source API docs

## Example Workflows

### Workflow 1: Find and Use Transform

```bash
# Search for Gmail transforms
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0

# Get detailed info
can registry info email/gmail_to_canonical@latest

# Pull the transform
can registry pull email/gmail_to_canonical@1.0.0

# Use it
can transform run \
  --meta ~/.cache/canonizer/registry/.../1.0.0/spec.meta.yaml \
  --input gmail_message.json \
  --output canonical_email.json
```

### Workflow 2: Contribute New Transform

```bash
# Fork and clone registry
gh repo fork benthepsychologist/canonizer-registry
cd canonizer-registry

# Create transform directory
mkdir -p transforms/crm/salesforce_to_canonical/1.0.0/tests

# Write transform logic
cat > transforms/crm/salesforce_to_canonical/1.0.0/spec.jsonata <<'EOF'
{
  "contact_id": payload.Id,
  "name": payload.Name,
  "email": payload.Email,
  "created_at": $toMillis($fromMillis(payload.CreatedDate))
}
EOF

# Create metadata (fill in checksum after computing)
cat > transforms/crm/salesforce_to_canonical/1.0.0/spec.meta.yaml <<'EOF'
id: crm/salesforce_to_canonical
version: 1.0.0
engine: jsonata
from_schema: iglu:com.salesforce/contact/jsonschema/1-0-0
to_schema: iglu:org.canonical/contact/jsonschema/1-0-0
spec_path: spec.jsonata
tests:
  - input: tests/input.json
    expect: tests/expected.json
checksum:
  jsonata_sha256: "<compute with shasum -a 256>"
provenance:
  author: "You <you@example.com>"
  created_utc: "2025-11-13T00:00:00Z"
status: draft
EOF

# Create golden tests
# ... (add test files)

# Compute checksum
shasum -a 256 transforms/crm/salesforce_to_canonical/1.0.0/spec.jsonata

# Validate locally
python tools/validate.py transforms/crm/salesforce_to_canonical/1.0.0/

# Commit and open PR
git add transforms/crm/
git commit -m "Add Salesforce to canonical transform"
git push origin main
gh pr create --fill
```

### Workflow 3: Update Transform for New Schema

```bash
# Pull existing transform
can registry pull email/gmail_to_canonical@1.0.0

# Copy to new version directory
cp -r ~/.cache/canonizer/registry/.../1.0.0 transforms/email/gmail_to_canonical/1.1.0/

# Edit for new schema
vim transforms/email/gmail_to_canonical/1.1.0/spec.jsonata

# Update metadata
# - Bump version: 1.0.0 → 1.1.0 (MINOR for new output schema)
# - Update to_schema to new version
# - Recompute checksum
vim transforms/email/gmail_to_canonical/1.1.0/spec.meta.yaml

# Validate and contribute
python tools/validate.py transforms/email/gmail_to_canonical/1.1.0/
git add transforms/email/gmail_to_canonical/1.1.0/
git commit -m "Update gmail_to_canonical for schema v1.1.0"
git push origin main
gh pr create --fill
```

## Cache Management

### Cache Location

```bash
~/.cache/canonizer/registry/<url-hash>/
  ├── REGISTRY_INDEX.json
  └── transforms/
      └── <id>/
          └── <version>/
              ├── spec.jsonata
              └── spec.meta.yaml
```

### Cache Operations

```bash
# List uses cached index (1 hour TTL)
can registry list

# Force refresh
can registry list --refresh

# Pull always fetches fresh
can registry pull email/gmail_to_canonical@1.0.0

# Clear cache manually
rm -rf ~/.cache/canonizer/registry/
```

## Troubleshooting

### "Transform not found"

- Check spelling of transform ID
- Verify version exists: `can registry list`
- Try refreshing cache: `can registry list --refresh`

### "Checksum verification failed"

- File was corrupted during download
- Try pulling again
- If persistent, report issue on GitHub

### "404 Not Found" for registry

- Check internet connection
- Verify registry URL is correct
- Default: https://raw.githubusercontent.com/benthepsychologist/canonizer-registry/main/

### Custom Registry

```bash
# Use a different registry
can registry list --registry-url https://example.com/my-registry/
can registry pull my_transform@1.0.0 --registry-url https://example.com/my-registry/
```

## Advanced Topics

### Multiple Registries

Currently, Canonizer supports one registry at a time via `--registry-url`. Future versions may support multiple configured registries.

### Private Transforms

For private transforms, host your own registry:
1. Fork `canonizer-registry` as a private repo
2. Set up CI with same validation
3. Use `--registry-url` to point to your private registry
4. Ensure authentication for raw.githubusercontent.com URLs

### Offline Usage

1. Pull all needed transforms while online
2. Cache persists at `~/.cache/canonizer/registry/`
3. Use cached transforms offline via file paths

## Additional Resources

- [Canonizer Main Documentation](../README.md)
- [Registry Repository](https://github.com/benthepsychologist/canonizer-registry)
- [JSONata Documentation](https://docs.jsonata.org/)
- [Iglu Schema Registry](https://github.com/snowplow/iglu)
- [SemVer Specification](https://semver.org/)

## Support

- Issues: [GitHub Issues](https://github.com/benthepsychologist/canonizer/issues)
- Registry Issues: [Registry Issues](https://github.com/benthepsychologist/canonizer-registry/issues)
- Discussions: [GitHub Discussions](https://github.com/benthepsychologist/canonizer/discussions)
