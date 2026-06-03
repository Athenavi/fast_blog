'use client';

import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AnimatePresence, motion} from 'framer-motion';
import {apiClient} from '@/lib/api/base-client';
import {getFullMediaUrl, timeAgo} from '@/lib/utils';
import {QueryProvider} from '@/components/QueryProvider';
import {AuthGuard} from '@/components/AuthGuard';
import {useConfirm} from '@/components/ui/confirm-provider';
import {
  BookOpen,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Copy,
  Crown,
  Edit,
  Eye,
  EyeOff,
  FileText,
  Globe,
  Grid,
  Heart,
  KeyRound,
  LayoutList,
  Loader2,
  Lock,
  MoreHorizontal,
  PenSquare,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  X
} from 'lucide-react';

/* ── Types ── */
interface Article {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  summary?: string;
  cover_image?: string;
  status: any;
  views?: number;
  likes?: number;
  hidden?: boolean;
  is_vip_only?: boolean;
  has_password?: boolean;
  created_at: string;
  updated_at?: string;
  category_name?: string;
  tags?: string[];
}

type ViewMode = 'list' | 'grid';
type StatusTab = 'all' | 'published' | 'drafts';

/* ── Helpers ── */
const isPublished = (s: any) => s === 'publish' || s === 'published' || s === 1 || s === true;
const isDraft = (s: any) => !isPublished(s) && s !== 'deleted';
const statusLabel = (s: any) => isPublished(s) ? '已发布' : '草稿';

const fadeUp = {hidden: {opacity: 0, y: 16}, show: {opacity: 1, y: 0, transition: {duration: 0.3}}};
const stagger = {show: {transition: {staggerChildren: 0.04}}};

/* ── Password Modal ── */
const PasswordModal: React.FC<{
  article: Article;
  onClose: () => void;
  onSuccess: () => void;
}> = ({article, onClose, onSuccess}) => {
  const [password, setPassword] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const isSet = !!article.has_password;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isSet && !password) {
      setError('请输入密码');
      return;
    }
    if (!isSet && password.length < 4) {
      setError('密码至少 4 位');
      return;
    }
    if (!isSet && password !== confirmPwd) {
      setError('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post(`/articles/${article.id}/password`, {password: isSet ? null : password});
      if (res.success) {
        onSuccess();
        onClose();
      } else {
        setError(res.error || '操作失败');
      }
    } catch (err: any) {
      setError(err.message || '网络错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}
                className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
                onClick={onClose}>
      <motion.div initial={{opacity: 0, scale: 0.95, y: 20}} animate={{opacity: 1, scale: 1, y: 0}}
                  exit={{opacity: 0, scale: 0.95, y: 20}}
                  className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-md overflow-hidden"
                  onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl ${isSet ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'}`}>
              {isSet ? <Lock className="w-5 h-5"/> : <KeyRound className="w-5 h-5"/>}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{isSet ? '移除文章密码' : '设置文章密码'}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">{article.title}</p>
            </div>
          </div>
          <button onClick={onClose}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-4 h-4"/>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {isSet ? (
            <div
              className="flex items-center gap-3 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
              <ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0"/>
              <p
                className="text-sm text-amber-700 dark:text-amber-300">当前文章已设置密码保护，确认后将移除密码，任何人都可访问。</p>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">访问密码</label>
                <input ref={inputRef} type="password" value={password} onChange={e => setPassword(e.target.value)}
                       placeholder="设置 4 位以上密码" minLength={4}
                       className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:text-white transition-all"/>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">确认密码</label>
                <input type="password" value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)}
                       placeholder="再次输入密码" minLength={4}
                       className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:text-white transition-all"/>
              </div>
              <div
                className="flex items-center gap-2 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <Lock className="w-4 h-4 text-blue-500 flex-shrink-0"/>
                <p
                  className="text-xs text-blue-600 dark:text-blue-400">设置密码后，访问者需要输入密码才能查看文章内容。</p>
              </div>
            </>
          )}

          {error && (
            <p className="text-sm text-red-500 dark:text-red-400 flex items-center gap-1.5">
              <X className="w-3.5 h-3.5"/>{error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button type="button" onClick={onClose}
                    className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
              取消
            </button>
            <button type="submit" disabled={loading}
                    className={`flex items-center gap-2 px-5 py-2 text-sm font-medium text-white rounded-xl transition-colors disabled:opacity-50 ${
                      isSet ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
                    }`}>
              {loading && <Loader2 className="w-4 h-4 animate-spin"/>}
              {isSet ? '确认移除' : '设置密码'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};

/* ── Stats Card ── */
const StatCard: React.FC<{
  icon: React.ElementType; label: string; value: number | string;
  color: string; delay?: number;
}> = ({icon: Icon, label, value, color, delay = 0}) => (
  <motion.div variants={fadeUp}
              className="flex items-center gap-3 p-4 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-shadow">
    <div className={`p-2.5 rounded-xl ${color}`}>
      <Icon className="w-5 h-5"/>
    </div>
    <div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  </motion.div>
);

/* ── Action Dropdown ── */
const ActionDropdown: React.FC<{
  article: Article; onEdit: () => void; onDelete: () => void; onDuplicate: () => void; onPassword: () => void;
}> = ({article, onEdit, onDelete, onDuplicate, onPassword}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button onClick={(e) => {
        e.stopPropagation();
        e.preventDefault();
        setOpen(!open);
      }}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
        <MoreHorizontal className="w-4 h-4"/>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div onClick={(e) => e.stopPropagation()} initial={{opacity: 0, scale: 0.95, y: -4}}
                      animate={{opacity: 1, scale: 1, y: 0}} exit={{opacity: 0, scale: 0.95, y: -4}}
                      transition={{duration: 0.12}}
                      className="absolute right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5 min-w-[180px]">
            <a href={`/my/posts/edit?id=${article.id}`} onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
            }}
               className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              <Edit className="w-4 h-4"/>编辑文章
            </a>
            <a href={`/view?slug=${article.slug}`} target="_blank" rel="noopener" onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
            }}
               className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              <Eye className="w-4 h-4"/>查看文章
            </a>
            <button onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onDuplicate();
              setOpen(false);
            }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              <Copy className="w-4 h-4"/>复制链接
            </button>
            <button onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onPassword();
              setOpen(false);
            }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
              {article.has_password ? <Lock className="w-4 h-4"/> : <KeyRound className="w-4 h-4"/>}
              {article.has_password ? '管理密码' : '设置密码'}
            </button>
            <div className="border-t border-gray-100 dark:border-gray-700 my-1"/>
            <button onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onDelete();
              setOpen(false);
            }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
              <Trash2 className="w-4 h-4"/>删除文章
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* ── List Item ── */
const ArticleListItem: React.FC<{
  article: Article; onDelete: () => void; onDuplicate: () => void; onPassword: () => void; index: number;
}> = ({article, onDelete, onDuplicate, onPassword, index}) => {
  const cover = getFullMediaUrl(article.cover_image);
  const published = isPublished(article.status);

  return (
    <motion.div variants={fadeUp}
                className="group bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-lg transition-all duration-300">
      <div className="flex flex-col sm:flex-row">
        {/* Cover Image */}
        {cover && (
          <a href={`/my/posts/edit?id=${article.id}`}
             className="block sm:w-48 md:w-56 h-40 sm:h-auto sm:self-stretch flex-shrink-0 overflow-hidden bg-gray-100 dark:bg-gray-800">
            <img src={cover} alt="" loading="lazy"
                 className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"/>
          </a>
        )}
        {/* Content */}
        <div className="flex-1 p-4 sm:p-5 flex flex-col min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {/* Status + Badges */}
              <div className="flex items-center gap-2 mb-2">
                <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                  published ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                }`}>{statusLabel(article.status)}</span>
                {article.hidden && <span className="flex items-center gap-1 text-xs text-gray-400"><EyeOff
                  className="w-3 h-3"/>隐藏</span>}
                {article.is_vip_only && <span className="flex items-center gap-1 text-xs text-amber-500"><Crown
                  className="w-3 h-3"/>VIP</span>}
                {article.has_password && <span className="flex items-center gap-1 text-xs text-blue-500"><Lock
                  className="w-3 h-3"/>已加密</span>}
              </div>
              {/* Title */}
              <a href={`/my/posts/edit?id=${article.id}`}
                 className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors line-clamp-2 text-base leading-snug">
                {article.title || '无标题'}
              </a>
              {/* Excerpt */}
              {(article.excerpt || article.summary) && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">
                  {article.excerpt || article.summary}
                </p>
              )}
            </div>
            {/* Actions */}
            <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <a href={`/my/posts/edit?id=${article.id}`}
                 className="p-2 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                 title="编辑">
                <Edit className="w-4 h-4"/>
              </a>
              <ActionDropdown article={article}
                              onEdit={() => window.location.href = `/my/posts/edit?id=${article.id}`}
                              onDelete={onDelete} onDuplicate={onDuplicate} onPassword={onPassword}/>
            </div>
          </div>
          {/* Meta */}
          <div
            className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-50 dark:border-gray-800 text-xs text-gray-400">
            {article.category_name &&
              <span className="flex items-center gap-1"><BookOpen className="w-3 h-3"/>{article.category_name}</span>}
            <span className="flex items-center gap-1"><Calendar
              className="w-3 h-3"/>{article.created_at ? timeAgo(article.created_at) : ''}</span>
            <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{article.views ?? 0}</span>
            <span className="flex items-center gap-1"><Heart className="w-3 h-3"/>{article.likes ?? 0}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

/* ── Grid Card ── */
const ArticleGridCard: React.FC<{
  article: Article; onDelete: () => void; onDuplicate: () => void; onPassword: () => void;
}> = ({article, onDelete, onDuplicate, onPassword}) => {
  const cover = getFullMediaUrl(article.cover_image);
  const published = isPublished(article.status);

  return (
    <motion.div variants={fadeUp}
                className="group bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-lg transition-all duration-300 flex flex-col">
      {/* Cover */}
      <a href={`/my/posts/edit?id=${article.id}`}
         className="block aspect-[16/10] bg-gray-100 dark:bg-gray-800 overflow-hidden relative">
        {cover ? (
          <img src={cover} alt="" loading="lazy"
               className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"/>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <FileText className="w-10 h-10 text-gray-200 dark:text-gray-700"/>
          </div>
        )}
        {/* Status badge overlay */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5">
          <span className={`px-2 py-0.5 text-xs rounded-full font-medium backdrop-blur-sm ${
            published ? 'bg-emerald-100/90 text-emerald-700 dark:bg-emerald-900/70 dark:text-emerald-300'
              : 'bg-amber-100/90 text-amber-700 dark:bg-amber-900/70 dark:text-amber-300'
          }`}>{statusLabel(article.status)}</span>
          {article.has_password && <span
            className="px-1.5 py-0.5 text-xs rounded-full font-medium backdrop-blur-sm bg-blue-100/90 text-blue-700 dark:bg-blue-900/70 dark:text-blue-300 flex items-center gap-1"><Lock
            className="w-3 h-3"/>加密</span>}
        </div>
        {/* Actions overlay */}
        <div
          className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
          <a href={`/my/posts/edit?id=${article.id}`}
             className="p-1.5 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm text-gray-600 dark:text-gray-300 hover:text-blue-600 transition-colors shadow-sm"
             title="编辑"><Edit className="w-3.5 h-3.5"/></a>
          <ActionDropdown article={article}
                          onEdit={() => window.location.href = `/my/posts/edit?id=${article.id}`}
                          onDelete={onDelete} onDuplicate={onDuplicate} onPassword={onPassword}/>
        </div>
      </a>
      {/* Content */}
      <div className="p-4 flex-1 flex flex-col">
        <a href={`/my/posts/edit?id=${article.id}`}
           className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors line-clamp-2 text-sm leading-snug">
          {article.title || '无标题'}
        </a>
        {(article.excerpt || article.summary) && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 line-clamp-2 leading-relaxed flex-1">
            {article.excerpt || article.summary}
          </p>
        )}
        <div
          className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-50 dark:border-gray-800 text-xs text-gray-400">
          <span className="flex items-center gap-1"><Calendar
            className="w-3 h-3"/>{article.created_at ? timeAgo(article.created_at) : ''}</span>
          <span className="flex items-center gap-1"><Eye className="w-3 h-3"/>{article.views ?? 0}</span>
        </div>
      </div>
    </motion.div>
  );
};

/* ── Skeleton ── */
const ListSkeleton: React.FC<{ viewMode: ViewMode }> = ({viewMode}) => (
  viewMode === 'grid' ? (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {[1, 2, 3, 4, 5, 6].map(i => (
        <div key={i} className="rounded-2xl overflow-hidden animate-pulse">
          <div className="aspect-[16/10] bg-gray-200 dark:bg-gray-800"/>
          <div className="p-4 space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-3/4"/>
            <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-full"/>
            <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-1/2"/>
          </div>
        </div>
      ))}
    </div>
  ) : (
    <div className="space-y-3">
      {[1, 2, 3, 4].map(i => (
        <div key={i}
             className="h-28 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 animate-pulse"/>
      ))}
    </div>
  )
);

/* ── Main Component ── */
function MyPostsInner() {
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [tab, setTab] = useState<StatusTab>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const perPage = 12;

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);

  // Reset page on filter change
  useEffect(() => {
    setPage(1);
  }, [debouncedQ, tab]);

  const {data, isLoading, isFetching} = useQuery({
    queryKey: ['my-posts', page, debouncedQ],
    queryFn: async () => {
      const res = await apiClient.get('/dashboard/my/articles', {page, per_page: perPage, q: debouncedQ || undefined});
      if (!res.success || !res.data) return {articles: [] as Article[], total: 0};
      if (Array.isArray(res.data)) return {articles: res.data, total: res.data.length};
      if (res.data.articles) return {
        articles: res.data.articles as Article[],
        total: res.data.total || res.data.articles.length
      };
      if (res.data.data) return {
        articles: ((res.data.data as any).articles || []) as Article[],
        total: (res.data.data as any).total || 0
      };
      return {articles: [] as Article[], total: 0};
    },
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/articles/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['my-posts']}),
  });

  const [pwdArticle, setPwdArticle] = useState<Article | null>(null);

  const allArticles = data?.articles || [];
  const total = data?.total || 0;

  // Client-side tab filter
  const articles = useMemo(() => {
    if (tab === 'published') return allArticles.filter(a => isPublished(a.status));
    if (tab === 'drafts') return allArticles.filter(a => isDraft(a.status));
    return allArticles;
  }, [allArticles, tab]);

  // Stats
  const stats = useMemo(() => {
    const published = allArticles.filter(a => isPublished(a.status)).length;
    const drafts = allArticles.filter(a => isDraft(a.status)).length;
    const totalViews = allArticles.reduce((s, a) => s + (a.views || 0), 0);
    const totalLikes = allArticles.reduce((s, a) => s + (a.likes || 0), 0);
    return {total: allArticles.length, published, drafts, totalViews, totalLikes};
  }, [allArticles]);

  const pages = Math.ceil(total / perPage);

  const handleCopyLink = useCallback((slug: string) => {
    navigator.clipboard.writeText(`${window.location.origin}/view?slug=${slug}`);
  }, []);

  const handleDelete = useCallback(async (id: number) => {
    if (await confirm({message: '确定要删除这篇文章吗？此操作不可撤销。', variant: 'danger'})) {
      delMut.mutate(id);
    }
  }, [confirm, delMut]);

  const tabs: { key: StatusTab; label: string; count: number }[] = [
    {key: 'all', label: '全部', count: stats.total},
    {key: 'published', label: '已发布', count: stats.published},
    {key: 'drafts', label: '草稿', count: stats.drafts},
  ];

  return (
    <>
      {pwdArticle && (
        <PasswordModal article={pwdArticle} onClose={() => setPwdArticle(null)}
                       onSuccess={() => qc.invalidateQueries({queryKey: ['my-posts']})}/>
      )}
      <div
        className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-gray-950 dark:via-gray-950 dark:to-gray-900 pt-20 pb-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">

          {/* ── Header ── */}
          <motion.div initial={{opacity: 0, y: -10}} animate={{opacity: 1, y: 0}} transition={{duration: 0.4}}
                      className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">我的文章</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">管理你的创作内容</p>
          </div>
            <a href="/my/posts/create"
               className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl transition-colors shadow-sm shadow-blue-500/20 hover:shadow-blue-500/30">
              <PenSquare className="w-4 h-4"/>写文章
            </a>
          </motion.div>

          {/* ── Stats Cards ── */}
          <motion.div variants={stagger} initial="hidden" animate="show"
                      className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
            <StatCard icon={BookOpen} label="总文章" value={stats.total}
                      color="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"/>
            <StatCard icon={Globe} label="已发布" value={stats.published}
                      color="bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"/>
            <StatCard icon={FileText} label="草稿" value={stats.drafts}
                      color="bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"/>
            <StatCard icon={Eye} label="总浏览" value={stats.totalViews}
                      color="bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"/>
          </motion.div>

          {/* ── Toolbar ── */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            {/* Tabs */}
            <div className="flex items-center bg-gray-100 dark:bg-gray-800/50 rounded-xl p-1">
              {tabs.map(t => (
                <button key={t.key} onClick={() => setTab(t.key)}
                        className={`relative px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                          tab === t.key
                            ? 'text-gray-900 dark:text-white'
                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                        }`}>
                  {tab === t.key && (
                    <motion.div layoutId="activeTab"
                                className="absolute inset-0 bg-white dark:bg-gray-700 rounded-lg shadow-sm"
                                transition={{type: 'spring', bounce: 0.2, duration: 0.4}}/>
                  )}
                  <span className="relative z-10">{t.label}</span>
                  <span className={`relative z-10 ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                    tab === t.key ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  }`}>{t.count}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                <input type="text" value={q} onChange={e => setQ(e.target.value)} placeholder="搜索文章..."
                       className="w-full pl-9 pr-8 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:text-white transition-all"/>
                {q && (
                  <button onClick={() => setQ('')}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                    <X className="w-3.5 h-3.5"/>
                  </button>
                )}
              </div>
              {/* View Toggle */}
              <div
                className="flex items-center bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-0.5">
                <button onClick={() => setViewMode('list')}
                        className={`p-1.5 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}>
                  <LayoutList className="w-4 h-4"/>
                </button>
                <button onClick={() => setViewMode('grid')}
                        className={`p-1.5 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}>
                  <Grid className="w-4 h-4"/>
                </button>
              </div>
            </div>
          </div>

          {/* ── Content ── */}
          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.div key="skeleton" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}>
                <ListSkeleton viewMode={viewMode}/>
              </motion.div>
            ) : articles.length === 0 ? (
              <motion.div key="empty" variants={fadeUp} initial="hidden" animate="show" exit={{opacity: 0}}
                          className="bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm rounded-2xl border border-gray-100 dark:border-gray-800 p-16 text-center">
                <div
                  className="w-20 h-20 mx-auto mb-6 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                  <PenSquare className="w-10 h-10 text-blue-300 dark:text-blue-600"/>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {debouncedQ ? '没有找到匹配的文章' : '还没有文章'}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                  {debouncedQ ? '尝试使用不同的关键词搜索' : '开始你的创作之旅，写下第一篇文章吧'}
                </p>
                {!debouncedQ && (
                  <a href="/my/posts/create"
                     className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors">
                    <Plus className="w-4 h-4"/>开始写作
                  </a>
                )}
              </motion.div>
            ) : viewMode === 'grid' ? (
              <motion.div key="grid" variants={stagger} initial="hidden" animate="show"
                          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {articles.map(a => (
                  <ArticleGridCard key={a.id} article={a}
                                   onDelete={() => handleDelete(a.id)}
                                   onDuplicate={() => handleCopyLink(a.slug)}
                                   onPassword={() => setPwdArticle(a)}/>
                ))}
              </motion.div>
            ) : (
              <motion.div key="list" variants={stagger} initial="hidden" animate="show"
                          className="space-y-3">
                {articles.map((a, i) => (
                  <ArticleListItem key={a.id} article={a} index={i}
                                   onDelete={() => handleDelete(a.id)}
                                   onDuplicate={() => handleCopyLink(a.slug)}
                                   onPassword={() => setPwdArticle(a)}/>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Pagination ── */}
          {pages > 1 && (
            <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.3}}
                        className="flex items-center justify-between mt-8 pt-6 border-t border-gray-100 dark:border-gray-800">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                共 {total} 篇，第 {page} / {pages} 页
              </p>
              <div className="flex items-center gap-1.5">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                        className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                  <ChevronLeft className="w-4 h-4"/>
                </button>
                {Array.from({length: Math.min(pages, 7)}, (_, i) => {
                  let p: number;
                  if (pages <= 7) {
                    p = i + 1;
                  } else if (page <= 4) {
                    p = i + 1;
                  } else if (page >= pages - 3) {
                    p = pages - 6 + i;
                  } else {
                    p = page - 3 + i;
                  }
                  return (
                    <button key={p} onClick={() => setPage(p)}
                            className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                              p === page ? 'bg-blue-600 text-white shadow-sm' : 'border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                            }`}>{p}</button>
                  );
                })}
                <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page >= pages}
                        className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                  <ChevronRight className="w-4 h-4"/>
                </button>
              </div>
            </motion.div>
          )}

          {/* ── Fetching indicator ── */}
          {isFetching && !isLoading && (
            <div className="fixed bottom-6 right-6 px-3 py-1.5 bg-blue-600 text-white text-xs rounded-full shadow-lg">
              更新中...
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function MyPostsPage() {
  return <AuthGuard><QueryProvider><MyPostsInner/></QueryProvider></AuthGuard>;
}
