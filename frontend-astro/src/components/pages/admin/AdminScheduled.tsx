'use client';

import React, {useMemo, useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {
  ChevronLeft, ChevronRight, Calendar, Clock, X, Send, List, Grid3X3,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────
interface ScheduledArticle {
  id: number; title?: string; scheduled_at?: string;
  created_at?: string; slug?: string; status?: number;
}

// ─── Calendar helpers ─────────────────────────────────
function getMonthDays(year: number, month: number): (number | null)[][] {
  const first = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const weeks: (number | null)[][] = [];
  let week: (number | null)[] = new Array(first).fill(null);
  for (let d = 1; d <= daysInMonth; d++) {
    week.push(d);
    if (week.length === 7) { weeks.push(week); week = []; }
  }
  if (week.length > 0) { while (week.length < 7) week.push(null); weeks.push(week); }
  return weeks;
}

const MONTHS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
const DAYS = ['日','一','二','三','四','五','六'];

// ─── Component ────────────────────────────────────────
function CalendarInner() {
  const toast = useToast();
  const qc = useQueryClient();
  const today = new Date();
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');
  const [curYear, setCurYear] = useState(today.getFullYear());
  const [curMonth, setCurMonth] = useState(today.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const {data, isLoading} = useQuery({
    queryKey: ['scheduled-articles-calendar'],
    queryFn: async () => {
      const res = await apiClient.get('/articles/scheduler/list', {page: 1, per_page: 200});
      return (res.data?.articles || []) as ScheduledArticle[];
    },
  });
  const articles = data || [];

  const cancelMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/articles/scheduler/cancel/${id}`),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['scheduled-articles-calendar']}); toast.success('已取消'); },
    onError: () => toast.error('取消失败'),
  });

  // Group articles by date
  const articlesByDate = useMemo(() => {
    const map: Record<string, ScheduledArticle[]> = {};
    for (const a of articles) {
      if (!a.scheduled_at) continue;
      const key = a.scheduled_at.slice(0, 10); // YYYY-MM-DD
      if (!map[key]) map[key] = [];
      map[key].push(a);
    }
    return map;
  }, [articles]);

  const weeks = useMemo(() => getMonthDays(curYear, curMonth), [curYear, curMonth]);

  // Articles for selected day
  const selectedArticles = useMemo(() => {
    if (selectedDay === null) return [];
    const key = `${curYear}-${String(curMonth + 1).padStart(2, '0')}-${String(selectedDay).padStart(2, '0')}`;
    return articlesByDate[key] || [];
  }, [selectedDay, curYear, curMonth, articlesByDate]);

  const prevMonth = () => { if (curMonth === 0) { setCurYear(y => y - 1); setCurMonth(11); } else setCurMonth(m => m - 1); setSelectedDay(null); };
  const nextMonth = () => { if (curMonth === 11) { setCurYear(y => y + 1); setCurMonth(0); } else setCurMonth(m => m + 1); setSelectedDay(null); };

  return (
    <AdminShell title="内容日历" actions={
      <div className="flex items-center gap-2">
        <div className="flex bg-gray-100 dark:bg-gray-800 p-0.5 rounded-xl">
          <button onClick={() => setViewMode('calendar')}
                  className={`p-2 rounded-lg transition-all ${viewMode === 'calendar' ? 'bg-white dark:bg-gray-700 shadow-sm' : ''}`}>
            <Grid3X3 className="w-4 h-4"/></button>
          <button onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white dark:bg-gray-700 shadow-sm' : ''}`}>
            <List className="w-4 h-4"/></button>
        </div>
        <button onClick={() => apiClient.post('/articles/scheduler/publish-due').then(() => { qc.invalidateQueries({queryKey: ['scheduled-articles-calendar']}); toast.success('已发布到期文章'); })}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/25">
          <Send className="w-4 h-4"/>发布到期
        </button>
      </div>
    }>
      {viewMode === 'calendar' ? (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="xl:col-span-2 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
              <button onClick={prevMonth} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
                <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400"/>
              </button>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{curYear}年 {MONTHS[curMonth]}</h3>
              <button onClick={nextMonth} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
                <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400"/>
              </button>
            </div>

            {/* Day headers */}
            <div className="grid grid-cols-7 border-b border-gray-100 dark:border-gray-800">
              {DAYS.map(d => (
                <div key={d} className="py-2 text-center text-xs font-medium text-gray-500">{d}</div>
              ))}
            </div>

            {/* Calendar grid */}
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {weeks.map((week, wi) => (
                <div key={wi} className="grid grid-cols-7">
                  {week.map((day, di) => {
                    if (day === null) return <div key={`e-${di}`} className="min-h-[80px] bg-gray-50/50 dark:bg-gray-800/20"/>;
                    const key = `${curYear}-${String(curMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    const dayArticles = articlesByDate[key] || [];
                    const isToday = day === today.getDate() && curMonth === today.getMonth() && curYear === today.getFullYear();
                    const isSelected = day === selectedDay;
                    return (
                      <button key={day} onClick={() => setSelectedDay(isSelected ? null : day)}
                              className={`min-h-[80px] p-1.5 border-r border-gray-100 dark:border-gray-800 last:border-r-0 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors text-left relative ${
                                isSelected ? 'bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500 ring-inset' : ''
                              }`}>
                        <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm ${
                          isToday ? 'bg-blue-600 text-white font-bold' : 'text-gray-700 dark:text-gray-300'
                        }`}>{day}</span>
                        {dayArticles.length > 0 && (
                          <div className="mt-1 space-y-0.5">
                            {dayArticles.slice(0, 3).map(a => (
                              <div key={a.id} className="flex items-center gap-1 px-1 py-0.5 bg-blue-100 dark:bg-blue-900/30 rounded">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"/>
                                <span className="text-[10px] text-blue-700 dark:text-blue-300 truncate">{a.title || `#${a.id}`}</span>
                              </div>
                            ))}
                            {dayArticles.length > 3 && (
                              <p className="text-[10px] text-gray-400 pl-1">+{dayArticles.length - 3} 更多</p>
                            )}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* Selected day detail */}
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {selectedDay ? `${curYear}年${curMonth + 1}月${selectedDay}日` : '选择日期'}
              </h3>
              <p className="text-xs text-gray-500">{selectedArticles.length} 篇文章</p>
            </div>
            <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto">
              {selectedDay === null ? (
                <p className="text-center py-8 text-sm text-gray-400">点击日历中的日期查看详情</p>
              ) : selectedArticles.length === 0 ? (
                <p className="text-center py-8 text-sm text-gray-400">该日无已排期文章</p>
              ) : (
                selectedArticles.map(a => (
                  <div key={a.id} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{a.title || `文章 #${a.id}`}</p>
                        <p className="text-[10px] text-gray-400 mt-0.5">ID: {a.id} · 状态: {a.status ?? '—'}</p>
                      </div>
                      <button onClick={() => cancelMut.mutate(a.id)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors shrink-0">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Stats */}
            <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>本月已排期</span>
                <span className="font-semibold text-gray-900 dark:text-white">{articles.length} 篇</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* List view (same as before) */
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {isLoading ? (
            <div className="space-y-3 p-6">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
          ) : articles.length === 0 ? (
            <div className="text-center py-20 text-gray-400">
              <Clock className="w-12 h-12 mx-auto mb-4 opacity-50"/>
              <p className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-1">暂无排期文章</p>
              <p className="text-sm">在文章编辑器中设置定时发布</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800 text-xs text-gray-500 uppercase">
                  <th className="text-left px-4 py-3 font-medium">标题</th>
                  <th className="text-left px-4 py-3 font-medium">排期时间</th>
                  <th className="text-right px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {articles.map((a: ScheduledArticle) => (
                  <tr key={a.id} className="border-b border-gray-100 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{a.title || `文章 #${a.id}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5"/>
                      {a.scheduled_at ? new Date(a.scheduled_at).toLocaleString('zh-CN') : '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => cancelMut.mutate(a.id)}
                              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-red-200 dark:border-red-800 text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                        <X className="w-3 h-3"/>取消
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminScheduled() {
  return (
    <AuthGuard>
      <QueryProvider>
        <CalendarInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
