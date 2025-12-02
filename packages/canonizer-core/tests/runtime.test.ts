import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { runTransform, validateData, TransformError } from '../src/runtime.js';
import { ValidationError } from '../src/validator.js';

describe('runTransform', () => {
  let tmpDir: string;

  beforeAll(() => {
    // Create a temp registry with test transform and schemas
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'canonizer-runtime-test-'));

    // Create schemas
    const inputSchemaDir = path.join(tmpDir, 'schemas', 'com.test', 'input', 'jsonschema');
    const outputSchemaDir = path.join(tmpDir, 'schemas', 'org.canonical', 'output', 'jsonschema');
    fs.mkdirSync(inputSchemaDir, { recursive: true });
    fs.mkdirSync(outputSchemaDir, { recursive: true });

    fs.writeFileSync(
      path.join(inputSchemaDir, '1-0-0.json'),
      JSON.stringify({
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'object',
        required: ['name'],
        properties: {
          name: { type: 'string' },
          html: { type: 'string' },
        },
      })
    );

    fs.writeFileSync(
      path.join(outputSchemaDir, '1-0-0.json'),
      JSON.stringify({
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'object',
        required: ['displayName'],
        properties: {
          displayName: { type: 'string' },
          content: { type: 'string' },
        },
      })
    );

    // Create simple transform without extensions
    const simpleTransformDir = path.join(tmpDir, 'transforms', 'test', 'simple', '1-0-0');
    fs.mkdirSync(simpleTransformDir, { recursive: true });

    fs.writeFileSync(
      path.join(simpleTransformDir, 'spec.meta.yaml'),
      `id: test/simple
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
`
    );

    fs.writeFileSync(
      path.join(simpleTransformDir, 'spec.jsonata'),
      `{
  "displayName": name,
  "content": html
}`
    );

    // Create transform with extensions
    const extTransformDir = path.join(tmpDir, 'transforms', 'test', 'with_extension', '1-0-0');
    fs.mkdirSync(extTransformDir, { recursive: true });

    fs.writeFileSync(
      path.join(extTransformDir, 'spec.meta.yaml'),
      `id: test/with_extension
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
extensions:
  - name: htmlToMarkdown
    impl: canonizer.extensions.html_to_markdown@1.0.0
`
    );

    fs.writeFileSync(
      path.join(extTransformDir, 'spec.jsonata'),
      `{
  "displayName": name,
  "content": $htmlToMarkdown(html)
}`
    );
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('should run a simple transform', async () => {
    const input = { name: 'John', html: '<p>Hello</p>' };
    const result = await runTransform('test/simple@1-0-0', input, {
      registryRoot: tmpDir,
    });

    expect(result).toEqual({
      displayName: 'John',
      content: '<p>Hello</p>',
    });
  });

  it('should run a transform with extensions', async () => {
    const input = { name: 'John', html: '<p>Hello <strong>world</strong></p>' };
    const result = await runTransform('test/with_extension@1-0-0', input, {
      registryRoot: tmpDir,
    });

    expect(result).toEqual({
      displayName: 'John',
      content: 'Hello **world**',
    });
  });

  it('should validate input by default', async () => {
    const input = { invalid: 'missing name' };

    await expect(
      runTransform('test/simple@1-0-0', input, { registryRoot: tmpDir })
    ).rejects.toThrow(ValidationError);
  });

  it('should skip input validation when disabled', async () => {
    const input = { invalid: 'missing name' };

    // Should not throw on input validation, but output might be invalid
    const result = await runTransform('test/simple@1-0-0', input, {
      registryRoot: tmpDir,
      validateInput: false,
      validateOutput: false,
    });

    expect(result).toBeDefined();
  });

  it('should validate output by default', async () => {
    // Create a transform that produces invalid output
    const badTransformDir = path.join(tmpDir, 'transforms', 'test', 'bad_output', '1-0-0');
    fs.mkdirSync(badTransformDir, { recursive: true });

    fs.writeFileSync(
      path.join(badTransformDir, 'spec.meta.yaml'),
      `id: test/bad_output
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
`
    );

    // This transform produces output missing required 'displayName'
    fs.writeFileSync(
      path.join(badTransformDir, 'spec.jsonata'),
      `{ "content": html }`
    );

    const input = { name: 'John', html: '<p>Hello</p>' };

    await expect(
      runTransform('test/bad_output@1-0-0', input, { registryRoot: tmpDir })
    ).rejects.toThrow(ValidationError);
  });

  it('should skip output validation when disabled', async () => {
    const badTransformDir = path.join(tmpDir, 'transforms', 'test', 'bad_output2', '1-0-0');
    fs.mkdirSync(badTransformDir, { recursive: true });

    fs.writeFileSync(
      path.join(badTransformDir, 'spec.meta.yaml'),
      `id: test/bad_output2
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
`
    );

    fs.writeFileSync(path.join(badTransformDir, 'spec.jsonata'), `{ "invalid": 123 }`);

    const input = { name: 'John', html: '<p>Hello</p>' };

    const result = await runTransform('test/bad_output2@1-0-0', input, {
      registryRoot: tmpDir,
      validateOutput: false,
    });

    expect(result).toEqual({ invalid: 123 });
  });

  it('should throw TransformError for non-existent transform', async () => {
    await expect(
      runTransform('nonexistent/transform@1-0-0', {}, { registryRoot: tmpDir })
    ).rejects.toThrow(TransformError);
  });

  it('should throw TransformError for invalid JSONata', async () => {
    const badJsonataDir = path.join(tmpDir, 'transforms', 'test', 'bad_jsonata', '1-0-0');
    fs.mkdirSync(badJsonataDir, { recursive: true });

    fs.writeFileSync(
      path.join(badJsonataDir, 'spec.meta.yaml'),
      `id: test/bad_jsonata
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
`
    );

    fs.writeFileSync(path.join(badJsonataDir, 'spec.jsonata'), `{ invalid jsonata syntax `);

    const input = { name: 'John', html: '<p>Hello</p>' };

    await expect(
      runTransform('test/bad_jsonata@1-0-0', input, { registryRoot: tmpDir })
    ).rejects.toThrow(TransformError);
  });
});

describe('validateData', () => {
  let tmpDir: string;

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'canonizer-validate-test-'));

    const schemaDir = path.join(tmpDir, 'schemas', 'com.test', 'example', 'jsonschema');
    fs.mkdirSync(schemaDir, { recursive: true });

    fs.writeFileSync(
      path.join(schemaDir, '1-0-0.json'),
      JSON.stringify({
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'object',
        required: ['id'],
        properties: {
          id: { type: 'string' },
        },
      })
    );
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('should pass for valid data', () => {
    expect(() =>
      validateData({ id: 'test' }, 'iglu:com.test/example/jsonschema/1-0-0', tmpDir)
    ).not.toThrow();
  });

  it('should throw ValidationError for invalid data', () => {
    expect(() =>
      validateData({ invalid: true }, 'iglu:com.test/example/jsonschema/1-0-0', tmpDir)
    ).toThrow(ValidationError);
  });
});
