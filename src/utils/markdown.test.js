import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderMarkdown } from './markdown.js';

test('renderMarkdown converts emphasis and unordered lists to HTML', () => {
  const html = renderMarkdown('**推荐游览路线**\n\n- 头门\n- 聚贤堂');

  assert.match(html, /<strong>推荐游览路线<\/strong>/);
  assert.match(html, /<ul>/);
  assert.match(html, /<li>头门<\/li>/);
  assert.match(html, /<li>聚贤堂<\/li>/);
});

test('renderMarkdown escapes raw HTML from model output', () => {
  const html = renderMarkdown('<script>alert("xss")</script>');

  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});
