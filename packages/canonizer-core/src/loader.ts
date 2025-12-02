/**
 * Transform and schema loader
 * Reads meta.yaml + .jsonata files from the registry
 */

import * as fs from 'fs';
import * as path from 'path';
import { parse as parseYaml } from 'yaml';
import type { TransformSpec, IgluUri, TransformId, ExtensionRef } from './types.js';

/**
 * Parse an Iglu URI into its components
 * Format: iglu:{vendor}/{name}/{format}/{version}
 * Example: iglu:com.microsoft/dataverse_report/jsonschema/1-0-0
 */
export function parseIgluUri(uri: string): IgluUri {
  const igluPrefix = 'iglu:';
  if (!uri.startsWith(igluPrefix)) {
    throw new Error(`Invalid Iglu URI: must start with "${igluPrefix}": ${uri}`);
  }

  const parts = uri.slice(igluPrefix.length).split('/');
  if (parts.length !== 4) {
    throw new Error(
      `Invalid Iglu URI: expected format "iglu:vendor/name/format/version", got: ${uri}`
    );
  }

  const [vendor, name, format, version] = parts;
  return { vendor, name, format, version };
}

/**
 * Parse a transform ID with version
 * Format: {domain}/{name}@{version}
 * Example: clinical_document/dataverse_to_canonical@1-0-0
 */
export function parseTransformId(transformId: string): TransformId {
  const atIndex = transformId.lastIndexOf('@');
  if (atIndex === -1) {
    throw new Error(
      `Invalid transform ID: must include version with @ separator: ${transformId}`
    );
  }

  const idPart = transformId.slice(0, atIndex);
  const version = transformId.slice(atIndex + 1);

  const slashIndex = idPart.indexOf('/');
  if (slashIndex === -1) {
    throw new Error(
      `Invalid transform ID: expected format "domain/name@version", got: ${transformId}`
    );
  }

  const domain = idPart.slice(0, slashIndex);
  const name = idPart.slice(slashIndex + 1);

  return { domain, name, version };
}

/**
 * Resolve the file path for a schema
 * @param igluUri - Iglu URI
 * @param registryRoot - Path to the registry root directory
 */
export function resolveSchemaPath(igluUri: IgluUri, registryRoot: string): string {
  // Path: {registryRoot}/schemas/{vendor}/{name}/{format}/{version}.json
  return path.join(
    registryRoot,
    'schemas',
    igluUri.vendor,
    igluUri.name,
    igluUri.format,
    `${igluUri.version}.json`
  );
}

/**
 * Resolve the directory path for a transform
 * @param transformId - Parsed transform ID
 * @param registryRoot - Path to the registry root directory
 */
export function resolveTransformDir(transformId: TransformId, registryRoot: string): string {
  // Path: {registryRoot}/transforms/{domain}/{name}/{version}/
  return path.join(
    registryRoot,
    'transforms',
    transformId.domain,
    transformId.name,
    transformId.version
  );
}

/**
 * Meta.yaml structure from existing transforms
 */
interface TransformMetaYaml {
  id: string;
  version: string;
  engine?: string;
  runtime?: string;
  from_schema: string;
  to_schema: string;
  spec_path?: string;
  checksum?: {
    jsonata_sha256?: string;
  };
  extensions?: ExtensionRef[];
  provenance?: {
    author?: string;
    created_utc?: string;
  };
  status?: string;
  description?: string;
  tests?: Array<{
    input: string;
    expect: string;
  }>;
}

/**
 * Load a transform specification from the registry
 * @param transformIdStr - Transform ID with version (e.g., "clinical_document/dataverse_to_canonical@1-0-0")
 * @param registryRoot - Path to the registry root directory
 */
export function loadTransformSpec(
  transformIdStr: string,
  registryRoot: string
): TransformSpec {
  const transformId = parseTransformId(transformIdStr);
  const transformDir = resolveTransformDir(transformId, registryRoot);

  // Read spec.meta.yaml
  const metaPath = path.join(transformDir, 'spec.meta.yaml');
  if (!fs.existsSync(metaPath)) {
    throw new Error(`Transform meta file not found: ${metaPath}`);
  }

  const metaContent = fs.readFileSync(metaPath, 'utf-8');
  const meta = parseYaml(metaContent) as TransformMetaYaml;

  // Read spec.jsonata
  const specPath = meta.spec_path || 'spec.jsonata';
  const jsonataPath = path.join(transformDir, specPath);
  if (!fs.existsSync(jsonataPath)) {
    throw new Error(`Transform JSONata file not found: ${jsonataPath}`);
  }

  const body = fs.readFileSync(jsonataPath, 'utf-8');

  return {
    id: meta.id,
    version: meta.version,
    sourceSchema: meta.from_schema,
    targetSchema: meta.to_schema,
    extensions: meta.extensions || [],
    body,
    checksum: meta.checksum?.jsonata_sha256,
  };
}

/**
 * Load a JSON schema from the registry
 * @param schemaUri - Iglu URI (e.g., "iglu:com.microsoft/dataverse_report/jsonschema/1-0-0")
 * @param registryRoot - Path to the registry root directory
 */
export function loadSchema(schemaUri: string, registryRoot: string): object {
  const igluUri = parseIgluUri(schemaUri);
  const schemaPath = resolveSchemaPath(igluUri, registryRoot);

  if (!fs.existsSync(schemaPath)) {
    throw new Error(`Schema file not found: ${schemaPath}`);
  }

  const schemaContent = fs.readFileSync(schemaPath, 'utf-8');
  return JSON.parse(schemaContent);
}
