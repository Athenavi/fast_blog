'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {PermissionGuard} from '@/components/admin/PermissionGuard';
import {apiClient} from '@/lib/api/base-client';
import {SYSTEM} from '@/lib/api/api-paths';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Database,
  Download,
  FileCode,
  Loader,
  RotateCcw,
  Server,
  Shield,
  Upload,
  XCircle,
} from 'lucide-react';

// ─── helpers ───────────────────────────────────
const statusIcon = (ok: boolean) =>
  ok ? <CheckCircle2 className="w-4 h-4 text-green-500"/> :
    <XCircle className="w-4 h-4 text-red-500"/>;

const statusBadge = (ok: boolean, label?: string) => {
  const cls = ok
    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
  return <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${cls}`}>{label || (ok ? '正常' : '异常')}</span>;
};

// ─── Zone 1: Version & Status ──────────────────
function VersionStatusCard() {
  const {data: ver, isLoading: verLoading} = useQuery({
    queryKey: ['system-version'],
    queryFn: async () => {
      const r = await apiClient.get(SYSTEM.VERSION_FULL);
      return r.success ? r.data : {};
    },
  });
  const {data: health, isLoading: healthLoading} = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const r = await apiClient.get(SYSTEM.HEALTH);
      return r.success ? r.data : {};
    },
  });
  const {data: info} = useQuery({
    queryKey: ['system-info'],
    queryFn: async () => {
      const r = await apiClient.get(SYSTEM.INFO);
      return r.success ? r.data : {};
    },
  });

  const score = health?.overall_score ?? null;
  const status = health?.status ?? null;
  const dbStatus = health?.checks?.database ?? null;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 space-y-5">
      <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <Server className="w-5 h-5"/>版本与运行状态
      </h3>

      {verLoading ? (
        <div className="h-20 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl"/>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InfoBox label="后端版本" value={ver?.version || '—'} icon={FileCode}/>
          <InfoBox label="构建时间" value={ver?.build_time?.slice(0, 10) || '—'} icon={Activity}/>
          <InfoBox label="数据库迁移" value={ver?.migration?.slice(0, 12) || '—'} icon={Database}/>
          <InfoBox label="迁移状态" value={ver?.migration_status || '—'} icon={Shield}/>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-gray-100 dark:border-gray-800">
        {/* Health score */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">健康评分:</span>
          {healthLoading ? (
            <Loader className="w-4 h-4 animate-spin text-gray-400"/>
          ) : score !== null ? (
            <span className={`text-lg font-bold ${score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
              {score}/100
            </span>
          ) : <span className="text-sm text-gray-400">—</span>}
        </div>

        {/* DB status */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">数据库:</span>
          {dbStatus ? (
            <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
              dbStatus.status === 'pass' || dbStatus.status === 'good'
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
            }`}>
              {dbStatus.status === 'pass' || dbStatus.status === 'good' ? '连接正常' : '异常'}
            </span>
          ) : <span className="text-sm text-gray-400">—</span>}
        </div>

        {status && statusBadge(status !== 'fail' && status !== 'critical', status.toUpperCase())}

        {/* Env */}
        <span className="text-xs text-gray-400 ml-auto">
          {info?.python_version} · {info?.environment || '—'}
        </span>
      </div>
    </div>
  );
}

const InfoBox: React.FC<{ label: string; value: string; icon: React.FC<{ className?: string }> }> = ({
  label, value, icon: Icon,
}) => (
  <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50">
    <div className="flex items-center gap-1.5 mb-1">
      <Icon className="w-3.5 h-3.5 text-gray-400"/>
      <span className="text-[10px] text-gray-500 dark:text-gray-400">{label}</span>
    </div>
    <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{value}</p>
  </div>
);

// ─── Zone 2: Migration Operations ──────────────
function MigrationCard() {
  const qc = useQueryClient();
  const [rollbackSteps, setRollbackSteps] = useState(1);
  const [log, setLog] = useState<string[]>([]);

  const addLog = (msg: string) => setLog(prev => {
    const next = [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`];
    return next.slice(-50); // keep last 50 lines
  });

  // Check status
  const {data: migStatus, isLoading: statusLoading, refetch: refetchStatus} = useQuery({
    queryKey: ['migration-status'],
    queryFn: async () => {
      const r = await apiClient.get(`${SYSTEM.INFO.replace('/info', '')}/migrations/status`);
      return r.success ? r.data : null;
    },
  });

  // Apply migrations
  const applyMut = useMutation({
    mutationFn: async () => {
      addLog('正在执行数据库迁移...');
      const r = await apiClient.post(`${SYSTEM.INFO.replace('/info', '')}/migrations/apply`);
      return r;
    },
    onSuccess: (r: any) => {
      if (r.success) {
        addLog(`✓ 迁移完成: 已应用 ${r.data?.applied_count || 0} 个迁移`);
      } else {
        addLog(`✗ 迁移失败: ${r.error || '未知错误'}`);
      }
      refetchStatus();
      qc.invalidateQueries({queryKey: ['system-version']});
    },
    onError: (err: Error) => addLog(`✗ 迁移失败: ${err.message}`),
  });

  // Rollback
  const rollbackMut = useMutation({
    mutationFn: async () => {
      addLog(`正在回滚 ${rollbackSteps} 步...`);
      const r = await apiClient.post(`${SYSTEM.INFO.replace('/info', '')}/migrations/rollback`, {steps: rollbackSteps});
      return r;
    },
    onSuccess: (r: any) => {
      if (r.success) {
        addLog(`✓ 回滚成功`);
      } else {
        addLog(`✗ 回滚失败: ${r.error || '未知错误'}`);
      }
      refetchStatus();
      qc.invalidateQueries({queryKey: ['system-version']});
    },
    onError: (err: Error) => addLog(`✗ 回滚失败: ${err.message}`),
  });

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Database className="w-5 h-5"/>数据库迁移
        </h3>
        <button onClick={() => refetchStatus()} disabled={statusLoading}
                className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 inline-flex items-center gap-1">
          <RotateCcw className="w-3 h-3"/>刷新
        </button>
      </div>

      <div className="p-6 space-y-4">
        {/* Current status */}
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">当前版本: </span>
            <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">
              {statusLoading ? '...' : migStatus?.current_revision?.slice(0, 12) || '未知'}
            </code>
          </div>
          {migStatus?.pending_count > 0 && (
            <span className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded-full text-xs font-medium">
              待处理: {migStatus.pending_count}
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-3">
          <button onClick={() => applyMut.mutate()} disabled={applyMut.isPending}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-all shadow-lg shadow-blue-500/25">
            {applyMut.isPending ? <Loader className="w-4 h-4 animate-spin"/> : <Upload className="w-4 h-4"/>}
            执行迁移
          </button>

          <div className="flex items-center gap-2">
            <button onClick={() => rollbackMut.mutate()} disabled={rollbackMut.isPending}
                    className="inline-flex items-center gap-1.5 px-4 py-2 border border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 hover:bg-orange-100 dark:hover:bg-orange-900/30 text-sm font-medium rounded-xl disabled:opacity-50 transition-all">
              {rollbackMut.isPending ? <Loader className="w-4 h-4 animate-spin"/> : <Download className="w-4 h-4"/>}
              回滚
            </button>
            <label className="sr-only" htmlFor="rollback-steps">回滚步数</label>
            <input id="rollback-steps" type="number" min={1} max={10} value={rollbackSteps}
                   onChange={e => setRollbackSteps(Math.max(1, parseInt(e.target.value) || 1))}
                   className="w-16 px-2 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-center"/>
            <span className="text-xs text-gray-400">步</span>
          </div>
        </div>

        {/* Log */}
        {log.length > 0 && (
          <div className="mt-2 p-3 rounded-xl bg-gray-950 dark:bg-black text-green-400 text-[11px] font-mono max-h-40 overflow-y-auto space-y-0.5">
            {log.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Zone 3: Quick Links ───────────────────────
const QUICK_LINKS = [
  { href: '/admin/backup', label: '备份管理', icon: Download, desc: '数据库备份、恢复与下载', color: 'bg-emerald-500' },
  { href: '/admin/system-hub', label: '系统管理', icon: Server, desc: '插件、审计、敏感词', color: 'bg-purple-500' },
  { href: '/admin/settings', label: '系统设置', icon: Activity, desc: '站点配置、菜单、页面', color: 'bg-blue-500' },
];

function QuickLinksCard() {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5"/>快捷入口
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {QUICK_LINKS.map(link => {
          const Icon = link.icon;
          return (
            <a key={link.href} href={link.href}
               className="group flex items-center gap-3 p-3.5 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm transition-all">
              <div className={`w-10 h-10 rounded-xl ${link.color} flex items-center justify-center shrink-0`}>
                <Icon className="w-5 h-5 text-white"/>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1">
                  {link.label}
                  <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:translate-x-0.5 transition-transform"/>
                </p>
                <p className="text-[10px] text-gray-400 truncate">{link.desc}</p>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────
function UpgradeInner() {
  return (
    <AdminShell title="系统升级">
      <div className="space-y-6">
        <VersionStatusCard/>
        <MigrationCard/>
        <QuickLinksCard/>
      </div>
    </AdminShell>
  );
}

export default function AdminUpgrade() {
  return (
    <QueryProvider>
      <AuthGuard>
        <PermissionGuard capability="settings:view">
          <UpgradeInner/>
        </PermissionGuard>
      </AuthGuard>
    </QueryProvider>
  );
}
