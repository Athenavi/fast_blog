/**
 * Markdown Worker - 在 Web Worker 中执行 Markdown 转换
 * 将耗时的 Markdown→HTML 转换移至后台线程，避免阻塞主线程
 */

import TurndownService from 'turndown';
import {marked} from 'marked';

// 配置 Turndown
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

// 保留图片 alt-text
turndown.addRule('images', {
  filter: 'img',
  replacement: (_content, node) => {
    const el = node as HTMLImageElement;
    const alt = el.alt || '';
    const src = el.getAttribute('src') || '';
    return `![${alt}](${src})`;
  },
});

// 转换视频/音频为 markdown 链接
turndown.addRule('videos', {
  filter: ['video', 'audio'],
  replacement: (_content, node) => {
    const el = node as HTMLVideoElement | HTMLAudioElement;
    const src = el.getAttribute('src') || el.querySelector('source')?.getAttribute('src') || '';
    const label = el.getAttribute('title') || el.getAttribute('alt') || src.split('/').pop() || 'media';
    return `[${label}](${src})`;
  },
});

// Worker 消息处理
self.onmessage = function (e: MessageEvent<{
  type: 'markdownToHtml' | 'htmlToMarkdown';
  id: number;
  content: string;
}>) {
  const {type, id, content} = e.data;

  try {
    let result: string;

    if (type === 'markdownToHtml') {
      result = content ? (marked.parse(content, {async: false}) as string) : '';
    } else {
      result = content ? turndown.turndown(content) : '';
    }

    self.postMessage({
      type: 'result',
      id,
      result
    });
  } catch (error) {
    self.postMessage({
      type: 'error',
      id,
      error: error instanceof Error ? error.message : String(error)
    });
  }
};

export {};
