import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { execSync, spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const CLI_PATH = path.join(__dirname, '..', 'bin', 'canonizer-core');

/**
 * Run CLI command and return result
 */
function runCli(
  args: string[],
  stdin?: string,
  options: { cwd?: string } = {}
): { stdout: string; stderr: string; exitCode: number } {
  try {
    const result = execSync(`node ${CLI_PATH} ${args.join(' ')}`, {
      input: stdin,
      encoding: 'utf-8',
      cwd: options.cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { stdout: result, stderr: '', exitCode: 0 };
  } catch (err: unknown) {
    const error = err as {
      stdout?: string;
      stderr?: string;
      status?: number;
    };
    return {
      stdout: error.stdout || '',
      stderr: error.stderr || '',
      exitCode: error.status || 1,
    };
  }
}

describe('CLI', () => {
  let tmpDir: string;

  beforeAll(() => {
    // Create a temp registry with test transform and schemas
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'canonizer-cli-test-'));

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

    // Create simple transform
    const transformDir = path.join(tmpDir, 'transforms', 'test', 'simple', '1-0-0');
    fs.mkdirSync(transformDir, { recursive: true });

    fs.writeFileSync(
      path.join(transformDir, 'spec.meta.yaml'),
      `id: test/simple
version: 1-0-0
from_schema: iglu:com.test/input/jsonschema/1-0-0
to_schema: iglu:org.canonical/output/jsonschema/1-0-0
`
    );

    fs.writeFileSync(
      path.join(transformDir, 'spec.jsonata'),
      `{
  "displayName": name,
  "content": html
}`
    );
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  describe('version', () => {
    it('should show version', () => {
      const result = runCli(['--version']);
      expect(result.exitCode).toBe(0);
      expect(result.stdout.trim()).toMatch(/^\d+\.\d+\.\d+$/);
    });
  });

  describe('help', () => {
    it('should show help', () => {
      const result = runCli(['--help']);
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toContain('canonizer-core');
      expect(result.stdout).toContain('run');
      expect(result.stdout).toContain('validate');
    });
  });

  describe('run', () => {
    it('should transform valid input', () => {
      const input = JSON.stringify({ name: 'John', html: '<p>Hello</p>' });
      const result = runCli(
        ['run', '--transform', 'test/simple@1-0-0', '--registry', tmpDir],
        input
      );

      expect(result.exitCode).toBe(0);
      const output = JSON.parse(result.stdout);
      expect(output).toEqual({
        displayName: 'John',
        content: '<p>Hello</p>',
      });
    });

    it('should fail with invalid input', () => {
      const input = JSON.stringify({ invalid: 'missing name' });
      const result = runCli(
        ['run', '--transform', 'test/simple@1-0-0', '--registry', tmpDir],
        input
      );

      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain('validation failed');
    });

    it('should succeed with --no-validate on invalid input', () => {
      const input = JSON.stringify({ invalid: 'missing name' });
      const result = runCli(
        ['run', '--transform', 'test/simple@1-0-0', '--registry', tmpDir, '--no-validate'],
        input
      );

      expect(result.exitCode).toBe(0);
    });

    it('should fail for non-existent transform', () => {
      const input = JSON.stringify({ name: 'John' });
      const result = runCli(
        ['run', '--transform', 'nonexistent/transform@1-0-0', '--registry', tmpDir],
        input
      );

      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain('Error');
    });
  });

  describe('validate', () => {
    it('should validate valid data', () => {
      const input = JSON.stringify({ name: 'John', html: 'test' });
      const result = runCli(
        ['validate', '--schema', 'iglu:com.test/input/jsonschema/1-0-0', '--registry', tmpDir],
        input
      );

      expect(result.exitCode).toBe(0);
      expect(result.stdout.trim()).toBe('');
    });

    it('should fail for invalid data', () => {
      const input = JSON.stringify({ invalid: 'missing name' });
      const result = runCli(
        ['validate', '--schema', 'iglu:com.test/input/jsonschema/1-0-0', '--registry', tmpDir],
        input
      );

      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain('validation failed');
    });
  });

  describe('check', () => {
    it('should validate a valid transform', () => {
      const result = runCli([
        'check',
        '--transform',
        'test/simple@1-0-0',
        '--registry',
        tmpDir,
      ]);

      expect(result.exitCode).toBe(0);
      expect(result.stdout).toContain('is valid');
    });

    it('should fail for non-existent transform', () => {
      const result = runCli([
        'check',
        '--transform',
        'nonexistent/transform@1-0-0',
        '--registry',
        tmpDir,
      ]);

      expect(result.exitCode).toBe(1);
    });
  });
});
