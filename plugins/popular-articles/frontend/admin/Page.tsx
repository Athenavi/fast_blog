import React, {useState, useEffect} from 'react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';

/**
 * Popular Articles — 阅读排行管理页面
 */
export default function PopularArticlesPage() {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [maxItems, setMaxItems] = useState(5);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v2/plugins/popular-articles/action`, {
      method: 'POST',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        action: 'get_popular',
        params: {max_items: maxItems, days}
      }),
    })
      .then(r => r.json())
      .then(res => {
        setArticles(res.data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [maxItems, days]);

  return (
    <AuthGuard>
      <QueryProvider>
        <AdminShell title="🔥 阅读排行">
          <div className="space-y-6 p-6">
            <div className="flex gap-4 items-center">
              <label className="text-sm">显示数量:
                <select value={maxItems} onChange={e => setMaxItems(Number(e.target.value))}
                        className="ml-2 border rounded px-2 py-1 text-sm">
                  {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
              <label className="text-sm">统计天数:
                <select value={days} onChange={e => setDays(Number(e.target.value))}
                        className="ml-2 border rounded px-2 py-1 text-sm">
                  {[7, 14, 30, 90].map(n => <option key={n} value={n}>{n}天</option>)}
                </select>
              </label>
            </div>

            {loading ? (
              <div className="animate-pulse space-y-3">
                {Array.from({length: 5}).map((_, i) => (
                  <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"/>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {articles.map((a: any, i: number) => (
                  <div key={a.id}
                       className="flex items-center gap-4 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <span className="text-lg font-bold text-gray-400 w-8 text-center">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{a.title}</p>
                      <p className="text-xs text-gray-400">{a.views} 次浏览</p>
                    </div>
                    <a href={`/article/${a.slug || a.id}`} target="_blank"
                       className="text-blue-500 hover:underline text-sm whitespace-nowrap">查看</a>
                  </div>
                ))}
                {articles.length === 0 && (
                  <p className="text-gray-400 text-center py-8">暂无数据</p>
                )}
              </div>
            )}
          </div>
        </AdminShell>
      </QueryProvider>
    </AuthGuard>
  );
}
