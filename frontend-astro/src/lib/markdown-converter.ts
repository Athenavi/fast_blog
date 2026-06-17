// Markdown ↔ HTML bidirectional converter
// Used for WYSIWYG ↔ Source mode switching in the article editor
import TurndownService from 'turndown';
import {marked} from 'marked';

const turndown = new TurndownService({
  headingStyle: 'atx',
  hr: '---',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced',
  emDelimiter: '*',
  strongDelimiter: '**',
  linkStyle: 'inlined',
  linkReferenceStyle: 'full',
});

// Preserve image alt-text during conversion
turndown.addRule('images', {
  filter: 'img',
  replacement: (_content, node) => {
    const el = node as HTMLImageElement;
    const alt = el.alt || '';
    const src = el.getAttribute('src') || '';
    return `![${alt}](${src})`;
  },
});

// Convert video/audio to markdown links
turndown.addRule('videos', {
  filter: ['video', 'audio'],
  replacement: (_content, node) => {
    const el = node as HTMLVideoElement | HTMLAudioElement;
    const src = el.getAttribute('src') || el.querySelector('source')?.getAttribute('src') || '';
    const label = el.getAttribute('title') || el.getAttribute('alt') || src.split('/').pop() || 'media';
    return `[${label}](${src})`;
  },
});

export function htmlToMarkdown(html: string): string {
  if (!html) return '';
  return turndown.turndown(html);
}

export function markdownToHtml(md: string): string {
  if (!md) return '';
  return marked.parse(md, {async: false}) as string;
}
