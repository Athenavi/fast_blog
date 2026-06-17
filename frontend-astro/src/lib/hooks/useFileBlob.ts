import { useState, useEffect, useRef } from 'react';
import { getAccessTokenFromCookie } from '@/lib/auth-utils';

interface UseFileBlobResult {
  blob: Blob | null;
  loading: boolean;
  error: string | null;
}

/**
 * 带 Auth 的文件 Blob 获取 Hook
 *
 * FileViewer iframe 内部的 Vue 应用不会自动携带 cookie，
 * 需要前端先 fetch 文件内容（带 Authorization header），再以 Blob 形式传入。
 */
export function useFileBlob(url: string | null | undefined, name?: string): UseFileBlobResult {
  const [blob, setBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!url) {
      setBlob(null);
      setError(null);
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

    const token = getAccessTokenFromCookie();

    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`加载文件异常：Request failed with status code ${res.status}`);
        }
        return res.blob();
      })
      .then((data) => {
        if (!cancelled) {
          setBlob(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [url]);

  return { blob, loading, error };
}
