/**
 * JSON Schema validation using ajv
 * This is the ONLY place validation happens - not Python
 */

import Ajv, { type ErrorObject } from 'ajv';
import addFormats from 'ajv-formats';

// Create a shared Ajv instance with common configuration
const ajv = new (Ajv as unknown as typeof Ajv.default)({
  allErrors: true,        // Report all errors, not just the first
  strict: false,          // Allow additional keywords in schemas
  validateFormats: true,  // Validate format keywords
});

// Add standard formats (date, time, email, uri, etc.)
(addFormats as unknown as typeof addFormats.default)(ajv);

/**
 * Validation error with detailed information
 */
export class ValidationError extends Error {
  constructor(
    message: string,
    public readonly context: 'input' | 'output',
    public readonly errors: ErrorObject[] = []
  ) {
    super(message);
    this.name = 'ValidationError';
  }

  /**
   * Get a formatted string of all validation errors
   */
  formatErrors(): string {
    if (this.errors.length === 0) {
      return this.message;
    }

    const lines = this.errors.map((err) => {
      const path = err.instancePath || '(root)';
      const message = err.message || 'unknown error';
      const params = err.params ? ` (${JSON.stringify(err.params)})` : '';
      return `  - ${path}: ${message}${params}`;
    });

    return `${this.message}:\n${lines.join('\n')}`;
  }
}

/**
 * Validate data against a JSON schema
 * @param data - Data to validate
 * @param schema - JSON Schema object
 * @param context - Whether this is input or output validation
 * @throws ValidationError if validation fails
 */
export function validateAgainstSchema(
  data: unknown,
  schema: object,
  context: 'input' | 'output'
): void {
  // Compile the schema (ajv caches compiled schemas)
  const validate = ajv.compile(schema);
  const valid = validate(data);

  if (!valid) {
    const errors = validate.errors || [];
    const message = `${context === 'input' ? 'Input' : 'Output'} validation failed`;
    throw new ValidationError(message, context, errors);
  }
}

/**
 * Create a validator function for a specific schema
 * Useful for validating multiple documents against the same schema
 * @param schema - JSON Schema object
 * @returns A validation function that throws ValidationError on failure
 */
export function createValidator(
  schema: object
): (data: unknown, context: 'input' | 'output') => void {
  const validate = ajv.compile(schema);

  return (data: unknown, context: 'input' | 'output') => {
    const valid = validate(data);
    if (!valid) {
      const errors = validate.errors || [];
      const message = `${context === 'input' ? 'Input' : 'Output'} validation failed`;
      throw new ValidationError(message, context, errors);
    }
  };
}
