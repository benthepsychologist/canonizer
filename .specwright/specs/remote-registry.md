---
version: "0.1"
tier: C
title: Remote Registry Infrastructure
owner: benthepsychologist
goal: Implement remote registry with static hosting, pull/sync commands, and CI publishing
labels: [registry, remote, cdn, infrastructure]
project_slug: canonizer
spec_version: 0.1.0
created: 2025-11-26T00:00:00+00:00
updated: 2025-12-01T00:00:00+00:00
status: complete
depends_on: local-registry-mvp
---

# Remote Registry Infrastructure

## Objective

> Build the remote registry infrastructure: static file hosting, pull/sync CLI commands,
> and CI automation for publishing schemas and transforms.

## Prerequisites

- local-registry-mvp spec completed
- `.canonizer/` directory model working
- Local resolution functions implemented

## Context

### Architecture

```
canonizer-registry (git repo)     →  Static host (CDN)
       ↓                                    ↓
   PRs, CI, SoT                    GET /schemas/..., GET /transforms/...
                                            ↓
                                   canonizer CLI pulls to .canonizer/
                                            ↓
                                   Local validation (no network needed)
```

**Source of Truth:** Git repo (`canonizer-registry`)
- Human-readable history
- PR-based contributions
- CI validation

**Consumer Endpoint:** Static file host
- Simple HTTP GET
- No auth for public schemas
- ETag/Last-Modified caching

## Acceptance Criteria

- [ ] Static file hosting deployed (GitHub Pages or equivalent)
- [ ] `canonizer registry pull <ref>` fetches from remote
- [ ] `canonizer registry sync` fetches all lock.json dependencies
- [ ] Hash verification on pull
- [ ] CI publishes to static host on merge to main
- [ ] Index file generation for discovery
- [ ] Channel support (stable, beta) - optional v1

## Scope

### In Scope

1. **Static file hosting**
   - Deploy to GitHub Pages (simplest) or Cloudflare R2
   - URL structure: `https://registry.canonizer.dev/schemas/...`
   - CORS headers for browser access (optional)

2. **Registry CLI commands**
   ```bash
   # Pull single ref
   canonizer registry pull iglu:com.google/gmail_email/jsonschema/1-0-0
   canonizer registry pull transform:email/gmail_to_jmap_lite/1.0.0

   # Pull by vendor/domain (convenience)
   canonizer registry pull com.google
   canonizer registry pull transforms/email

   # Sync all dependencies from lock.json
   canonizer registry sync

   # List available schemas/transforms
   canonizer registry list
   canonizer registry list --schemas
   canonizer registry list --transforms
   ```

3. **Config file updates**
   ```yaml
   # .canonizer/config.yaml
   registry:
     mode: remote  # or "local" for offline
     remote: https://registry.canonizer.dev
     channel: stable
   ```

4. **Hash verification**
   - Verify SHA256 on pull
   - Fail if hash mismatch
   - Store hashes in lock.json

5. **CI automation**
   - GitHub Actions workflow
   - Validate schemas on PR
   - Publish to static host on merge
   - Generate `index.json` manifest

### Out of Scope

- Authentication/private registries
- Schema submission via CLI (`canonizer registry submit`)
- Multiple registry sources
- Mirroring/caching proxies

## Implementation Plan

### Step 1: Static hosting setup
- Choose host (GitHub Pages recommended for simplicity)
- Configure domain (optional: registry.canonizer.dev)
- Set up directory structure

### Step 2: Index generation
- Script to generate `index.json` from registry contents
- Include all schema refs, transform refs, versions

### Step 3: CI workflow
- Validate schemas on PR
- Publish to static host on merge
- Generate and publish index

### Step 4: Pull command
- HTTP client (httpx)
- Download to `.canonizer/registry/`
- Verify hash
- Update lock.json

### Step 5: Sync command
- Read lock.json
- Pull all missing/outdated refs
- Verify all hashes

### Step 6: List command
- Fetch index.json
- Display available schemas/transforms
- Filter by vendor/domain

## File Formats

### index.json (on static host)
```json
{
  "version": "1.0.0",
  "updated": "2025-11-26T00:00:00Z",
  "schemas": {
    "iglu:com.google/gmail_email/jsonschema/1-0-0": {
      "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
      "hash": "sha256:abc123...",
      "size": 4521
    }
  },
  "transforms": {
    "transform:email/gmail_to_jmap_lite/1.0.0": {
      "path": "transforms/email/gmail_to_jmap_lite/1.0.0/",
      "files": ["spec.meta.yaml", "spec.jsonata"],
      "hash": "sha256:def456..."
    }
  }
}
```

## Notes

- This spec builds on local-registry-mvp
- Can be deferred until multiple consumers need shared registry
- GitHub Pages is simplest starting point
- Consider Cloudflare R2 for better performance/control later
