/**
 * useMarkdownWorker - 使用 Web Worker 进行 Markdown 转换的 Hook
 *
 * 使用示例:
 * ```tsx
 * const {markdownToHtml, htmlToMarkdown} = useMarkdownWorker();
 *
 * // 异步转换
 * const html = await markdownToHtml(markdownContent);
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

interface WorkerMessage {
  type: 'markdownToHtml' | 'htmlToMarkdown' | 'result' | 'error';
  id: number;
  content?: string;
  result?: string;
  error?: string;
}

interface UseMarkdownWorkerResult {
  /** 将 Markdown 转换为 HTML */
  markdownToHtml: (md: string) => Promise<string>;
  /** 将 HTML 转换为 Markdown */
  htmlToMarkdown: (html: string) => Promise<string>;
  /** Worker 是否就绪 */
  ready: boolean;
  /** 当前错误 */
  error: string | null;
}

let sharedWorker: Worker | null = null;

export function useMarkdownWorker(): UseMarkdownWorkerResult {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageIdRef = useRef(0);
  const pendingCallbacksRef = useRef<Map<number, {
    resolve: (value: string) => void;
    reject: (error: Error) => void
  }>>(new Map());

  useEffect(() => {
    // 创建共享 Worker
    if (!sharedWorker) {
      try {
        // 使用 dynamic import 创建 Worker
        const workerScript = new URL(
          '../markdown-worker.ts',
          import.meta.url
        );

        sharedWorker = new Worker(workerScript, {
          type: 'module',
          name: 'markdown-converter'
        });

        // 设置消息处理
        sharedWorker.onmessage = (e: MessageEvent<WorkerMessage>) => {
          const {type, id, result, error: errorMsg} = e.data;

          const callback = pendingCallbacksRef.current.get(id);
          if (!callback) return;

          pendingCallbacksRef.current.delete(id);

          if (type === 'result') {
            callback.resolve(result || '');
          } else if (type === 'error') {
            callback.reject(new Error(errorMsg));
          }
        };

        sharedWorker.onerror = (error) => {
          setError(error.message || 'Worker error occurred');

          // 清除所有待处理的回调
          pendingCallbacksRef.current.forEach(({reject}) => {
            reject(new Error('Worker error'));
          });
          pendingCallbacksRef.current.clear();
        };

        setReady(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create worker');
      }
    } else {
      setReady(true);
    }

    // 清理函数
    return () => {
      // 不清理 sharedWorker，因为其他组件可能还在使用
      // 只在所有实例都卸载时清理
      if (sharedWorker && pendingCallbacksRef.current.size === 0) {
        // 延迟清理，给其他组件时间创建新的引用
        setTimeout(() => {
          if (pendingCallbacksRef.current.size === 0) {
            sharedWorker?.terminate();
            sharedWorker = null;
          }
        }, 1000);
      }
    };
  }, []);

  const markdownToHtml = useCallback((md: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!sharedWorker) {
        // 回退到同步转换
        import('../markdown-converter.ts').then(({markdownToHtml: syncConvert}) => {
          resolve(syncConvert(md));
        }).catch(reject);
        return;
      }

      const id = ++messageIdRef.current;
      pendingCallbacksRef.current.set(id, {resolve, reject});

      sharedWorker.postMessage({
        type: 'markdownToHtml',
        id,
        content: md
      });
    });
  }, []);

  const htmlToMarkdown = useCallback((html: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!sharedWorker) {
        // 回退到同步转换
        import('../markdown-converter.ts').then(({htmlToMarkdown: syncConvert}) => {
          resolve(syncConvert(html));
        }).catch(reject);
        return;
      }

      const id = ++messageIdRef.current;
      pendingCallbacksRef.current.set(id, {resolve, reject});

      sharedWorker.postMessage({
        type: 'htmlToMarkdown',
        id,
        content: html
      });
    });
  }, []);

  return {
    markdownToHtml,
    htmlToMarkdown,
    ready,
    error
  };
}

export default useMarkdownWorker;
