'use client';

import React, {useEffect, useMemo, useState, useRef} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';
import {apiClient, CategoryService} from '@/lib/api';
import type {Category} from '@/lib/api/base-types';
import {Save, ArrowLeft, X, History, Settings2, Eye, EyeOff, Tag, FolderTree, Image, FileText, Hash} from 'lucide-react';
import {QueryProvider} from '@/components/QueryProvider';
import RevisionsSidebar from '@/components/editor/RevisionsSidebar';

const RichEditor = React.lazy(() => import('@/components/editor/RichEditor'));

const DRAFT_KEY = 'fastblog_draft';
const slugify = (s: string) => s.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-').replace(/^-|-$/g, '').slice(0, 200);
const loadDraft = () => { try { const d = localStorage.getItem(DRAFT_KEY); return d ? JSON.parse(d) : null; } catch { return null; } };
const saveDraft = (data: any) => { try { localStorage.setItem(DRAFT_KEY, JSON.stringify({...data, _savedAt: Date.now()})); } catch {} };
const clearDraft = () => { try { localStorage.removeItem(DRAFT_KEY); } catch {} };

const schema = z.object({
  title: z.string().min(1, '标题不能为空').max(200), slug: z.string().optional(),
  excerpt: z.string().max(500).optional(), cover_image: z.string().optional(),
  category_id: z.coerce.number().optional(), tags: z.string().optional(),
  status: z.union([z.literal(0), z.literal(1)]).default(0),
  hidden: z.boolean().default(false), is_vip_only: z.boolean().default(false),
});
type FormData = z.infer<typeof schema>;
interface Props { mode: 'create' | 'edit'; }

/* Sidebar section helper */
const Section: React.FC<{icon: any; title: string; children: React.ReactNode}> = ({icon: Icon, title, children}) => (
  <div className="border-b border-gray-100 dark:border-gray-800 pb-4 mb-4 last:border-0 last:mb-0 last:pb-0">
    <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3"><Icon className="w-3.5 h-3.5"/>{title}</div>
    {children}
  </div>
);

const ArticleEditorPageInner: React.FC<Props> = ({mode}) => {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<number | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showRevisions, setShowRevisions] = useState(false);
  const [content, setContent] = useState('');
  const draftLoaded = useRef(false);

  const articleId = useMemo(() => {
    if (mode === 'edit' && typeof window !== 'undefined') return new URLSearchParams(window.location.search).get('id');
    return null;
  }, [mode]);

  const {register, handleSubmit, reset, watch, setValue, getValues, formState: {errors}} = useForm<FormData>({
    resolver: zodResolver(schema), defaultValues: {status: 0, hidden: false, is_vip_only: false, tags: ''},
  });

  const title = watch('title');

  // Auto-slug
  useEffect(() => {
    const cur = getValues('slug');
    if (title && !cur && mode === 'create') setValue('slug', slugify(title));
  }, [title, mode, getValues, setValue]);

  // Auto-save draft
  useEffect(() => {
    if (mode !== 'create') return;
    const t = setInterval(() => {
      const d = getValues();
      if (d.title || content) { saveDraft({...d, content}); setLastSaved(Date.now()); }
    }, 30000);
    return () => clearInterval(t);
  }, [mode, getValues, content]);

  // Load draft
  useEffect(() => {
    if (mode === 'create' && !draftLoaded.current) {
      draftLoaded.current = true;
      const draft = loadDraft();
      if (draft?.title && confirm('检测到未保存的草稿，是否恢复？')) {
        reset({...draft, status: 0});
        if (draft.content) setContent(draft.content);
      } else clearDraft();
    }
  }, [mode, reset]);

  const {data: categories} = useQuery({
    queryKey: ['categories'], staleTime: 300_000,
    queryFn: async () => {
      const res = await CategoryService.getCategories({per_page: 100});
      return res.success && res.data ? (res.data.categories || []) : [];
    },
  });

  const {isLoading: loadingArticle} = useQuery({
    queryKey: ['article-edit', articleId], enabled: mode === 'edit' && !!articleId,
    queryFn: async () => {
      const res = await apiClient.get<any>(`/articles/edit/${articleId}`);
      if (res.success && res.data) {
        const d = res.data;
        reset({
          title: d.article?.title || d.title || '', slug: d.article?.slug || '',
          excerpt: d.article?.excerpt || d.excerpt || '',
          category_id: d.article?.category_id || undefined,
          tags: (d.article?.tags || []).join(', '),
          status: d.article?.status ?? 0, hidden: d.article?.hidden || false,
          is_vip_only: d.article?.is_vip_only || false,
        });
        setContent(d.content || d.article?.content || '');
      }
      return res;
    },
  });

  const submitMut = useMutation({
    mutationFn: async (data: FormData) => {
      const fd = new FormData();
      Object.entries(data).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') fd.append(k, String(v)); });
      fd.set('content', content);
      fd.set('status', String(data.status ?? 0));
      return mode === 'create'
        ? apiClient.request('/articles', {method: 'POST', body: fd})
        : apiClient.request(`/articles/${articleId}`, {method: 'PUT', body: fd});
    },
    onSuccess: (res) => {
      if (res.success) { qc.invalidateQueries({queryKey: ['my-posts']}); clearDraft(); setTimeout(() => window.location.href = '/my/posts', 500); }
    },
  });

  const submit = async (data: FormData) => { setSaving(true); await submitMut.mutateAsync(data); setSaving(false); };
  const publish = () => { setValue('status', 1 as any); handleSubmit(submit)(); };
  const draft = () => { setValue('status', 0 as any); handleSubmit(submit)(); };

  if (mode === 'edit' && loadingArticle) {
    return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"/></div>;
  }

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-gray-950 overflow-hidden">
      {/* ===== Top Bar ===== */}
      <header className="flex items-center justify-between px-4 lg:px-6 h-14 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex-shrink-0">
        <div className="flex items-center gap-3">
          <a href="/my/posts" className="p-2 -ml-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-300"/>
          </a>
          <span className="text-sm font-medium text-gray-500 dark:text-gray-400 hidden sm:block">/ 文章 / {mode === 'create' ? '新建' : '编辑'}</span>
          {lastSaved && <span className="text-xs text-gray-400 hidden sm:block">草稿已自动保存</span>}
        </div>
        <div className="flex items-center gap-2">
          {mode === 'edit' && articleId && (
            <button onClick={() => setShowRevisions(true)} className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex items-center gap-1.5">
              <History className="w-4 h-4"/><span className="hidden sm:inline">版本</span>
            </button>
          )}
          <button onClick={() => setShowSidebar(!showSidebar)} className={`p-1.5 rounded-lg border transition-colors ${showSidebar ? 'bg-blue-50 border-blue-200 text-blue-600 dark:bg-blue-900/20 dark:border-blue-800' : 'border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
            <Settings2 className="w-4 h-4"/>
          </button>
          <button onClick={draft} disabled={saving} className="px-4 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50">
            <Save className="w-4 h-4 inline mr-1 -mt-0.5"/>{saving ? '保存中...' : '草稿'}
          </button>
          <button onClick={publish} disabled={saving} className="px-5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50">
            {mode === 'create' ? '发布' : '更新'}
          </button>
        </div>
      </header>

      {/* ===== Editor Area ===== */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main editor */}
        <main className={`flex-1 overflow-y-auto ${showSidebar ? '' : 'max-w-3xl mx-auto'}`}>
          <div className="max-w-3xl mx-auto px-6 lg:px-10 py-8">
            <form onSubmit={handleSubmit(submit)}>
              {/* Title (inline with editor, like WordPress) */}
              <input {...register('title')} placeholder="添加标题"
                className="w-full text-3xl lg:text-4xl font-bold mb-6 px-0 py-2 bg-transparent border-none outline-none focus:ring-0 dark:text-white placeholder-gray-300 dark:placeholder-gray-600" />
              {errors.title && <p className="text-red-500 text-sm -mt-4 mb-4">{errors.title.message}</p>}

              {/* Tiptap Editor */}
              <React.Suspense fallback={<div className="h-[60vh] bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse" />}>
                <RichEditor value={content} onChange={setContent} placeholder="开始写作..." />
              </React.Suspense>
            </form>
          </div>
        </main>

        {/* ===== Settings Sidebar (WordPress-style) ===== */}
        {showSidebar && (
          <aside className="w-72 lg:w-80 border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 overflow-y-auto flex-shrink-0 p-5 space-y-1">
            <Section icon={Eye} title="发布设置">
              <div className="space-y-2">
                <label className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">公开可见</span>
                  <input type="checkbox" {...register('hidden')} className="toggle" />
                </label>
                <label className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">仅 VIP 可读</span>
                  <input type="checkbox" {...register('is_vip_only')} className="toggle" />
                </label>
              </div>
            </Section>

            <Section icon={FolderTree} title="分类">
              <select {...register('category_id')} className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
                <option value="">选择分类</option>
                {categories?.map((c: Category) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Section>

            <Section icon={Hash} title="标签">
              <input {...register('tags')} placeholder="输入标签，逗号分隔" className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
            </Section>

            <Section icon={Image} title="封面图">
              <div className="space-y-2">
                {watch('cover_image') && (
                  <div className="relative rounded-lg overflow-hidden">
                    <img src={watch('cover_image')} alt="" className="w-full h-24 object-cover" onError={e => {(e.target as HTMLImageElement).style.display='none'}} />
                    <button type="button" onClick={() => setValue('cover_image', '')} className="absolute top-1 right-1 p-1 bg-black/50 text-white rounded-full hover:bg-black/70"><X className="w-3 h-3"/></button>
                  </div>
                )}
                <input type="url" {...register('cover_image')} placeholder="图片 URL..." className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
              </div>
            </Section>

            <Section icon={FileText} title="摘要">
              <textarea {...register('excerpt')} rows={3} placeholder="文章摘要..." className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none"/>
            </Section>

            <Section icon={Hash} title="Slug">
              <input {...register('slug')} placeholder="自动生成" className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 font-mono text-xs"/>
            </Section>
          </aside>
        )}
      </div>

      {/* Revisions overlay */}
      {mode === 'edit' && articleId && (
        <RevisionsSidebar articleId={articleId} open={showRevisions} onClose={() => setShowRevisions(false)}
          onRestore={(c, t, e) => { setContent(c); setValue('title', t); setValue('excerpt', e); setShowRevisions(false); }} />
      )}
    </div>
  );
};

const ArticleEditorPage: React.FC<Props> = (props) => (
  <QueryProvider><ArticleEditorPageInner {...props} /></QueryProvider>
);
export default ArticleEditorPage;
