'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {MEDIA, MEMBERSHIP} from '@/lib/api/api-paths';
import {formatBytes} from '@/lib/utils';
import {
  Ban,
  CheckCircle2,
  Clock,
  Crown,
  Download,
  ExternalLink,
  File,
  FileText,
  Image,
  Link as LinkIcon,
  Music,
  RefreshCw,
  RotateCcw,
  Trash2,
  Video,
  X,
} from 'lucide-react';

/* ── 类型定义 ── */
interface OfflineDownloadTask {
  id: number;
  source_url: string;
  resource_type: string;
  filename: string;
  status: string;
  progress: number;
  total_size?: number;
  downloaded_size?: number;
  error_message?: string;
  media_id?: number;
  retry_count: number;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
}

interface DownloadLimits {
  vip_level: number;
  allowed: boolean;
  max_concurrent: number;
  max_file_size_mb: number;
  max_pending: number;
  active_count: number;
  remaining_slots: number;
}

interface VipStatus {
  is_vip: boolean;
  level: number;
  expires_at?: string;
  plan_name?: string;
}

/* ── 状态配置 ── */
const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  pending: {label: '等待中', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', icon: Clock},
  downloading: {label: '下载中', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', icon: Download},
  completed: {label: '已完成', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', icon: CheckCircle2},
  failed: {label: '失败', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: Ban},
  cancelled: {label: '已取消', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400', icon: RotateCcw},
};

const RESOURCE_TYPE_OPTIONS = [
  {value: 'image', label: '图片', icon: Image},
  {value: 'video', label: '视频', icon: Video},
  {value: 'audio', label: '音频', icon: Music},
  {value: 'document', label: '文档', icon: FileText},
] as const;

/* ═══════════════════════════════════════════════════════════════════
   ── 离线下载主弹窗 ──
   ═══════════════════════════════════════════════════════════════════ */
interface OfflineDownloadDialogProps {
  open: boolean;
  onClose: () => void;
}

export const OfflineDownloadDialog: React.FC<OfflineDownloadDialogProps> = ({open, onClose}) => {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState('');
  const [resourceType, setResourceType] = useState('image');
  const [activeTab, setActiveTab] = useState<'create' | 'tasks'>('create');
  const [statusFilter, setStatusFilter] = useState('');

  // ── 查询 VIP 状态和下载限制 ──
  const {data: vipStatus} = useQuery<VipStatus>({
    queryKey: ['vip-status'],
    queryFn: async () => {
      const r = await apiClient.get<any>(MEMBERSHIP.STATUS);
      return (r.success && r.data) ? r.data : {is_vip: false, level: 0};
    },
    enabled: open,
    staleTime: 30_000,
  });

  const {data: limits} = useQuery<DownloadLimits>({
    queryKey: ['offline-download-limits'],
    queryFn: async () => {
      const r = await apiClient.get<any>(MEDIA.OFFLINE_DOWNLOAD_LIMITS);
      return (r.success && r.data) ? r.data : {allowed: false, vip_level: 0, max_concurrent: 0, max_file_size_mb: 0, max_pending: 0, active_count: 0, remaining_slots: 0};
    },
    enabled: open,
    staleTime: 10_000,
  });

  // ── 查询下载任务列表 ──
  const {data: tasksData, isLoading: tasksLoading, refetch: refetchTasks} = useQuery<{ tasks: OfflineDownloadTask[]; pagination: any }>({
    queryKey: ['offline-download-tasks', statusFilter],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (statusFilter) params.status = statusFilter;
      const r = await apiClient.get<any>(MEDIA.OFFLINE_DOWNLOAD_TASKS, params);
      return (r.success && r.data) ? r.data : {tasks: [], pagination: {}};
    },
    enabled: open,
    refetchInterval: (query) => {
      // 有活跃任务时轮询
      const data = query.state.data;
      if (data?.tasks?.some(t => t.status === 'downloading' || t.status === 'pending')) {
        return 3000; // 3秒
      }
      return false;
    },
  });

  const tasks = tasksData?.tasks || [];

  // ── 创建下载任务 ──
  const createMutation = useMutation({
    mutationFn: async (params: { url: string; resource_type: string }) => {
      return apiClient.post(MEDIA.OFFLINE_DOWNLOAD_TASKS, params);
    },
    onSuccess: (res) => {
      if (res.success) {
        setUrl('');
        setActiveTab('tasks');
        queryClient.invalidateQueries({queryKey: ['offline-download-tasks']});
        queryClient.invalidateQueries({queryKey: ['offline-download-limits']});
      } else {
        alert(res.error || '创建失败');
      }
    },
    onError: (e: Error) => alert(e.message || '创建失败'),
  });

  // ── 取消任务 ──
  const cancelMutation = useMutation({
    mutationFn: async (taskId: number) => apiClient.post(MEDIA.OFFLINE_DOWNLOAD_CANCEL(taskId)),
    onSuccess: (res) => {
      if (res.success) {
        queryClient.invalidateQueries({queryKey: ['offline-download-tasks']});
        queryClient.invalidateQueries({queryKey: ['offline-download-limits']});
      }
    },
  });

  // ── 重试任务 ──
  const retryMutation = useMutation({
    mutationFn: async (taskId: number) => apiClient.post(MEDIA.OFFLINE_DOWNLOAD_RETRY(taskId)),
    onSuccess: (res) => {
      if (res.success) {
        queryClient.invalidateQueries({queryKey: ['offline-download-tasks']});
      } else {
        alert(res.error || '重试失败');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    createMutation.mutate({url: url.trim(), resource_type: resourceType});
  };

  const isVip = vipStatus?.is_vip || false;
  const isAllowed = limits?.allowed || false;
  const remainingSlots = limits?.remaining_slots ?? 0;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
              <Download className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">离线下载</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {isVip
                  ? `VIP Lv.{limits?.vip_level || vipStatus?.level || 1} · 剩余 ${remainingSlots} 个下载槽位`
                  : 'VIP 会员专属功能'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
            <X className="w-5 h-5"/>
          </button>
        </div>

        {/* VIP 升级提示 */}
        {!isVip && (
          <div className="mx-6 mt-4 p-4 rounded-xl bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800">
            <div className="flex items-start gap-3">
              <Crown className="w-6 h-6 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5"/>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">VIP 会员专属功能</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  离线下载仅限 VIP 会员使用。升级后可享受多并发下载、大文件支持等特权。
                </p>
                <a href="/vip"
                   className="inline-flex items-center gap-1 mt-2 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium transition-colors">
                  <Crown className="w-3.5 h-3.5"/>
                  立即升级
                </a>
              </div>
            </div>
          </div>
        )}

        {/* VIP 等级配额信息 */}
        {isVip && limits && (
          <div className="mx-6 mt-4 grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-center">
              <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{limits.max_concurrent}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">最大并发</p>
            </div>
            <div className="p-3 rounded-xl bg-green-50 dark:bg-green-900/20 text-center">
              <p className="text-lg font-bold text-green-600 dark:text-green-400">{limits.max_file_size_mb}MB</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">单文件限制</p>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 text-center">
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400">{remainingSlots}/{limits.max_concurrent}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">可用槽位</p>
            </div>
          </div>
        )}

        {/* 标签页切换 */}
        <div className="flex items-center gap-1 px-6 mt-4 border-b dark:border-gray-700">
          <button
            onClick={() => setActiveTab('create')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'create'
                ? 'border-purple-600 text-purple-600 dark:text-purple-400 dark:border-purple-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            新建下载
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'tasks'
                ? 'border-purple-600 text-purple-600 dark:text-purple-400 dark:border-purple-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            下载列表
            {tasks.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-[10px] rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
                {tasks.length}
              </span>
            )}
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'create' ? (
            <CreateTab
              url={url}
              onUrlChange={setUrl}
              resourceType={resourceType}
              onResourceTypeChange={setResourceType}
              onSubmit={handleSubmit}
              isAllowed={isAllowed}
              isVip={isVip}
              isSubmitting={createMutation.isPending}
              remainingSlots={remainingSlots}
            />
          ) : (
            <TasksTab
              tasks={tasks}
              loading={tasksLoading}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              onCancel={(id) => cancelMutation.mutate(id)}
              onRetry={(id) => retryMutation.mutate(id)}
              onRefresh={() => refetchTasks()}
            />
          )}
        </div>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   ── 新建下载 Tab ──
   ═══════════════════════════════════════════════════════════════════ */
const CreateTab: React.FC<{
  url: string;
  onUrlChange: (v: string) => void;
  resourceType: string;
  onResourceTypeChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isAllowed: boolean;
  isVip: boolean;
  isSubmitting: boolean;
  remainingSlots: number;
}> = ({url, onUrlChange, resourceType, onResourceTypeChange, onSubmit, isAllowed, isVip, isSubmitting, remainingSlots}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAllowed) inputRef.current?.focus();
  }, [isAllowed]);

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {/* URL 输入 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          资源链接 <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
          <input
            ref={inputRef}
            type="url"
            value={url}
            onChange={e => onUrlChange(e.target.value)}
            placeholder={isAllowed ? "粘贴视频 / 图片 / 文件 URL..." : "升级 VIP 后可使用离线下载"}
            disabled={!isAllowed || isSubmitting}
            className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
        <p className="mt-1 text-xs text-gray-400">
          支持 http:// 和 https:// 开头的资源链接
        </p>
      </div>

      {/* 资源类型 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">资源类型</label>
        <div className="flex items-center gap-2">
          {RESOURCE_TYPE_OPTIONS.map(opt => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => onResourceTypeChange(opt.value)}
                disabled={!isAllowed || isSubmitting}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  resourceType === opt.value
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                } disabled:opacity-50`}
              >
                <Icon className="w-4 h-4"/>
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 提交 */}
      <button
        type="submit"
        disabled={!url.trim() || !isAllowed || isSubmitting || remainingSlots <= 0}
        className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
            创建中...
          </>
        ) : remainingSlots <= 0 && isAllowed ? (
          '下载槽位已满，请等待现有任务完成'
        ) : (
          <>
            <Download className="w-4 h-4"/>
            添加到离线下载
          </>
        )}
      </button>

      {/* 使用提示 */}
      <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">使用提示</h4>
        <ul className="space-y-1.5 text-xs text-gray-500 dark:text-gray-400">
          <li className="flex items-start gap-2">
            <span className="text-purple-500 mt-0.5">•</span>
            输入外部资源的直链 URL，系统将自动下载并保存到您的媒体库
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-500 mt-0.5">•</span>
            支持图片、视频、音频和文档等多种格式
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-500 mt-0.5">•</span>
            下载完成后可在媒体库中查看和管理已下载的文件
          </li>
          {isVip && (
            <li className="flex items-start gap-2">
              <span className="text-purple-500 mt-0.5">•</span>
              高级 VIP 享有更高的并发和文件大小限制
            </li>
          )}
        </ul>
      </div>
    </form>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   ── 下载任务列表 Tab ──
   ═══════════════════════════════════════════════════════════════════ */
const TasksTab: React.FC<{
  tasks: OfflineDownloadTask[];
  loading: boolean;
  statusFilter: string;
  onStatusFilterChange: (v: string) => void;
  onCancel: (id: number) => void;
  onRetry: (id: number) => void;
  onRefresh: () => void;
}> = ({tasks, loading, statusFilter, onStatusFilterChange, onCancel, onRetry, onRefresh}) => {
  const STATUS_FILTERS = [
    {value: '', label: '全部'},
    {value: 'pending', label: '等待中'},
    {value: 'downloading', label: '下载中'},
    {value: 'completed', label: '已完成'},
    {value: 'failed', label: '失败'},
    {value: 'cancelled', label: '已取消'},
  ];

  return (
    <div className="space-y-4">
      {/* 筛选栏 */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 overflow-x-auto flex-1">
          {STATUS_FILTERS.map(s => (
            <button
              key={s.value}
              onClick={() => onStatusFilterChange(s.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                statusFilter === s.value
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <button
          onClick={onRefresh}
          className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4"/>
        </button>
      </div>

      {/* 任务列表 */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800">
              <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-xl"/>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48"/>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
              </div>
              <div className="w-20 h-6 bg-gray-200 dark:bg-gray-700 rounded-full"/>
            </div>
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <div className="py-16 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <Download className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
            {statusFilter ? '没有匹配的下载任务' : '暂无离线下载任务'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {statusFilter ? '尝试切换筛选条件' : '在「新建下载」中输入链接开始离线下载'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map(task => {
            const sc = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending;
            const StatusIcon = sc.icon;
            return (
              <div
                key={task.id}
                className="group flex items-start gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition-colors"
              >
                {/* 类型图标 */}
                <div className="w-10 h-10 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                  {task.resource_type === 'image' ? <Image className="w-5 h-5 text-blue-500"/> :
                    task.resource_type === 'video' ? <Video className="w-5 h-5 text-purple-500"/> :
                      task.resource_type === 'audio' ? <Music className="w-5 h-5 text-amber-500"/> :
                        <File className="w-5 h-5 text-gray-400"/>}
                </div>

                {/* 信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {task.filename || task.source_url}
                    </p>
                    {task.media_id && (
                      <a
                        href={`/media`}
                        className="text-blue-500 hover:text-blue-600"
                        title="已导入媒体库"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5"/>
                      </a>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 truncate max-w-md mt-0.5">{task.source_url}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {task.total_size && (
                      <span className="text-xs text-gray-400">{formatBytes(task.total_size)}</span>
                    )}
                    {task.downloaded_size && task.status === 'downloading' && (
                      <span className="text-xs text-gray-400">
                        / {formatBytes(task.downloaded_size)} 已下载
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : ''}
                    </span>
                  </div>

                  {/* 进度条 */}
                  {(task.status === 'downloading' || task.status === 'pending') && (
                    <div className="mt-2 w-full">
                      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-500"
                          style={{width: `${task.progress || 0}%`}}
                        />
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{task.progress || 0}%</p>
                    </div>
                  )}

                  {task.error_message && task.status === 'failed' && (
                    <p className="text-xs text-red-500 dark:text-red-400 mt-1 truncate">{task.error_message}</p>
                  )}
                </div>

                {/* 状态 + 操作 */}
                <div className="flex flex-col items-end gap-2 shrink-0">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${sc.color}`}>
                    <StatusIcon className="w-3 h-3"/>{sc.label}
                  </span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {task.status === 'downloading' && (
                      <button
                        onClick={() => onCancel(task.id)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        title="取消下载"
                      >
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                    {task.status === 'failed' && (
                      <button
                        onClick={() => onRetry(task.id)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                        title="重试下载"
                      >
                        <RefreshCw className="w-3.5 h-3.5"/>
                      </button>
                    )}
                    {task.status === 'pending' && (
                      <button
                        onClick={() => onCancel(task.id)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        title="取消"
                      >
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
