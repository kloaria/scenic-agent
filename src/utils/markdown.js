import MarkdownIt from 'markdown-it';

const markdown = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: false,
  typographer: false
});

export function renderMarkdown(content) {
  return markdown.render(content);
}
