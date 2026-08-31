import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Flame, Loader2} from 'lucide-react';

const PLUGIN_SLUG = 'popular-articles';

function call(action: string, params: any = {}) {
  return apiClient.post(`/plugins/${PLUGIN_SLUG}/action`, {action, params});
}

/**
 * Popular Articles — 阅读排行管理页面
 */
function PopularRanking() {
  const [maxItems, setMaxItems] = useState(5);
  const [days, setDays] = useState(30);

  const {data: articles = [], isLoading} = useQuery({
    queryKey: ['popular-articles', maxItems, days],
    queryFn: async () => {
      const r = await call('get_popular', {max_items: maxItems, days});
      return r.data || [];
    },
    placeholderData: (prev: any) => prev || [],
  });

  return (
    <AdminShell title="阅读排行" actions={
      <div className="flex items-center gap-4 text-sm">
        <label className="flex items-center gap-1.5 text-gray-500">
          <span>显示</span>
          <select value={maxItems} onChange={e => setMaxItems(Number(e.target.value))}
                  className="border rounded-lg px-2 py-1 text-xs bg-white dark:bg-gray-800">
            {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-gray-500">
          <span>近</span>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
                  className="border rounded-lg px-2 py-1 text-xs bg-white dark:bg-gray-800">
            {[7, 14, 30, 90].map(n => <option key={n} value={n}>{n}天</option>)}
          </select>
        </label>
      </div>
    }>
      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-blue-500"/></div>
      ) : articles.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Flame className="w-12 h-12 mx-auto mb-4 opacity-50"/>
          <p className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-1">暂无热门文章</p>
          <p className="text-sm">文章需要有一定的浏览量才会出现在这里</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
          <div className="divide-y dark:divide-gray-800">
            {articles.map((a: any, i: number) => (
              <div key={a.id}
                   className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                <span className={`w-8 h-8 flex items-center justify-center rounded-full text-sm font-bold ${
                  i === 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                    i === 1 ? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' :
                      i === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                        'text-gray-400'
                }`}>{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{a.title || `#${a.id}`}</p>
                  <p className="text-xs text-gray-400">{a.views ?? 0} 次浏览</p>
                </div>
                <a href={`/article/${a.slug || a.id}`} target="_blank" rel="noopener noreferrer"
                   className="px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors whitespace-nowrap">
                  查看
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </AdminShell>
  );
}

export default function PopularArticlesPage() {
  return <AuthGuard><QueryProvider><PopularRanking/></QueryProvider></AuthGuard>;
}
