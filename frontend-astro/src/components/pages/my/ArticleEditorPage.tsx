'use client';

import React, {useCallback, useEffect, useMemo, useState, useRef} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';
import {apiClient, CategoryService} from '@/lib/api';
import type {Category} from '@/lib/api/base-types';
import {Save, ArrowLeft, X} from 'lucide-react';
import {QueryProvider} from '@/components/QueryProvider';

// Lazy-loaded editor (avoids loading Tiptap in main chunk)
const RichEditor = React.lazy(() => import('@/components/editor/RichEditor'));

const DRAFT_KEY = 'fastblog_draft';

/* ========== Utils ========== */
const slugify = (s: string) => s.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-').replace(/^-|-$/g, '').slice(0, 200);

const loadDraft = () => {
  try { const d = localStorage.getItem(DRAFT_KEY); return d ? JSON.parse(d) : null; } catch { return null; }
};
const saveDraft = (data: any) => {
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify({...data, _savedAt: Date.now()})); } catch {}
};
const clearDraft = () => { try { localStorage.removeItem(DRAFT_KEY); } catch {} };

/* ========== Schema ========== */
const schema = z.object({
  title: z.string().min(1, '标题不能为空').max(200),
  slug: z.string().optional(),
  excerpt: z.string().max(500).optional(),
  content: z.string().optional(),
  cover_image: z.string().optional(),
  category_id: z.coerce.number().optional(),
  tags: z.string().optional(),
  status: z.union([z.literal(0), z.literal(1)]).default(0),
  hidden: z.boolean().default(false),
  is_vip_only: z.boolean().default(false),
});
type FormData = z.infer<typeof schema>;

interface Props { mode: 'create' | 'edit'; }

/* ========== Tags Input Sub-component ========== */
const TagsInput: React.FC<{value: string; onChange: (v: string) => void}> = ({value, onChange}) => {
  const tags = useMemo(() => value ? value.split(',').map(t => t.trim()).filter(Boolean) : [], [value]);
  const [input, setInput] = useState('');
  const addTag = (t: string) => { if (t && !tags.includes(t)) onChange([...tags, t].join(', ')); setInput(''); };
  const removeTag = (t: string) => onChange(tags.filter(x => x !== t).join(', '));
  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 min-h-[42px] focus-within:ring-2 focus-within:ring-blue-500">
      {tags.map(t => (
        <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded-full">
          {t}<button type="button" onClick={() => removeTag(t)} className="hover:text-red-500"><X className="w-3 h-3"/></button>
        </span>
      ))}
      <input type="text" value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(input); } }}
        placeholder={tags.length ? '' : '输入标签后回车...'}
        className="flex-1 min-w-[80px] bg-transparent border-none outline-none text-sm dark:text-white placeholder-gray-400" />
    </div>
  );
};

/* ========== Cover Image ========== */
const CoverInput: React.FC<{value: string; onChange: (v: string) => void}> = ({value, onChange}) => (
  <div>
    <label className="block text-sm text-gray-500 mb-1">封面图</label>
    {value ? (
      <div className="relative rounded-lg overflow-hidden mb-2">
        <img src={value} alt="cover" className="w-full h-32 object-cover" onError={e => {(e.target as HTMLImageElement).style.display='none'}} />
        <button type="button" onClick={() => onChange('')} className="absolute top-1 right-1 p-1 bg-black/50 text-white rounded-full hover:bg-black/70"><X className="w-3.5 h-3.5"/></button>
      </div>
    ) : null}
    <div className="flex gap-2">
      <input type="url" value={value} onChange={e => onChange(e.target.value)} placeholder="粘贴图片 URL..." className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white" />
    </div>
  </div>
);

/* ========== Main Component ========== */
const ArticleEditorPageInner: React.FC<Props> = ({mode}) => {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [autoSaveTimer, setAutoSaveTimer] = useState<NodeJS.Timeout | null>(null);
  const [lastSaved, setLastSaved] = useState<number | null>(null);
  const draftLoaded = useRef(false);

  const articleId = useMemo(() => {
    if (mode === 'edit' && typeof window !== 'undefined') return new URLSearchParams(window.location.search).get('id');
    return null;
  }, [mode]);

  const {register, handleSubmit, reset, watch, setValue, getValues, formState: {errors}} = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {status: 0, hidden: false, is_vip_only: false, tags: ''},
  });

  const title = watch('title');
  const coverImage = watch('cover_image');

  // Auto-generate slug from title
  useEffect(() => {
    const currentSlug = getValues('slug');
    if (title && !currentSlug && mode === 'create') {
      setValue('slug', slugify(title));
    }
  }, [title, mode, getValues, setValue]);

  // Draft auto-save (every 30s)
  useEffect(() => {
    if (mode !== 'create') return;
    const t = setInterval(() => {
      const data = getValues();
      if (data.title || content) {
        saveDraft({...data, content});
        setLastSaved(Date.now());
      }
    }, 30000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Load draft for create mode
  const [content, setContent] = useState('');
  useEffect(() => {
    if (mode === 'create' && !draftLoaded.current) {
      draftLoaded.current = true;
      const draft = loadDraft();
      if (draft && draft.title) {
        if (confirm('检测到未保存的草稿，是否恢复？')) {
          reset({...draft, status: 0});
          if (draft.content) setContent(draft.content);
        } else clearDraft();
      }
    }
  }, [mode, reset]);

  // Load categories
  const {data: categories} = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await CategoryService.getCategories({per_page: 100});
      return res.success && res.data ? (res.data.categories || []) : [];
    }, staleTime: 300_000,
  });

  // Load article for edit
  const {isLoading: loadingArticle} = useQuery({
    queryKey: ['article-edit', articleId],
    enabled: mode === 'edit' && !!articleId,
    queryFn: async () => {
      const res = await apiClient.get<any>(`/articles/edit/${articleId}`);
      if (res.success && res.data) {
        const d = res.data;
        reset({
          title: d.article?.title || d.title || '',
          slug: d.article?.slug || '',
          excerpt: d.article?.excerpt || d.excerpt || '',
          category_id: d.article?.category_id || undefined,
          tags: (d.article?.tags || []).join(', '),
          status: d.article?.status ?? 0,
          hidden: d.article?.hidden || false,
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
      if (mode === 'create') return apiClient.request('/articles', {method: 'POST', body: fd});
      return apiClient.request(`/articles/${articleId}`, {method: 'PUT', body: fd});
    },
    onSuccess: (res) => {
      if (res.success) { qc.invalidateQueries({queryKey: ['my-posts']}); clearDraft(); setTimeout(() => window.location.href = '/my/posts', 500); }
    },
  });

  const submit = async (data: FormData) => { setSaving(true); await submitMut.mutateAsync(data); setSaving(false); };
  const publish = () => { setValue('status', 1 as any); handleSubmit(submit)(); };
  const draft = () => { setValue('status', 0 as any); handleSubmit(submit)(); };

  if (mode === 'edit' && loadingArticle) {
    return <div className="min-h-screen pt-24 flex items-center justify-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"/></div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <a href="/my/posts" className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><ArrowLeft className="w-5 h-5"/></a>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{mode === 'create' ? '创建文章' : '编辑文章'}</h1>
            {lastSaved && <span className="text-xs text-gray-400">草稿已自动保存</span>}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={draft} disabled={saving} className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <Save className="w-4 h-4 inline mr-1.5"/>{saving ? '保存中...' : '存草稿'}
            </button>
            <button onClick={publish} disabled={saving} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
              {mode === 'create' ? '发布' : '更新'}
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit(submit)} className="space-y-6">
          {/* Title */}
          <input {...register('title')} placeholder="文章标题"
            className="w-full text-3xl font-bold px-0 py-2 bg-transparent border-none outline-none focus:ring-0 dark:text-white placeholder-gray-300 dark:placeholder-gray-600" />
          {errors.title && <p className="text-red-500 text-sm -mt-4">{errors.title.message}</p>}

          {/* Editor */}
          <React.Suspense fallback={<div className="h-[400px] bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse" />}>
            <RichEditor value={content} onChange={setContent} />
          </React.Suspense>

          {/* Meta panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
                <h3 className="font-semibold text-gray-900 dark:text-white">文章信息</h3>
                <div><label className="block text-sm text-gray-500 mb-1">摘要</label>
                  <textarea {...register('excerpt')} rows={3} placeholder="文章摘要..." className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/></div>
                <CoverInput value={coverImage || ''} onChange={v => setValue('cover_image', v)} />
                <div><label className="block text-sm text-gray-500 mb-1">标签</label>
                  <TagsInput value={watch('tags') || ''} onChange={v => setValue('tags', v)} /></div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
                <h3 className="font-semibold text-gray-900 dark:text-white">设置</h3>
                <div><label className="block text-sm text-gray-500 mb-1">分类</label>
                  <select {...register('category_id')} className="w-full px-3 py-2.5 border rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
                    <option value="">选择分类</option>
                    {categories?.map((c: Category) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select></div>
                <div><label className="block text-sm text-gray-500 mb-1">Slug</label>
                  <input {...register('slug')} placeholder="自动生成" className="w-full px-3 py-2.5 border rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
                <label className="flex items-center gap-3 cursor-pointer"><input type="checkbox" {...register('hidden')} className="h-4 w-4 text-blue-600 rounded"/><span className="text-sm text-gray-700 dark:text-gray-300">隐藏文章</span></label>
                <label className="flex items-center gap-3 cursor-pointer"><input type="checkbox" {...register('is_vip_only')} className="h-4 w-4 text-blue-600 rounded"/><span className="text-sm text-gray-700 dark:text-gray-300">仅 VIP</span></label>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

const ArticleEditorPage: React.FC<Props> = (props) => (
  <QueryProvider><ArticleEditorPageInner {...props} /></QueryProvider>
);
export default ArticleEditorPage;
