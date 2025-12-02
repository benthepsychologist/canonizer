/**
 * HTML to Markdown extension function
 * Converts HTML content to Markdown format using Turndown
 */

import TurndownService from 'turndown';

// Configure Turndown with sensible defaults
const turndown = new TurndownService({
  headingStyle: 'atx',           // Use # style headings
  hr: '---',                     // Horizontal rule style
  bulletListMarker: '-',         // Bullet list marker
  codeBlockStyle: 'fenced',      // Use ``` for code blocks
  emDelimiter: '_',              // Emphasis delimiter
  strongDelimiter: '**',         // Strong delimiter
  linkStyle: 'inlined',          // Inline links [text](url)
});

/**
 * Convert HTML to Markdown
 * @param html - HTML string to convert
 * @returns Markdown string
 */
export function htmlToMarkdownV1(html: string): string {
  if (!html || typeof html !== 'string') {
    return '';
  }

  // Trim whitespace
  const trimmed = html.trim();
  if (trimmed === '') {
    return '';
  }

  try {
    return turndown.turndown(trimmed);
  } catch {
    // If conversion fails, return the original text stripped of tags
    return trimmed.replace(/<[^>]*>/g, '');
  }
}
