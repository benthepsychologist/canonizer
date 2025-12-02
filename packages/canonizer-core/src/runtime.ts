/**
 * Transform runtime
 * Ties together loader, validation, extensions, and JSONata execution
 */

import jsonata from 'jsonata';
import { loadTransformSpec, loadSchema } from './loader.js';
import { validateAgainstSchema } from './validator.js';
import { registerExtensions } from './extensions/index.js';

/**
 * Default registry root - relative to cwd
 */
const DEFAULT_REGISTRY_ROOT = '.';

/**
 * Options for running a transform
 */
export interface RunOptions {
  /** Validate input against source schema (default: true) */
  validateInput?: boolean;
  /** Validate output against target schema (default: true) */
  validateOutput?: boolean;
  /** Path to the registry root directory */
  registryRoot?: string;
}

/**
 * Error thrown when transform execution fails
 */
export class TransformError extends Error {
  constructor(
    message: string,
    public readonly transformId: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'TransformError';
  }
}

/**
 * Run a transform on input data
 *
 * This is the main entry point for executing transforms. It:
 * 1. Loads the transform specification (meta.yaml + .jsonata)
 * 2. Optionally validates input against the source schema
 * 3. Compiles and executes the JSONata expression with extensions
 * 4. Optionally validates output against the target schema
 * 5. Returns the transformed output
 *
 * @param transformId - Transform ID with version (e.g., "clinical_document/dataverse_to_canonical@1-0-0")
 * @param input - Input data to transform
 * @param options - Run options
 * @returns Transformed output
 * @throws TransformError if transform execution fails
 * @throws ValidationError if input or output validation fails
 */
export async function runTransform(
  transformId: string,
  input: unknown,
  options: RunOptions = {}
): Promise<unknown> {
  const {
    validateInput = true,
    validateOutput = true,
    registryRoot = DEFAULT_REGISTRY_ROOT,
  } = options;

  // Load the transform specification
  let spec;
  try {
    spec = loadTransformSpec(transformId, registryRoot);
  } catch (err) {
    throw new TransformError(
      `Failed to load transform: ${transformId}`,
      transformId,
      err instanceof Error ? err : undefined
    );
  }

  // Validate input against source schema
  if (validateInput) {
    try {
      const sourceSchema = loadSchema(spec.sourceSchema, registryRoot);
      validateAgainstSchema(input, sourceSchema, 'input');
    } catch (err) {
      if (err instanceof Error && err.name === 'ValidationError') {
        throw err; // Re-throw validation errors as-is
      }
      throw new TransformError(
        `Failed to validate input for transform: ${transformId}`,
        transformId,
        err instanceof Error ? err : undefined
      );
    }
  }

  // Compile and execute JSONata expression
  let output: unknown;
  try {
    const expr = jsonata(spec.body);

    // Register extension functions if any
    if (spec.extensions.length > 0) {
      registerExtensions(expr, spec.extensions);
    }

    // Execute the transform
    output = await expr.evaluate(input);
  } catch (err) {
    throw new TransformError(
      `Failed to execute transform: ${transformId}`,
      transformId,
      err instanceof Error ? err : undefined
    );
  }

  // Validate output against target schema
  if (validateOutput) {
    try {
      const targetSchema = loadSchema(spec.targetSchema, registryRoot);
      validateAgainstSchema(output, targetSchema, 'output');
    } catch (err) {
      if (err instanceof Error && err.name === 'ValidationError') {
        throw err; // Re-throw validation errors as-is
      }
      throw new TransformError(
        `Failed to validate output for transform: ${transformId}`,
        transformId,
        err instanceof Error ? err : undefined
      );
    }
  }

  return output;
}

/**
 * Validate data against a schema without running a transform
 *
 * @param data - Data to validate
 * @param schemaUri - Iglu schema URI
 * @param registryRoot - Path to the registry root directory
 * @throws ValidationError if validation fails
 */
export function validateData(
  data: unknown,
  schemaUri: string,
  registryRoot: string = DEFAULT_REGISTRY_ROOT
): void {
  const schema = loadSchema(schemaUri, registryRoot);
  validateAgainstSchema(data, schema, 'input');
}
