import { describe, it, expect } from 'vitest';
import { validateAgainstSchema, ValidationError, createValidator } from '../src/validator.js';

const simpleSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  type: 'object',
  required: ['name', 'age'],
  properties: {
    name: { type: 'string' },
    age: { type: 'integer', minimum: 0 },
    email: { type: 'string', format: 'email' },
  },
};

describe('validateAgainstSchema', () => {
  it('should pass validation for valid data', () => {
    const data = { name: 'John', age: 30 };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).not.toThrow();
  });

  it('should pass validation with optional fields', () => {
    const data = { name: 'John', age: 30, email: 'john@example.com' };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).not.toThrow();
  });

  it('should throw ValidationError for missing required field', () => {
    const data = { name: 'John' };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).toThrow(ValidationError);

    try {
      validateAgainstSchema(data, simpleSchema, 'input');
    } catch (err) {
      expect(err).toBeInstanceOf(ValidationError);
      const validationErr = err as ValidationError;
      expect(validationErr.context).toBe('input');
      expect(validationErr.errors.length).toBeGreaterThan(0);
      expect(validationErr.message).toBe('Input validation failed');
    }
  });

  it('should throw ValidationError for wrong type', () => {
    const data = { name: 'John', age: 'thirty' };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).toThrow(ValidationError);
  });

  it('should throw ValidationError for constraint violation', () => {
    const data = { name: 'John', age: -5 };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).toThrow(ValidationError);
  });

  it('should validate format constraints', () => {
    const data = { name: 'John', age: 30, email: 'not-an-email' };

    expect(() => validateAgainstSchema(data, simpleSchema, 'input')).toThrow(ValidationError);
  });

  it('should distinguish between input and output context', () => {
    const data = { name: 'John' };

    try {
      validateAgainstSchema(data, simpleSchema, 'output');
    } catch (err) {
      const validationErr = err as ValidationError;
      expect(validationErr.context).toBe('output');
      expect(validationErr.message).toBe('Output validation failed');
    }
  });
});

describe('ValidationError', () => {
  it('should format errors correctly', () => {
    const data = { name: 123, age: -5 };

    try {
      validateAgainstSchema(data, simpleSchema, 'input');
    } catch (err) {
      const validationErr = err as ValidationError;
      const formatted = validationErr.formatErrors();

      expect(formatted).toContain('Input validation failed');
      expect(formatted).toContain('/name:');
      expect(formatted).toContain('/age:');
    }
  });

  it('should handle empty errors array', () => {
    const err = new ValidationError('Test message', 'input', []);
    expect(err.formatErrors()).toBe('Test message');
  });
});

describe('createValidator', () => {
  it('should create a reusable validator function', () => {
    const validate = createValidator(simpleSchema);

    expect(() => validate({ name: 'John', age: 30 }, 'input')).not.toThrow();
    expect(() => validate({ name: 'Jane', age: 25 }, 'output')).not.toThrow();
    expect(() => validate({ name: 'Bad' }, 'input')).toThrow(ValidationError);
  });
});

describe('complex schema validation', () => {
  const complexSchema = {
    $schema: 'http://json-schema.org/draft-07/schema#',
    type: 'object',
    required: ['id', 'data'],
    properties: {
      id: { type: 'string' },
      data: {
        type: 'object',
        required: ['items'],
        properties: {
          items: {
            type: 'array',
            items: {
              type: 'object',
              required: ['value'],
              properties: {
                value: { type: 'number' },
              },
            },
          },
        },
      },
    },
  };

  it('should validate nested objects', () => {
    const validData = {
      id: 'test-1',
      data: {
        items: [{ value: 1 }, { value: 2 }],
      },
    };

    expect(() => validateAgainstSchema(validData, complexSchema, 'input')).not.toThrow();
  });

  it('should report errors in nested paths', () => {
    const invalidData = {
      id: 'test-1',
      data: {
        items: [{ value: 1 }, { value: 'not-a-number' }],
      },
    };

    try {
      validateAgainstSchema(invalidData, complexSchema, 'input');
      expect.fail('Should have thrown');
    } catch (err) {
      const validationErr = err as ValidationError;
      const formatted = validationErr.formatErrors();
      expect(formatted).toContain('/data/items/1/value');
    }
  });
});
