/**
 * canonizer-core
 *
 * Node.js runtime for JSONata transforms with extension functions.
 * This is THE engine - all transform logic lives here.
 */

// Re-export public API
export { runTransform, validateData, TransformError, type RunOptions } from './runtime.js';
export { loadTransformSpec, loadSchema, parseIgluUri, parseTransformId } from './loader.js';
export { validateAgainstSchema, ValidationError } from './validator.js';
export { registerExtensions, ExtensionNotFoundError } from './extensions/index.js';
export type { TransformSpec, ExtensionRef, IgluUri, TransformId } from './types.js';
