'use client';

import React, {useState, useEffect, useRef, useMemo} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {useConfirm} from '@/components/ui/confirm-provider';
import {
  Check,
  X,
  MessageSquare,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  User,
  FileText,
  RefreshCw,
  MoreHorizontal,
  Eye,
  Trash2,
  Filter,
  ChevronRight,
  Search,
  Shield,
  ThumbsUp,
  ThumbsDown,
  Ban
} from 'lucide-react';

const STATUS_TABS = [
    {value: 'pending', label: '待审核', icon: Clock, color: 'amber'},
    {value: 'approved', label: '已通过', icon: CheckCircle2, color: 'green'},
    {value: 'rejected', label: '已拒绝', icon: XCircle, color: 'red'},
    {value: '', label: '全部', icon: MessageSquare, color: 'gray'},
] as const;

/* ── Comment Avatar ── */
const CommentAvatar: React.FC<{ name: string }> = ({name}) => {
    const colors = ['from-blue-500 to-indigo-500', 'from-purple-500 to-pink-500', 'from-emerald-500 to-teal-500', 'from-amber-500 to-orange-500', 'from-rose-500 to-red-500', 'from-cyan-500 to-blue-500'];
    const colorIndex = (name || '').charCodeAt(0) % colors.length;
    return (
        <div
            className={`w-9 h-9 rounded-full bg-gradient-to-br ${colors[colorIndex]} flex items-center justify-center text-white text-sm font-bold shadow-sm shrink-0`}>
            {(name || '?').charAt(0).toUpperCase()}
        </div>
    );
};

/* ── Status Badge ── */
const CommentStatusBadge: React.FC<{ status: string }> = ({status}) => {
    const config = useMemo(() => {
        switch (status) {
            case 'approved':
                return {
                    label: '已通过',
                    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
                    text: 'text-emerald-700 dark:text-emerald-400',
                    dot: 'bg-emerald-500'
                };
            case 'rejected':
                return {
                    label: '已拒绝',
                    bg: 'bg-red-50 dark:bg-red-900/20',
                    text: 'text-red-700 dark:text-red-400',
                    dot: 'bg-red-500'
                };
            default:
                return {
                    label: '待审核',
                    bg: 'bg-amber-50 dark:bg-amber-900/20',
                    text: 'text-amber-700 dark:text-amber-400',
                    dot: 'bg-amber-500'
                };
        }
    }, [status]);
    return (
        <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${config.bg} ${config.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`}/>{config.label}
    </span>
    );
};

/* ── Comment Card ── */
const CommentCard: React.FC<{
    comment: any;
    onApprove: () => void;
    onReject: () => void;
    onDelete: () => void;
    isPending?: boolean;
}> = ({comment, onApprove, onReject, onDelete, isPending}) => {
    const [showActions, setShowActions] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!showActions) return;
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setShowActions(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [showActions]);

    return (
        <div className={`group p-5 hover:bg-gray-50/80 dark:hover:bg-gray-800/30 transition-colors ${
            comment.status === 'pending' ? 'border-l-2 border-l-amber-400' : ''
        }`}>
            <div className="flex items-start gap-3">
                <CommentAvatar name={comment.author_name || comment.author?.username || '匿名'}/>

                <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-1.5">
            <span className="font-medium text-gray-900 dark:text-white text-sm">
              {comment.author_name || comment.author?.username || '匿名用户'}
            </span>
                        <CommentStatusBadge status={comment.status || 'pending'}/>
                        <span className="text-xs text-gray-400 ml-auto shrink-0">
              {comment.created_at ? new Date(comment.created_at).toLocaleString('zh-CN') : ''}
            </span>
                    </div>

                    {/* Content */}
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-2">{comment.content}</p>

                    {/* Article Reference */}
                    {comment.article_title && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-400">
                            <FileText className="w-3 h-3"/>
                            <span>评论文章：</span>
                            <a href={`/view?slug=${comment.article_slug || ''}`} target="_blank"
                               rel="noopener noreferrer"
                               className="text-blue-500 hover:text-blue-600 hover:underline truncate max-w-[200px]">
                                {comment.article_title}
                            </a>
                        </div>
                    )}

                    {/* Action Buttons for Pending */}
                    {comment.status === 'pending' && (
                        <div className="flex items-center gap-2 mt-3">
                            <button onClick={onApprove}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium rounded-lg shadow-sm shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all">
                                <ThumbsUp className="w-3.5 h-3.5"/>通过
                            </button>
                            <button onClick={onReject}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-medium rounded-lg shadow-sm shadow-red-500/20 hover:shadow-red-500/30 transition-all">
                                <ThumbsDown className="w-3.5 h-3.5"/>拒绝
                            </button>
                        </div>
                    )}
                </div>

                {/* More Actions */}
                <div className="relative shrink-0" ref={ref}>
                    <button onClick={() => setShowActions(!showActions)}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 opacity-0 group-hover:opacity-100 transition-all">
                        <MoreHorizontal className="w-4 h-4"/>
                    </button>
                    {showActions && (
                        <div
                            className="absolute right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5 min-w-[140px]">
                            {comment.status !== 'approved' && (
                                <button onClick={() => {
                                    setShowActions(false);
                                    onApprove();
                                }}
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors">
                                    <Check className="w-4 h-4"/>通过
                                </button>
                            )}
                            {comment.status !== 'rejected' && (
                                <button onClick={() => {
                                    setShowActions(false);
                                    onReject();
                                }}
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                                    <X className="w-4 h-4"/>拒绝
                                </button>
                            )}
                            <div className="h-px bg-gray-100 dark:bg-gray-700 my-1"/>
                            <button onClick={() => {
                                setShowActions(false);
                                onDelete();
                            }}
                                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                                <Trash2 className="w-4 h-4"/>删除
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

function CommentsInner() {
  const confirm = useConfirm();
  const qc = useQueryClient();
    const [statusFilter, setStatusFilter] = useState('pending');
    const [searchInput, setSearchInput] = useState('');

    const {data: comments, isLoading, refetch} = useQuery({
        queryKey: ['admin-comments', statusFilter],
    queryFn: async () => {
        if (statusFilter === 'pending') {
          const res = await apiClient.get<unknown[]>('/comments/admin/comments/pending');
            return res.success && res.data ? (Array.isArray(res.data) ? res.data : []) : [];
        }
      const res = await apiClient.get<unknown[]>('/comments/admin/comments', {status: statusFilter || undefined});
        return res.success && res.data ? (Array.isArray(res.data) ? res.data : (res.data as any).comments || []) : [];
    },
  });

  const approveMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/comments/admin/comments/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-comments']}),
  });

  const rejectMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/comments/admin/comments/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['admin-comments']}),
  });

    const deleteMut = useMutation({
        mutationFn: (id: number) => apiClient.delete(`/comments/admin/comments/${id}`),
        onSuccess: () => qc.invalidateQueries({queryKey: ['admin-comments']}),
    });

    const filteredComments = useMemo(() => {
        if (!comments) return [];
        if (!searchInput) return comments;
        const q = searchInput.toLowerCase();
      return comments.filter((c) =>
            (c.content || '').toLowerCase().includes(q) ||
            (c.author_name || '').toLowerCase().includes(q) ||
            (c.article_title || '').toLowerCase().includes(q)
        );
    }, [comments, searchInput]);

    // Stats
    const allComments = comments || [];
    const stats = useMemo(() => ({
      pending: allComments.filter((c) => c.status === 'pending' || !c.status).length,
      approved: allComments.filter((c) => c.status === 'approved').length,
      rejected: allComments.filter((c) => c.status === 'rejected').length,
        total: allComments.length,
    }), [allComments]);

    return (
        <AdminShell title="评论管理" actions={
            <button onClick={() => refetch()}
                    className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    title="刷新">
                <RefreshCw className="w-4 h-4"/>
            </button>
        }>
            {/* Status Tabs */}
            <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1">
                {STATUS_TABS.map(tab => {
                    const count = tab.value === 'pending' ? stats.pending : tab.value === 'approved' ? stats.approved : tab.value === 'rejected' ? stats.rejected : stats.total;
                    return (
                        <button key={tab.value} onClick={() => setStatusFilter(tab.value)}
                                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                                    statusFilter === tab.value
                                        ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-md shadow-gray-200/50 dark:shadow-gray-900/50 border border-gray-200 dark:border-gray-700'
                                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
                                }`}>
                            <tab.icon className="w-4 h-4"/>
                            {tab.label}
                            <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full ${
                                statusFilter === tab.value
                                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                            }`}>{count}</span>
                        </button>
                    );
                })}
            </div>

            {/* Search */}
            <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
                       placeholder="搜索评论内容、作者、文章标题..."
                       className="w-full pl-10 pr-10 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:text-white transition-all"/>
                {searchInput && (
                    <button onClick={() => setSearchInput('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600 transition-colors">
                        <X className="w-4 h-4"/>
                    </button>
                )}
            </div>

            {/* Comments List */}
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm">
        {isLoading ? (
            <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="p-5 animate-pulse">
                        <div className="flex items-start gap-3">
                            <div className="w-9 h-9 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded"/>
                                    <div className="h-5 w-16 bg-gray-100 dark:bg-gray-800 rounded-full"/>
                                </div>
                                <div className="h-4 w-full bg-gray-100 dark:bg-gray-800 rounded"/>
                                <div className="h-3 w-2/3 bg-gray-50 dark:bg-gray-800/50 rounded"/>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        ) : filteredComments.length === 0 ? (
            <div className="p-16 text-center">
                <div
                    className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <MessageSquare className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                    {searchInput ? '未找到匹配的评论' : statusFilter === 'pending' ? '暂无待审评论' : '暂无评论'}
                </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                    {searchInput ? '尝试使用不同的关键词搜索' : statusFilter === 'pending' ? '所有评论都已处理完毕' : '该分类下暂无评论'}
                </p>
            </div>
        ) : (
            <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
              {filteredComments.map((c) => (
                    <CommentCard
                        key={c.id}
                        comment={c}
                        onApprove={() => approveMut.mutate(c.id)}
                        onReject={() => rejectMut.mutate(c.id)}
                        onDelete={async () => {
                          if (await confirm({
                            message: '确认删除此评论？此操作不可恢复。',
                            variant: 'danger'
                          })) deleteMut.mutate(c.id);
                        }}
                    />
                ))}
            </div>
        )}
            </div>

            {/* Batch Actions for Pending */}
            {statusFilter === 'pending' && filteredComments.length > 0 && (
                <div
                    className="flex items-center justify-between mt-4 p-4 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30 rounded-xl">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600"/>
                        <span className="text-sm text-amber-800 dark:text-amber-300">
              有 <strong>{filteredComments.length}</strong> 条待审核评论
            </span>
                    </div>
                  <button onClick={async () => {
                    if (await confirm({
                      message: `确认批量通过所有 ${filteredComments.length} 条评论？`,
                      variant: 'danger'
                    })) {
                      filteredComments.forEach((c) => approveMut.mutate(c.id));
                        }
                    }}
                            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition-colors">
                        <CheckCircle2 className="w-4 h-4"/>全部通过
                    </button>
                </div>
            )}
    </AdminShell>
  );
}

export default function AdminComments() {
  return <AuthGuard><QueryProvider><CommentsInner /></QueryProvider></AuthGuard>;
}
