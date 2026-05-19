'use client';

import React, {useEffect, useMemo, useRef, useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';
import {apiClient, CategoryService} from '@/lib/api';
import type {Category} from '@/lib/api/base-types';
import {Save, Eye, ArrowLeft, Tags} from 'lucide-react';
import {QueryProvider} from '@/components/QueryProvider';

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

interface Props {
  mode: 'create' | 'edit';
}

const ArticleEditorPageInner: React.FC<Props> = ({mode}) => {
  const qc = useQueryClient();
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);

  // Get article ID from URL for edit mode
  const articleId = useMemo(() => {
    if (mode === 'edit' && typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search).get('id');
    }
    return null;
  }, [mode]);

  const {register, handleSubmit, reset, watch, setValue, formState: {errors}} = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {status: 0, hidden: false, is_vip_only: false},
  });

  const {data: categories} = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await CategoryService.getCategories({per_page: 100});
      return res.success && res.data ? (res.data.categories || []) : [];
    },
  });

  // Load existing article data for edit mode
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
      fd.append('title', data.title);
      if (data.slug) fd.append('slug', data.slug);
      if (data.excerpt) fd.append('excerpt', data.excerpt);
      fd.append('content', content);
      if (data.cover_image) fd.append('cover_image', data.cover_image);
      if (data.category_id) fd.append('category_id', String(data.category_id));
      if (data.tags) fd.append('tags', data.tags);
      fd.append('status', String(data.status));
      fd.append('hidden', data.hidden ? '1' : '0');
      fd.append('is_vip_only', data.is_vip_only ? '1' : '0');

      if (mode === 'create') {
        return apiClient.request('/articles', {method: 'POST', body: fd});
      } else {
        return apiClient.request(`/articles/${articleId}`, {method: 'PUT', body: fd});
      }
    },
    onSuccess: (res) => {
      if (res.success) {
        qc.invalidateQueries({queryKey: ['my-posts']});
        setTimeout(() => window.location.href = '/my/posts', 500);
      }
    },
  });

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    await submitMut.mutateAsync(data);
    setSaving(false);
  };

  const handlePublish = () => {
    setValue('status', 1 as any);
    handleSubmit(onSubmit)();
  };

  const handleSaveDraft = () => {
    setValue('status', 0 as any);
    handleSubmit(onSubmit)();
  };

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
          </div>
          <div className="flex items-center gap-3">
            <button onClick={handleSaveDraft} disabled={saving} className="px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <Save className="w-4 h-4 inline mr-1.5"/>{saving ? '保存中...' : '存草稿'}
            </button>
            <button onClick={handlePublish} disabled={saving} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
              {mode === 'create' ? '发布' : '更新'}
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Title */}
          <div>
            <input {...register('title')} placeholder="文章标题" className="w-full text-3xl font-bold px-0 py-2 bg-transparent border-none outline-none focus:ring-0 dark:text-white placeholder-gray-300 dark:placeholder-gray-600"/>
            {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message}</p>}
          </div>

          {/* Content Editor */}
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center gap-1 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              {[
                {label: 'B', cmd: 'bold', className: 'font-bold'},
                {label: 'I', cmd: 'italic', className: 'italic'},
                {label: 'H2', cmd: 'heading', className: ''},
                {label: '「」', cmd: 'blockquote', className: ''},
                {label: '••', cmd: 'bullet-list', className: ''},
              ].map(b => (
                <button key={b.cmd} type="button" className={`px-3 py-1.5 text-sm rounded hover:bg-gray-200 dark:hover:bg-gray-700 ${b.className}`}>{b.label}</button>
              ))}
            </div>
            <textarea value={content} onChange={e => setContent(e.target.value)}
              placeholder="开始写作..." rows={20}
              className="w-full px-6 py-4 bg-transparent resize-y focus:outline-none dark:text-white font-mono text-sm leading-relaxed"/>
          </div>

          {/* Meta panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: metadata */}
            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">文章信息</h3>
                <div className="space-y-3">
                  <div><label className="block text-sm text-gray-500 mb-1">摘要</label>
                    <textarea {...register('excerpt')} rows={3} placeholder="文章摘要..." className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/></div>
                  <div><label className="block text-sm text-gray-500 mb-1">分类</label>
                    <select {...register('category_id')} className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
                      <option value="">选择分类</option>
                      {categories?.map((c: Category) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select></div>
                  <div><label className="block text-sm text-gray-500 mb-1">标签（逗号分隔）</label>
                    <input {...register('tags')} placeholder="标签1, 标签2" className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
                  <div><label className="block text-sm text-gray-500 mb-1">封面图 URL</label>
                    <input {...register('cover_image')} placeholder="https://..." className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
                </div>
              </div>
            </div>

            {/* Right: settings */}
            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">高级设置</h3>
                <div className="space-y-3">
                  <div><label className="block text-sm text-gray-500 mb-1">自定义 Slug</label>
                    <input {...register('slug')} placeholder="自动生成" className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/></div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" {...register('hidden')} className="h-4 w-4 text-blue-600 rounded"/>
                    <span className="text-sm text-gray-700 dark:text-gray-300">隐藏文章（仅通过链接访问）</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" {...register('is_vip_only')} className="h-4 w-4 text-blue-600 rounded"/>
                    <span className="text-sm text-gray-700 dark:text-gray-300">仅 VIP 可读</span>
                  </label>
                </div>
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
