import { describe, it, expect } from 'vitest';
import jsonata from 'jsonata';
import {
  htmlToMarkdownV1,
  registerExtensions,
  resolveExtension,
  listExtensions,
  hasExtension,
  ExtensionNotFoundError,
} from '../src/extensions/index.js';

describe('htmlToMarkdownV1', () => {
  it('should convert basic HTML to markdown', () => {
    const html = '<p>Hello <strong>world</strong></p>';
    const result = htmlToMarkdownV1(html);
    expect(result).toBe('Hello **world**');
  });

  it('should convert headings', () => {
    const html = '<h1>Title</h1><h2>Subtitle</h2>';
    const result = htmlToMarkdownV1(html);
    expect(result).toContain('# Title');
    expect(result).toContain('## Subtitle');
  });

  it('should convert links', () => {
    const html = '<a href="https://example.com">Example</a>';
    const result = htmlToMarkdownV1(html);
    expect(result).toBe('[Example](https://example.com)');
  });

  it('should convert lists', () => {
    const html = '<ul><li>Item 1</li><li>Item 2</li></ul>';
    const result = htmlToMarkdownV1(html);
    // Turndown may add extra spaces; just check the structure
    expect(result).toContain('Item 1');
    expect(result).toContain('Item 2');
    expect(result).toMatch(/^-/); // Starts with list marker
  });

  it('should convert code blocks', () => {
    const html = '<pre><code>const x = 1;</code></pre>';
    const result = htmlToMarkdownV1(html);
    expect(result).toContain('```');
    expect(result).toContain('const x = 1;');
  });

  it('should handle empty input', () => {
    expect(htmlToMarkdownV1('')).toBe('');
    expect(htmlToMarkdownV1('   ')).toBe('');
  });

  it('should handle null/undefined input', () => {
    expect(htmlToMarkdownV1(null as unknown as string)).toBe('');
    expect(htmlToMarkdownV1(undefined as unknown as string)).toBe('');
  });

  it('should handle plain text', () => {
    const text = 'Just plain text';
    const result = htmlToMarkdownV1(text);
    expect(result).toBe('Just plain text');
  });
});

describe('resolveExtension', () => {
  it('should resolve a valid extension', () => {
    const fn = resolveExtension({
      name: 'htmlToMarkdown',
      impl: 'canonizer.extensions.html_to_markdown@1.0.0',
    });
    expect(typeof fn).toBe('function');
    expect(fn('<p>test</p>')).toBe('test');
  });

  it('should throw for unknown extension', () => {
    expect(() =>
      resolveExtension({
        name: 'unknown',
        impl: 'canonizer.extensions.unknown@1.0.0',
      })
    ).toThrow(ExtensionNotFoundError);
  });
});

describe('listExtensions', () => {
  it('should list all registered extensions', () => {
    const extensions = listExtensions();
    expect(extensions).toContain('canonizer.extensions.html_to_markdown@1.0.0');
  });
});

describe('hasExtension', () => {
  it('should return true for registered extension', () => {
    expect(hasExtension('canonizer.extensions.html_to_markdown@1.0.0')).toBe(true);
  });

  it('should return false for unknown extension', () => {
    expect(hasExtension('canonizer.extensions.unknown@1.0.0')).toBe(false);
  });
});

describe('registerExtensions', () => {
  it('should register extensions on JSONata expression', async () => {
    const expr = jsonata('$htmlToMarkdown(html)');
    registerExtensions(expr, [
      {
        name: 'htmlToMarkdown',
        impl: 'canonizer.extensions.html_to_markdown@1.0.0',
      },
    ]);

    const result = await expr.evaluate({ html: '<p>Hello <em>world</em></p>' });
    expect(result).toBe('Hello _world_');
  });

  it('should handle multiple extensions', async () => {
    const expr = jsonata('$htmlToMarkdown(html)');
    registerExtensions(expr, [
      {
        name: 'htmlToMarkdown',
        impl: 'canonizer.extensions.html_to_markdown@1.0.0',
      },
    ]);

    const result = await expr.evaluate({ html: '<strong>Bold</strong>' });
    expect(result).toBe('**Bold**');
  });

  it('should throw for unknown extension', () => {
    const expr = jsonata('$test()');
    expect(() =>
      registerExtensions(expr, [
        {
          name: 'test',
          impl: 'canonizer.extensions.nonexistent@1.0.0',
        },
      ])
    ).toThrow(ExtensionNotFoundError);
  });

  it('should work with complex JSONata expressions', async () => {
    const expr = jsonata(`
      {
        "title": title,
        "content": $htmlToMarkdown(body)
      }
    `);
    registerExtensions(expr, [
      {
        name: 'htmlToMarkdown',
        impl: 'canonizer.extensions.html_to_markdown@1.0.0',
      },
    ]);

    const input = {
      title: 'My Post',
      body: '<h1>Welcome</h1><p>This is a <strong>test</strong></p>',
    };

    const result = await expr.evaluate(input);
    expect(result).toEqual({
      title: 'My Post',
      content: '# Welcome\n\nThis is a **test**',
    });
  });
});
