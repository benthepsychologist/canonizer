/**
 * Core types for canonizer-core
 */

/**
 * Reference to an extension function with versioned implementation
 */
export interface ExtensionRef {
  /** Extension function name (e.g., "htmlToMarkdown") */
  name: string;
  /** Implementation reference (e.g., "canonizer.extensions.html_to_markdown@1.0.0") */
  impl: string;
}

/**
 * Transform specification loaded from meta.yaml + .jsonata files
 */
export interface TransformSpec {
  /** Transform ID (e.g., "clinical_document/dataverse_to_canonical") */
  id: string;
  /** Version in dash-separated format (e.g., "1-0-0") */
  version: string;
  /** Iglu URI for input schema (e.g., "iglu:com.microsoft/dataverse_report/jsonschema/1-0-0") */
  sourceSchema: string;
  /** Iglu URI for output schema */
  targetSchema: string;
  /** Extension functions required by this transform */
  extensions: ExtensionRef[];
  /** JSONata expression body */
  body: string;
  /** SHA256 checksum of the .jsonata file */
  checksum?: string;
}

/**
 * Parsed Iglu URI components
 */
export interface IgluUri {
  vendor: string;
  name: string;
  format: string;
  version: string;
}

/**
 * Parsed transform ID components
 */
export interface TransformId {
  domain: string;
  name: string;
  version: string;
}
