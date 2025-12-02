/**
 * Extension function registry
 * Extensions are pure, versioned helper functions for JSONata transforms
 */

import type { Expression } from 'jsonata';
import type { ExtensionRef } from '../types.js';
import { htmlToMarkdownV1 } from './htmlToMarkdown.js';

/**
 * Extension function type - generic function
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ExtensionFn = (...args: any[]) => any;

/**
 * Registry of all available extension implementations
 * Key format: "{namespace}.{name}@{version}"
 */
const extensionRegistry: Record<string, ExtensionFn> = {
  'canonizer.extensions.html_to_markdown@1.0.0': htmlToMarkdownV1,
};

/**
 * Error thrown when an extension cannot be found
 */
export class ExtensionNotFoundError extends Error {
  constructor(
    public readonly name: string,
    public readonly impl: string
  ) {
    super(`Extension not found: ${name} (impl: ${impl})`);
    this.name = 'ExtensionNotFoundError';
  }
}

/**
 * Resolve an extension reference to its implementation
 * @param ref - Extension reference with name and impl
 * @returns The extension function
 * @throws ExtensionNotFoundError if the extension is not registered
 */
export function resolveExtension(ref: ExtensionRef): ExtensionFn {
  const fn = extensionRegistry[ref.impl];
  if (!fn) {
    throw new ExtensionNotFoundError(ref.name, ref.impl);
  }
  return fn;
}

/**
 * Register extension functions on a JSONata expression
 * @param expr - JSONata expression object
 * @param extensionRefs - List of extension references to register
 * @throws ExtensionNotFoundError if any extension is not found
 */
export function registerExtensions(
  expr: Expression,
  extensionRefs: ExtensionRef[]
): void {
  for (const ref of extensionRefs) {
    const fn = resolveExtension(ref);

    // Register the extension function with JSONata
    // The function name exposed to JSONata is the "name" field
    expr.registerFunction(ref.name, fn);
  }
}

/**
 * Get a list of all registered extension implementations
 * Useful for debugging and validation
 */
export function listExtensions(): string[] {
  return Object.keys(extensionRegistry);
}

/**
 * Check if an extension implementation exists
 * @param impl - Implementation reference (e.g., "canonizer.extensions.html_to_markdown@1.0.0")
 */
export function hasExtension(impl: string): boolean {
  return impl in extensionRegistry;
}

// Re-export individual extensions for direct use
export { htmlToMarkdownV1 } from './htmlToMarkdown.js';
