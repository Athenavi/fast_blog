'use client';

import React from 'react';

// ─── Result Visualizer ─────────────────────────

interface ToolResultVisualizerProps {
  name: string;
  result: string; // raw JSON string from backend
}

/** 智能工具结果渲染：根据工具名自动选择合适的可视化方式 */
export default function ToolResultVisualizer({name, result}: ToolResultVisualizerProps) {
  let data: any;
  try {
    data = typeof result === 'string' ? JSON.parse(result) : result;
  } catch {
    return <pre className="text-[11px] bg-white/60 dark:bg-black/20 rounded-lg p-2.5 overflow-x-auto text-gray-600 dark:text-gray-400 font-mono leading-relaxed max-h-40 overflow-y-auto border border-black/5 dark:border-white/5">{result}</pre>;
  }

  // ── null/undefined ──
  if (data === null || data === undefined) {
    return <div className="text-xs text-gray-400 italic py-1">无数据</div>;
  }

  // ── List tools (list_*, search_*) → 表格 ──
  if (name.startsWith('list_') || name.startsWith('search_')) {
    return <ListResult data={data} />;
  }

  // ── Create/Update/Delete → 成功消息 ──
  if (name.startsWith('create_') || name.startsWith('update_') || name.startsWith('delete_')) {
    return <MutationResult name={name} data={data} />;
  }

  // ── Stats/Analytics → 统计卡片 ──
  if (name.includes('stats') || name.includes('analytics') || name.includes('statistics')) {
    return <StatsResult data={data} />;
  }

  // ── System info / status → 信息展示 ──
  if (name.includes('system_info') || name.includes('maintenance') || name.includes('cache_status')) {
    return <InfoResult data={data} />;
  }

  // ── Fallback: 格式化 JSON ──
  return (
    <pre className="text-[11px] bg-white/60 dark:bg-black/20 rounded-lg p-2.5 overflow-x-auto text-gray-600 dark:text-gray-400 font-mono leading-relaxed max-h-60 overflow-y-auto border border-black/5 dark:border-white/5">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}


// ═══════════════════════════════════════════════
// 子组件
// ═══════════════════════════════════════════════

/** 列表结果 → 表格 */
function ListResult({data}: {data: any}) {
  // 解包嵌套结构: {articles: [...], users: [...], data: [...]} 或直接数组
  const items: any[] = data?.data || data?.articles || data?.users || data?.results || data?.items || (Array.isArray(data) ? data : Object.values(data).find(Array.isArray) || []);
  if (!Array.isArray(items) || items.length === 0) {
    return <div className="text-xs text-gray-400 italic py-1">空列表</div>;
  }

  // 提取列名（取第一条的非空字段）
  const sampleKeys = Object.keys(items[0] || {}).filter(k => !k.startsWith('_'));
  const columns = sampleKeys.slice(0, 8); // 最多8列

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="bg-gray-100 dark:bg-gray-800">
            {columns.map(col => (
              <th key={col} className="px-2 py-1.5 text-left font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                {col}
              </th>
            ))}
            {items.length > 8 && <th className="px-2 py-1.5 text-right text-gray-400">共{items.length}条</th>}
          </tr>
        </thead>
        <tbody>
          {items.slice(0, 20).map((item, i) => (
            <tr key={i} className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
              {columns.map(col => (
                <td key={col} className="px-2 py-1.5 text-gray-600 dark:text-gray-400 truncate max-w-[150px]" title={String(item[col] ?? '')}>
                  {formatCell(item[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {items.length > 20 && (
        <div className="text-[10px] text-gray-400 text-center py-1 border-t border-gray-100 dark:border-gray-800">
          显示前 20 条，共 {items.length} 条
        </div>
      )}
    </div>
  );
}

/** 创建/更新/删除 → 成功徽章 + 摘要 */
function MutationResult({name, data}: {name: string; data: any}) {
  const action = name.startsWith('create_') ? '创建' : name.startsWith('update_') ? '更新' : '删除';
  const resource = name.replace(/^(create_|update_|delete_)/, '');
  const id = data?.id || data?.data?.id || data?.article_id || data?.user_id;

  return (
    <div className="flex items-center gap-2 py-1">
      <span className="text-sm">{action === '删除' ? '🗑️' : '✅'}</span>
      <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
        {resource} {action}成功
      </span>
      {id && <span className="text-[10px] text-gray-400 font-mono">(ID: {id})</span>}
    </div>
  );
}

/** 统计数据 → 卡片网格 */
function StatsResult({data}: {data: any}) {
  // 展平嵌套: {data: {articles: 10, users: 5}} → {articles: 10, users: 5}
  const flat = data?.data || data;
  const entries = Object.entries(flat).filter(([k, v]) => typeof v === 'number' || typeof v === 'string') || [];

  return (
    <div className="grid grid-cols-2 gap-1.5">
      {entries.slice(0, 12).map(([key, val]) => (
        <div key={key} className="bg-white/50 dark:bg-black/20 rounded-lg px-2.5 py-2 border border-gray-100 dark:border-gray-800">
          <div className="text-[10px] text-gray-400 dark:text-gray-500 truncate">{key.replace(/_/g, ' ')}</div>
          <div className="text-sm font-bold text-gray-800 dark:text-gray-200 tabular-nums">{formatCell(val)}</div>
        </div>
      ))}
    </div>
  );
}

/** 系统信息 → 键值对 */
function InfoResult({data}: {data: any}) {
  const flat = data?.data || data;
  const entries = Object.entries(flat).filter(([k]) => !k.startsWith('_')) || [];

  return (
    <div className="space-y-0.5">
      {entries.slice(0, 15).map(([key, val]) => (
        <div key={key} className="flex items-center gap-2 text-[11px]">
          <span className="text-gray-400 dark:text-gray-500 font-mono min-w-[80px] truncate">{key}:</span>
          <span className="text-gray-700 dark:text-gray-300 truncate">{formatCell(val)}</span>
        </div>
      ))}
    </div>
  );
}


// ═══════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════

function formatCell(val: any): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? '是' : '否';
  if (typeof val === 'object') return JSON.stringify(val).slice(0, 60);
  return String(val);
}
