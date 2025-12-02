#!/usr/bin/env node
/**
 * CLI for canonizer-core
 *
 * I/O Contract:
 * - Input: JSON from stdin
 * - Output: JSON to stdout (success) or error message to stderr (failure)
 * - Exit code: 0 = success, non-zero = failure
 */

import { Command } from 'commander';
import { runTransform, validateData } from './runtime.js';
import { ValidationError } from './validator.js';

const VERSION = '0.1.0';

/**
 * Read all data from stdin as a string
 */
async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

/**
 * Parse JSON from string, with error handling
 */
function parseJson(input: string): unknown {
  try {
    return JSON.parse(input);
  } catch {
    throw new Error(`Invalid JSON input: ${input.slice(0, 100)}...`);
  }
}

const program = new Command();

program
  .name('canonizer-core')
  .description('Node.js runtime for JSONata transforms with extensions')
  .version(VERSION);

program
  .command('run')
  .description('Transform JSON input to output')
  .requiredOption('-t, --transform <id>', 'Transform ID with version (e.g., domain/name@1-0-0)')
  .option('-r, --registry <path>', 'Path to registry root', '.')
  .option('--no-validate', 'Skip input/output validation')
  .action(async (options) => {
    try {
      // Read and parse input from stdin
      const inputStr = await readStdin();
      const input = parseJson(inputStr);

      // Run the transform
      const output = await runTransform(options.transform, input, {
        registryRoot: options.registry,
        validateInput: options.validate,
        validateOutput: options.validate,
      });

      // Output JSON to stdout
      console.log(JSON.stringify(output, null, 2));
      process.exit(0);
    } catch (err) {
      // Output error to stderr
      if (err instanceof ValidationError) {
        console.error(err.formatErrors());
      } else if (err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error('Unknown error occurred');
      }
      process.exit(1);
    }
  });

program
  .command('validate')
  .description('Validate JSON against schema')
  .requiredOption('-s, --schema <uri>', 'Iglu schema URI')
  .option('-r, --registry <path>', 'Path to registry root', '.')
  .action(async (options) => {
    try {
      // Read and parse input from stdin
      const inputStr = await readStdin();
      const input = parseJson(inputStr);

      // Validate against schema
      validateData(input, options.schema, options.registry);

      // Success - exit 0 with no output
      process.exit(0);
    } catch (err) {
      // Output error to stderr
      if (err instanceof ValidationError) {
        console.error(err.formatErrors());
      } else if (err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error('Unknown error occurred');
      }
      process.exit(1);
    }
  });

program
  .command('validate-file')
  .description('Validate JSON against schema file (not via Iglu URI)')
  .requiredOption('-f, --file <path>', 'Path to JSON Schema file')
  .action(async (options) => {
    try {
      const fs = await import('fs');
      const { validateAgainstSchema } = await import('./validator.js');

      // Read and parse schema file
      const schemaContent = fs.readFileSync(options.file, 'utf-8');
      const schema = JSON.parse(schemaContent);

      // Read and parse input from stdin
      const inputStr = await readStdin();
      const input = parseJson(inputStr);

      // Validate against schema
      validateAgainstSchema(input, schema, 'input');

      // Success - exit 0 with no output
      process.exit(0);
    } catch (err) {
      if (err instanceof ValidationError) {
        console.error(err.formatErrors());
      } else if (err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error('Unknown error occurred');
      }
      process.exit(1);
    }
  });

program
  .command('jsonata')
  .description('Execute raw JSONata expression on JSON input')
  .requiredOption('-e, --expr <expression>', 'JSONata expression to evaluate')
  .action(async (options) => {
    try {
      // Dynamically import jsonata
      const jsonata = (await import('jsonata')).default;

      // Read and parse input from stdin
      const inputStr = await readStdin();
      const input = parseJson(inputStr);

      // Compile and evaluate expression
      const expression = jsonata(options.expr);
      const result = await expression.evaluate(input);

      // Output JSON to stdout
      console.log(JSON.stringify(result));
      process.exit(0);
    } catch (err) {
      if (err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error('Unknown error occurred');
      }
      process.exit(1);
    }
  });

program
  .command('check')
  .description('Check if a transform can be loaded (validate configuration)')
  .requiredOption('-t, --transform <id>', 'Transform ID with version (e.g., domain/name@1-0-0)')
  .option('-r, --registry <path>', 'Path to registry root', '.')
  .action(async (options) => {
    try {
      // Import loader dynamically to check transform
      const { loadTransformSpec, loadSchema } = await import('./loader.js');
      const { hasExtension } = await import('./extensions/index.js');

      // Try to load the transform
      const spec = loadTransformSpec(options.transform, options.registry);

      // Check that schemas can be loaded
      loadSchema(spec.sourceSchema, options.registry);
      loadSchema(spec.targetSchema, options.registry);

      // Check that all extensions are available
      const missingExtensions: string[] = [];
      for (const ext of spec.extensions) {
        if (!hasExtension(ext.impl)) {
          missingExtensions.push(`${ext.name} (${ext.impl})`);
        }
      }

      if (missingExtensions.length > 0) {
        console.error(`Missing extensions:\n  ${missingExtensions.join('\n  ')}`);
        process.exit(1);
      }

      console.log(`Transform ${options.transform} is valid`);
      console.log(`  Source schema: ${spec.sourceSchema}`);
      console.log(`  Target schema: ${spec.targetSchema}`);
      console.log(`  Extensions: ${spec.extensions.length}`);
      process.exit(0);
    } catch (err) {
      if (err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error('Unknown error occurred');
      }
      process.exit(1);
    }
  });

program.parse();
