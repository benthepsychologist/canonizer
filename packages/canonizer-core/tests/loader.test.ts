import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import {
  parseIgluUri,
  parseTransformId,
  resolveSchemaPath,
  resolveTransformDir,
  loadTransformSpec,
  loadSchema,
} from '../src/loader.js';

describe('parseIgluUri', () => {
  it('should parse a valid Iglu URI', () => {
    const uri = 'iglu:com.microsoft/dataverse_report/jsonschema/1-0-0';
    const result = parseIgluUri(uri);

    expect(result).toEqual({
      vendor: 'com.microsoft',
      name: 'dataverse_report',
      format: 'jsonschema',
      version: '1-0-0',
    });
  });

  it('should throw for URI without iglu: prefix', () => {
    expect(() => parseIgluUri('com.microsoft/dataverse_report/jsonschema/1-0-0')).toThrow(
      'must start with "iglu:"'
    );
  });

  it('should throw for URI with wrong number of parts', () => {
    expect(() => parseIgluUri('iglu:com.microsoft/dataverse_report')).toThrow(
      'expected format'
    );
  });
});

describe('parseTransformId', () => {
  it('should parse a valid transform ID', () => {
    const id = 'clinical_document/dataverse_to_canonical@1-0-0';
    const result = parseTransformId(id);

    expect(result).toEqual({
      domain: 'clinical_document',
      name: 'dataverse_to_canonical',
      version: '1-0-0',
    });
  });

  it('should handle nested domain paths', () => {
    const id = 'email/gmail_to_jmap_full@1.0.0';
    const result = parseTransformId(id);

    expect(result).toEqual({
      domain: 'email',
      name: 'gmail_to_jmap_full',
      version: '1.0.0',
    });
  });

  it('should throw for ID without version', () => {
    expect(() => parseTransformId('clinical_document/dataverse_to_canonical')).toThrow(
      'must include version with @'
    );
  });

  it('should throw for ID without domain', () => {
    expect(() => parseTransformId('transform_name@1-0-0')).toThrow(
      'expected format'
    );
  });
});

describe('resolveSchemaPath', () => {
  it('should resolve schema path correctly', () => {
    const igluUri = {
      vendor: 'com.microsoft',
      name: 'dataverse_report',
      format: 'jsonschema',
      version: '1-0-0',
    };
    const result = resolveSchemaPath(igluUri, '/registry');

    expect(result).toBe(
      path.join('/registry', 'schemas', 'com.microsoft', 'dataverse_report', 'jsonschema', '1-0-0.json')
    );
  });
});

describe('resolveTransformDir', () => {
  it('should resolve transform directory correctly', () => {
    const transformId = {
      domain: 'clinical_document',
      name: 'dataverse_to_canonical',
      version: '1-0-0',
    };
    const result = resolveTransformDir(transformId, '/registry');

    expect(result).toBe(
      path.join('/registry', 'transforms', 'clinical_document', 'dataverse_to_canonical', '1-0-0')
    );
  });
});

describe('loadTransformSpec', () => {
  let tmpDir: string;

  beforeAll(() => {
    // Create a temp registry with test data
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'canonizer-test-'));

    // Create transform directory
    const transformDir = path.join(tmpDir, 'transforms', 'test', 'example', '1-0-0');
    fs.mkdirSync(transformDir, { recursive: true });

    // Write meta.yaml
    fs.writeFileSync(
      path.join(transformDir, 'spec.meta.yaml'),
      `id: test/example
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
checksum:
  jsonata_sha256: abc123
extensions:
  - name: htmlToMarkdown
    impl: canonizer.extensions.html_to_markdown@1.0.0
`
    );

    // Write spec.jsonata
    fs.writeFileSync(path.join(transformDir, 'spec.jsonata'), '{ "result": $.input }');
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('should load a transform spec', () => {
    const spec = loadTransformSpec('test/example@1-0-0', tmpDir);

    expect(spec.id).toBe('test/example');
    expect(spec.version).toBe('1-0-0');
    expect(spec.sourceSchema).toBe('iglu:com.test/input/jsonschema/1-0-0');
    expect(spec.targetSchema).toBe('iglu:org.canonical/output/jsonschema/1-0-0');
    expect(spec.checksum).toBe('abc123');
    expect(spec.extensions).toEqual([
      { name: 'htmlToMarkdown', impl: 'canonizer.extensions.html_to_markdown@1.0.0' },
    ]);
    expect(spec.body).toBe('{ "result": $.input }');
  });

  it('should throw for non-existent transform', () => {
    expect(() => loadTransformSpec('nonexistent/transform@1-0-0', tmpDir)).toThrow(
      'Transform meta file not found'
    );
  });
});

describe('loadSchema', () => {
  let tmpDir: string;

  beforeAll(() => {
    // Create a temp registry with test schema
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'canonizer-schema-test-'));

    const schemaDir = path.join(tmpDir, 'schemas', 'com.test', 'example', 'jsonschema');
    fs.mkdirSync(schemaDir, { recursive: true });

    fs.writeFileSync(
      path.join(schemaDir, '1-0-0.json'),
      JSON.stringify({
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'object',
        properties: {
          name: { type: 'string' },
        },
      })
    );
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('should load a schema', () => {
    const schema = loadSchema('iglu:com.test/example/jsonschema/1-0-0', tmpDir);

    expect(schema).toEqual({
      $schema: 'http://json-schema.org/draft-07/schema#',
      type: 'object',
      properties: {
        name: { type: 'string' },
      },
    });
  });

  it('should throw for non-existent schema', () => {
    expect(() => loadSchema('iglu:com.test/nonexistent/jsonschema/1-0-0', tmpDir)).toThrow(
      'Schema file not found'
    );
  });
});
