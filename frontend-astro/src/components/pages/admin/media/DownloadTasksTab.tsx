import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {SYSTEM} from '@/lib/api/api-paths';
import {
  Ban, CheckCircle2, Clock, Download, FileText, Image, Music, RotateCcw,
  ArrowRightLeft, Video, X, File
} from 'lucide-react';
import {TaskSkeleton, Pagination} from './MediaUI';
import {type DownloadTaskItem, STATUS_CONFIG, timeAgo} from './MediaTypes';
import {formatBytes} from '@/lib/utils';

export function DownloadTasksTab() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const {data, isLoading, refetch} = useQuery({
    queryKey: ['download-tasks', page, statusFilter],
    queryFn: async () => {
      const params: Record<string, string | number> = {page, per_page: 20};
      if (statusFilter) params.status = statusFilter;
      const res = await apiClient.get(SYSTEM.TRANSFER_TASKS, params);
      return {
        tasks: (res.data || []) as DownloadTaskItem[],
        total: res.pagination?.total || 0,
        totalPages: res.pagination?.total_pages || 1,
      };
    },
  });

  const tasks = data?.tasks || [];
  const totalPages = data?.totalPages || 1;
  const total = data?.total || 0;

  const STATUS_FILTERS = [
    {value: '', label: '全部'},
    {value: 'pending', label: '等待中'},
    {value: 'downloading', label: '下载中'},
    {value: 'completed', label: '已完成'},
    {value: 'failed', label: '失败'},
  ];

  return (
    <>
      {/* 工具栏 */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className="flex items-center gap-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-1 overflow-x-auto">
          {STATUS_FILTERS.map(s => (
            <button key={s.value} onClick={() => {
              setStatusFilter(s.value);
              setPage(1);
            }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                      statusFilter === s.value
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex-1"/>
        <button onClick={() => refetch()}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <RotateCcw className="w-4 h-4"/>
        </button>
      </div>

      {/* 任务列表 */}
      {isLoading ? (
        <TaskSkeleton/>
      ) : tasks.length === 0 ? (
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-16 text-center">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <Download className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {statusFilter ? '没有匹配的下载任务' : '暂无下载任务'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {statusFilter ? '尝试切换筛选条件' : '通过 API 创建外部资源下载任务'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map(task => {
            const sc = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending;
            const StatusIcon = sc.icon;
            return (
              <div key={task.id}
                   className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition-colors">
                {/* 图标 */}
                <div
                  className="w-10 h-10 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                  {task.resource_type === 'image' ? <Image className="w-5 h-5 text-blue-500"/> :
                    task.resource_type === 'video' ? <Video className="w-5 h-5 text-purple-500"/> :
                      <File className="w-5 h-5 text-gray-400"/>}
                </div>

                {/* 信息 */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {task.filename || task.source_url}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-gray-400 truncate max-w-xs">{task.source_url}</p>
                    {task.total_size && (
                      <span className="text-xs text-gray-400">{formatBytes(task.total_size)}</span>
                    )}
                  </div>
                  {/* 进度条 */}
                  {(task.status === 'downloading' || task.status === 'processing') && (
                    <div className="mt-2 w-full max-w-xs">
                      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full transition-all duration-300"
                             style={{width: `${task.progress || 0}%`}}/>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{task.progress || 0}%</p>
                    </div>
                  )}
                  {task.error_message && task.status === 'failed' && (
                    <p className="text-xs text-red-500 dark:text-red-400 mt-1 truncate">{task.error_message}</p>
                  )}
                </div>

                {/* 状态标签 */}
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${sc.color}`}>
                        <StatusIcon className="w-3 h-3"/>{sc.label}
                      </span>

                {/* 时间 */}
                <span className="text-xs text-gray-400 hidden sm:block w-20 text-right">
                        {task.created_at ? timeAgo(task.created_at) : '-'}
                      </span>
              </div>
            );
          })}
        </div>
      )}

      {/* 分页 */}
      <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage}/>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   ── 上传任务 Tab ──
   ═══════════════════════════════════════════════════════════════════ */
