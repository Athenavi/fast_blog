'use client';

import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {BarChart3, Shield, Ticket, Terminal, ScrollText, Bell, Loader2} from 'lucide-react';

const BASE = '/enterprise/admin';

const TABS = [
  {key: 'overview', label: '概览', icon: BarChart3},
  {key: 'licenses', label: '许可证', icon: Shield},
  {key: 'tickets', label: '工单', icon: Ticket},
  {key: 'scripts', label: '部署脚本', icon: Terminal},
  {key: 'logs', label: '部署日志', icon: ScrollText},
  {key: 'alerts', label: '告警', icon: Bell},
];

export default function EnterprisePage() {
  const [tab, setTab] = useState('overview');
  const [page, setPage] = useState(1);

  // 概览
  const {data: overview} = useQuery({
    queryKey: ['enterprise-overview'],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/overview`); return r.data || {}; },
    enabled: tab === 'overview',
  });

  // 许可证
  const {data: licenses, isLoading: loadLic} = useQuery({
    queryKey: ['enterprise-licenses', page],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/licenses`, {page, per_page: 20}); return r.data || {items: [], total: 0}; },
    enabled: tab === 'licenses',
  });

  // 工单
  const {data: tickets, isLoading: loadTickets} = useQuery({
    queryKey: ['enterprise-tickets', page],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/tickets`, {page, per_page: 20}); return r.data || {items: [], total: 0}; },
    enabled: tab === 'tickets',
  });

  // 脚本
  const {data: scripts, isLoading: loadScripts} = useQuery({
    queryKey: ['enterprise-scripts', page],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/scripts`, {page, per_page: 20}); return r.data || {items: [], total: 0}; },
    enabled: tab === 'scripts',
  });

  // 日志
  const {data: logs, isLoading: loadLogs} = useQuery({
    queryKey: ['enterprise-logs', page],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/logs`, {page, per_page: 20}); return r.data || {items: [], total: 0}; },
    enabled: tab === 'logs',
  });

  // 告警
  const {data: alerts, isLoading: loadAlerts} = useQuery({
    queryKey: ['enterprise-alerts', page],
    queryFn: async () => { const r = await apiClient.get(`${BASE}/alerts`, {page, per_page: 20}); return r.data || {items: [], total: 0}; },
    enabled: tab === 'alerts',
  });

  const dataMap: Record<string, any> = {overview, licenses, tickets, scripts, logs, alerts};
  const loadingMap: Record<string, boolean> = {licenses: loadLic, tickets: loadTickets, scripts: loadScripts, logs: loadLogs, alerts: loadAlerts};
  const currentData = dataMap[tab];
  const currentLoading = loadingMap[tab] || false;

  const overviewCards = overview ? [
    {label: '总许可证', value: overview.total_licenses ?? '—'},
    {label: '活跃许可证', value: overview.active_licenses ?? '—'},
    {label: '待处理工单', value: overview.open_tickets ?? '—'},
    {label: '进行中工单', value: overview.in_progress_tickets ?? '—'},
    {label: '部署脚本', value: overview.total_scripts ?? '—'},
    {label: '部署次数', value: overview.total_deployments ?? '—'},
    {label: '失败部署', value: overview.failed_deployments ?? '—'},
    {label: '未解决告警', value: overview.unresolved_alerts ?? '—'},
  ] : [];

  return (
    <AdminShell title="企业管理">
      {/* Tab Bar */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {TABS.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); setPage(1); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
              tab === t.key ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-900 border hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}>
            <t.icon className="w-4 h-4"/>{t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'overview' && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {overviewCards.map(c => (
            <div key={c.label} className="bg-white dark:bg-gray-900 rounded-xl border p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{c.label}</p>
              <p className="text-2xl font-bold">{c.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Licenses / Tickets / Scripts / Logs / Alerts — shared table */}
      {tab !== 'overview' && (
        currentLoading ? (
          <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-blue-500"/></div>
        ) : (
          <div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden">
            {(!currentData?.items || currentData.items.length === 0) ? (
              <div className="py-16 text-center text-gray-400">
                <Shield className="w-10 h-10 mx-auto mb-3 opacity-40"/>
                <p className="text-sm">暂无数据</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-800 border-b">
                  <tr>
                    {tab === 'licenses' && <>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">KEY</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">状态</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right">过期</th>
                    </>}
                    {tab === 'tickets' && <>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">标题</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">状态</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right hidden md:table-cell">优先级</th>
                    </>}
                    {tab === 'scripts' && <>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">名称</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right hidden sm:table-cell">版本</th>
                    </>}
                    {tab === 'logs' && <>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">脚本</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">状态</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right">时间</th>
                    </>}
                    {tab === 'alerts' && <>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left">消息</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-left hidden sm:table-cell">级别</th>
                      <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase text-right">时间</th>
                    </>}
                  </tr>
                </thead>
                <tbody className="divide-y dark:divide-gray-800">
                  {currentData.items.map((item: any, i: number) => (
                    <tr key={item.id || i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      {tab === 'licenses' && <>
                        <td className="px-5 py-4 text-sm font-mono text-gray-900 dark:text-white truncate max-w-[200px]">{item.license_key || item.id}</td>
                        <td className="px-5 py-4 text-sm hidden sm:table-cell">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${item.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{item.is_active ? '活跃' : '已停用'}</span>
                        </td>
                        <td className="px-5 py-4 text-sm text-gray-500 text-right">{item.expires_at ? new Date(item.expires_at).toLocaleDateString() : '—'}</td>
                      </>}
                      {tab === 'tickets' && <>
                        <td className="px-5 py-4 text-sm font-medium text-gray-900 dark:text-white">{item.title || `#${item.id}`}</td>
                        <td className="px-5 py-4 text-sm hidden sm:table-cell">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            item.status === 'open' ? 'bg-yellow-100 text-yellow-700' :
                            item.status === 'resolved' ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-500'
                          }`}>{item.status || '—'}</span>
                        </td>
                        <td className="px-5 py-4 text-sm text-gray-500 text-right hidden md:table-cell">{item.priority || '—'}</td>
                      </>}
                      {tab === 'scripts' && <>
                        <td className="px-5 py-4 text-sm font-medium text-gray-900 dark:text-white">{item.name || `#${item.id}`}</td>
                        <td className="px-5 py-4 text-sm text-gray-500 text-right hidden sm:table-cell">{item.version || '1.0'}</td>
                      </>}
                      {tab === 'logs' && <>
                        <td className="px-5 py-4 text-sm text-gray-900 dark:text-white">{item.script_name || `#${item.script_id}`}</td>
                        <td className="px-5 py-4 text-sm hidden sm:table-cell">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${item.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{item.status || '—'}</span>
                        </td>
                        <td className="px-5 py-4 text-sm text-gray-500 text-right">{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td>
                      </>}
                      {tab === 'alerts' && <>
                        <td className="px-5 py-4 text-sm text-gray-900 dark:text-white truncate max-w-xs">{item.message || `#${item.id}`}</td>
                        <td className="px-5 py-4 text-sm hidden sm:table-cell">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${item.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{item.severity || 'info'}</span>
                        </td>
                        <td className="px-5 py-4 text-sm text-gray-500 text-right">{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td>
                      </>}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )
      )}
    </AdminShell>
  );
}
