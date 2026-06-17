import { useState, useEffect, useRef } from 'react';
import { getAccessTokenFromCookie } from '@/lib/auth-utils';

interface UseFileBlobResult {
  blob: Blob | null;
  loading: boolean;
  error: string | null;
  sizeExceeded: boolean;
}

/** 超过此大小的文件不通过 Blob 下载（浏览器内存限制），改走 URL+token */
const MAX_BLOB_SIZE = 200 * 1024 * 1024; // 200MB

/**
 * 带 Auth 的文件 Blob 获取 Hook
 *
 * FileViewer iframe 内部的 Vue 应用不会自动携带 cookie，
 * 需要前端先 fetch 文件内容（带 Authorization header），再以 Blob 形式传入。
 *
 * 超过 MAX_BLOB_SIZE 的文件返回 sizeExceeded=true，
 * 调用方应改用 getAuthenticatedMediaUrl 传递带 token 的 URL。
 */
export function useFileBlob(url: string | null | undefined, name?: string): UseFileBlobResult {
  const [blob, setBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sizeExceeded, setSizeExceeded] = useState(false);
  const lastUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!url) {
      setBlob(null);
      setError(null);
      setSizeExceeded(false);
      setLoading(false);
      return;
    }

    // URL 没变则不重复请求
    if (url === lastUrlRef.current) return;
    lastUrlRef.current = url;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setBlob(null);
    setSizeExceeded(false);

    const token = getAccessTokenFromCookie();

    const controller = new AbortController();

    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`加载文件异常：Request failed with status code ${res.status}`);
        }

        // 检查 Content-Length，超出限制则不下载 body
        const contentLength = res.headers.get('Content-Length');
        if (contentLength && parseInt(contentLength, 10) > MAX_BLOB_SIZE) {
          if (!cancelled) {
            controller.abort();
            setSizeExceeded(true);
            setLoading(false);
          }
          return;
        }

        return res.blob();
      })
      .then((data) => {
        if (!cancelled && data) {
          setBlob(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled && err.name !== 'AbortError') {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; controller.abort(); };
  }, [url]);

  return { blob, loading, error, sizeExceeded };
}
