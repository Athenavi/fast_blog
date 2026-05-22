'use client';

import React, {useMemo} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {
  TrendingUp, Eye, Users, FileText, MessageSquare, UserPlus,
  Clock, Globe, Monitor, Smartphone, Tablet, ChevronUp, ChevronDown,
  Activity, Zap, ExternalLink,
} from 'lucide-react';

// ─── Helpers ──────────────────────────────────────────
const fmt = (n: number | string | undefined | null) => {
  if (n === null || n === undefined) return '—';
  if (typeof n === 'string') return n;
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);
};

const pct = (n: number | undefined | null) => (n !== null && n !== undefined ? `${n}%` : '—');

// ─── Sub-Components ───────────────────────────────────
const StatCard: React.FC<{icon: any; label: string; value: any; change?: number; color?: string}> = ({icon: Icon, label, value, change, color}) => (
  <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm text-gray-500">{label}</span>
      <Icon className={`w-5 h-5 ${color || 'text-gray-400'}`} />
    </div>
    <p className="text-2xl font-bold text-gray-900 dark:text-white">{fmt(value)}</p>
    {change !== undefined && (
      <p className={`text-xs mt-1 flex items-center gap-0.5 ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
        {change >= 0 ? <ChevronUp className="w-3 h-3"/> : <ChevronDown className="w-3 h-3"/>}
        {Math.abs(change).toFixed(1)}%
      </p>
    )}
  </div>
);

const SectionTitle: React.FC<{icon: any; title: string; subtitle?: string}> = ({icon: Icon, title, subtitle}) => (
  <div className="flex items-center gap-2 mb-5">
    <Icon className="w-5 h-5 text-gray-400" />
    <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
    {subtitle && <span className="text-xs text-gray-400">{subtitle}</span>}
  </div>
);

// ─── SVG Bar Chart ────────────────────────────────────
const TrendChart: React.FC<{data: {date: string; views: number; visitors: number}[]}> = ({data}) => {
  if (!data?.length) return <div className="py-8 text-center text-sm text-gray-400">暂无趋势数据</div>;

  const maxVal = Math.max(...data.map(d => Math.max(d.views, d.visitors)), 1);
  const labels = data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 5)) === 0);
  const w = 600;
  const barW = Math.max(4, (w / data.length) - 1);
  const h = 180;

  return (
    <svg viewBox={`0 0 ${w} ${h + 24}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((r, i) => (
        <g key={i}>
          <line x1={0} y1={h * (1 - r)} x2={w} y2={h * (1 - r)} stroke="#e5e7eb" strokeWidth={0.5}/>
          <text x={-4} y={h * (1 - r) + 3} textAnchor="end" className="text-[8px]" fill="#9ca3af">{Math.round(maxVal * r)}</text>
        </g>
      ))}
      {/* Bars: views (blue) */}
      {data.map((d, i) => (
        <rect key={`v${i}`} x={i * (barW + 1)} y={h * (1 - d.views / maxVal)} width={barW * 0.45} height={h * (d.views / maxVal)} fill="#339af0" opacity={0.8} rx={1}/>
      ))}
      {/* Bars: visitors (green) */}
      {data.map((d, i) => (
        <rect key={`u${i}`} x={i * (barW + 1) + barW * 0.5} y={h * (1 - d.visitors / maxVal)} width={barW * 0.45} height={h * (d.visitors / maxVal)} fill="#51cf66" opacity={0.8} rx={1}/>
      ))}
      {/* X labels */}
      {labels.map((d, i) => {
        const idx = data.indexOf(d);
        return <text key={i} x={idx * (barW + 1) + barW / 2} y={h + 14} textAnchor="middle" className="text-[7px]" fill="#9ca3af">
          {d.date.slice(5)}
        </text>;
      })}
    </svg>
  );
};

// ─── Bar (horizontal) ─────────────────────────────────
const HBar: React.FC<{items: {name: string; value: number; pct: number}[]; color?: string}> = ({items, color = '#339af0'}) => (
  <div className="space-y-2.5">
    {items.slice(0, 8).map((item, i) => (
      <div key={i}>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-700 dark:text-gray-300 truncate">{item.name}</span>
          <span className="text-gray-500 shrink-0 ml-2">{item.value} ({item.pct.toFixed(0)}%)</span>
        </div>
        <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-500" style={{width: `${item.pct}%`, backgroundColor: color}} />
        </div>
      </div>
    ))}
    {!items.length && <p className="text-sm text-gray-400 text-center py-4">暂无数据</p>}
  </div>
);

// ─── Main Component ───────────────────────────────────
function AnalyticsInner() {
  const days = 30;

  // ── queries ──
  const {data: overview} = useQuery({
    queryKey: ['analytics-overview', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/overview', {days});
      return res.success && res.data ? res.data : {};
    },
  });
  const {data: trend} = useQuery({
    queryKey: ['analytics-trend', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/article-views-trend', {days});
      return res.success && res.data ? res.data : [];
    },
  });
  const {data: popular} = useQuery({
    queryKey: ['analytics-popular', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/popular-articles', {limit: 10, days});
      return res.success && res.data ? res.data : [];
    },
  });
  const {data: categories} = useQuery({
    queryKey: ['analytics-categories'],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/category-distribution');
      return res.success && res.data ? res.data : [];
    },
  });
  const {data: activity} = useQuery({
    queryKey: ['analytics-activity', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/user-activity', {days});
      return res.success && res.data ? res.data : {};
    },
  });
  const {data: trafficSources} = useQuery({
    queryKey: ['analytics-traffic', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/traffic-sources', {days});
      return res.success && res.data ? res.data : [];
    },
  });
  const {data: deviceStats} = useQuery({
    queryKey: ['analytics-devices', days],
    queryFn: async () => {
      const res = await apiClient.get<any>('/dashboard/analytics/device-stats', {days});
      return res.success && res.data ? res.data : [];
    },
  });

  // ── category distribution → HBar ──
  const catItems = useMemo(() => {
    if (!Array.isArray(categories)) return [];
    const total = categories.reduce((s: number, c: any) => s + (c.value || c.count || 0), 0) || 1;
    return categories.map((c: any) => ({
      name: c.name || c.category_name || '未知',
      value: c.value || c.count || 0,
      pct: ((c.value || c.count || 0) / total) * 100,
    }));
  }, [categories]);

  // ── traffic sources → HBar ──
  const trafficItems = useMemo(() => {
    if (!Array.isArray(trafficSources)) return [];
    const total = trafficSources.reduce((s: number, t: any) => s + (t.count || t.visits || 0), 0) || 1;
    return trafficSources.map((t: any) => ({
      name: t.source || t.name || '未知',
      value: t.count || t.visits || 0,
      pct: ((t.count || t.visits || 0) / total) * 100,
    }));
  }, [trafficSources]);

  // ── device → items ──
  const deviceItems = useMemo(() => {
    if (!Array.isArray(deviceStats)) return [];
    const total = deviceStats.reduce((s: number, d: any) => s + (d.count || d.visits || 0), 0) || 1;
    return deviceStats.map((d: any) => ({
      name: d.device || d.device_type || '未知',
      value: d.count || d.visits || 0,
      pct: ((d.count || d.visits || 0) / total) * 100,
      icon: (d.device || '').toLowerCase().includes('mobile') || (d.device || '').toLowerCase().includes('phone') ? Smartphone
        : (d.device || '').toLowerCase().includes('tablet') ? Tablet : Monitor,
    }));
  }, [deviceStats]);

  const trendData = Array.isArray(trend) ? trend : [];

  return (
    <AdminShell title="数据分析">
      {/* ═══ 1. Stat Cards ═══ */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard icon={Eye} label="总浏览量" value={overview?.total_views} color="text-blue-500" />
        <StatCard icon={Users} label="独立访客" value={overview?.unique_visitors} color="text-green-500" />
        <StatCard icon={FileText} label="文章总数" value={overview?.total_articles} change={overview?.page_views_change} color="text-purple-500" />
        <StatCard icon={MessageSquare} label="评论总数" value={overview?.total_comments} color="text-orange-500" />
        <StatCard icon={UserPlus} label="新增用户" value={overview?.new_users || overview?.total_users} color="text-teal-500" />
        <StatCard icon={Clock} label="跳出率" value={pct(overview?.bounce_rate)} color="text-red-500" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        {/* ═══ 2. Trend Chart ═══ */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={TrendingUp} title="30天浏览趋势" subtitle="蓝色=浏览量 绿色=访客" />
          <TrendChart data={trendData} />
        </div>

        {/* ═══ 3. User Activity ═══ */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={Activity} title="用户活跃度" />
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800">
              <span className="text-sm text-gray-600 dark:text-gray-400">活跃作者</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">{fmt(activity?.active_authors)}</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800">
              <span className="text-sm text-gray-600 dark:text-gray-400">活跃评论者</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">{fmt(activity?.active_commenters)}</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800">
              <span className="text-sm text-gray-600 dark:text-gray-400">新增文章</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">{fmt(overview?.new_articles)}</span>
            </div>
            <div className="flex items-center justify-between py-3">
              <span className="text-sm text-gray-600 dark:text-gray-400">新注册用户</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">{fmt(activity?.new_users || overview?.new_users)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* ═══ 4. Popular Articles ═══ */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={Zap} title="热门文章" subtitle={`近${days}天`} />
          {Array.isArray(popular) && popular.length > 0 ? (
            <div className="space-y-1">
              {popular.map((a: any, i: number) => (
                <div key={a.id || i} className="flex items-center gap-3 py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                    ${i === 0 ? 'bg-yellow-100 text-yellow-700' : i === 1 ? 'bg-gray-200 text-gray-600 dark:bg-gray-700' : i === 2 ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-500 dark:bg-gray-800'}`}>
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{a.title || '无标题'}</p>
                    <p className="text-xs text-gray-400">{fmt(a.views)} 次浏览 · {a.comments || 0} 评论</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-gray-400">暂无热门文章数据</div>
          )}
        </div>

        {/* ═══ 5. Category Distribution ═══ */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={FileText} title="分类分布" />
          <HBar items={catItems} color="#8b5cf6" />
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* ═══ 6. Traffic Sources ═══ */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={Globe} title="流量来源" />
          <HBar items={trafficItems} color="#339af0" />
        </div>

        {/* ═══ 7. Device Distribution ═══ */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
          <SectionTitle icon={Monitor} title="设备分布" />
          <div className="space-y-4">
            {deviceItems.map((d, i) => {
              const Icon = d.icon;
              return (
                <div key={i}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="flex items-center gap-2 text-gray-700 dark:text-gray-300"><Icon className="w-4 h-4 text-gray-400"/>{d.name}</span>
                    <span className="text-gray-500">{d.value} ({d.pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full h-2.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{width: `${d.pct}%`, backgroundColor: i === 0 ? '#339af0' : i === 1 ? '#51cf66' : '#f59f00'}} />
                  </div>
                </div>
              );
            })}
            {!deviceItems.length && <p className="text-sm text-gray-400 text-center py-4">暂无设备数据</p>}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

export default function AdminAnalytics() {
  return <AuthGuard><QueryProvider><AnalyticsInner /></QueryProvider></AuthGuard>;
}
