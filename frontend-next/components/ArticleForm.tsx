'use client';

import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useRouter} from 'next/navigation';
import dynamic from 'next/dynamic';
import {Category} from "@/lib/api";
import {OptimizedInput, OptimizedTextarea} from '@/components/ui/optimized-input';
import CoverImageUploader from '@/components/CoverImageUploader';
import {DraftService} from '@/lib/draft-service';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';
import {useToast} from '@/hooks/use-toast';
import {useHotkeys} from '@/hooks/useHotkeys';
import ArticleRevisionsSidebar from '@/components/ArticleRevisionsSidebar';

// 动态导入优化后的组件
const UniversalEditor = dynamic(
    () => import('@/components/editor/UniversalEditor'),
    {
      ssr: false,
      loading: () => (
          <div className="h-96 animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg"/>
      )
    }
);

const TagsInput = dynamic(
    () => import('./TagsInput'),
    {ssr: false}
);

interface ArticleFormData {
  id?: number;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  cover_image: string;
  tags: string[];
  status: number;
  hidden: boolean;
  is_vip_only: boolean;
  required_vip_level: number;
  article_ad: string;
  is_featured: boolean;
  category_id: number | null;
  scheduled_publish_at: string;
}

interface ArticleFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<ArticleFormData>;
  categories: Category[];
  onSubmit: (data: ArticleFormData, createRevision?: boolean) => Promise<{
    success: boolean;
    error?: string;
    data?: any
  }>;
  onCancel: () => void;
  onViewRevisions?: () => void; // 新增：查看修订历史的回调
  articleId?: number | null; // 新增：文章ID，用于修订历史
  isLoading?: boolean;
}

const ArticleForm: React.FC<ArticleFormProps> = ({
                                                   mode,
                                                   initialData = {},
                                                   categories,
                                                   onSubmit,
                                                   onCancel,
                                                   onViewRevisions,
                                                   articleId = null,
                                                   isLoading = false
                                                 }) => {
  const router = useRouter();
  const {toast} = useToast();

  // ✅ 移除生产环境的 console.log，避免性能问题
  // if (process.env.NODE_ENV === 'development') {
  //   console.log('ArticleForm rendered - mode:', mode, 'articleId:', articleId);
  // }

  // 使用useMemo初始化表单数据，避免不必要的重新计算
  const initialFormState = useMemo(() => ({
    title: '',
    slug: '',
    excerpt: '',
    content: '',
    cover_image: '',
    tags: [],
    status: 0,
    hidden: false,
    is_vip_only: false,
    required_vip_level: 0,
    article_ad: '',
    is_featured: false,
    category_id: null,
    scheduled_publish_at: '',
    ...initialData
  }), [initialData]);

  const [form, setForm] = useState<ArticleFormData>(initialFormState);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [coverValid, setCoverValid] = useState<boolean>(true);

  // 保存确认对话框状态
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);
  const [createRevision, setCreateRevision] = useState(true); // 默认勾选创建修订

  // 自动保存状态
  const [autoSaveStatus, setAutoSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedTime, setLastSavedTime] = useState<Date | null>(null);
  const autoSaveTimerRef = React.useRef<NodeJS.Timeout | null>(null);
  const lastContentRef = React.useRef<string>('');

  // 修订历史侧边栏状态
  const [showRevisionsSidebar, setShowRevisionsSidebar] = useState(false);

  // Ctrl+S 快捷键保存
  useHotkeys({
    'ctrl+s': (e) => {
      e.preventDefault();
      // 如果正在提交或显示确认对话框，不重复触发
      if (!isSubmitting && !showSaveConfirm) {
        setShowSaveConfirm(true);
      }
    }
  });

  // 自动保存草稿函数 - 保存到本地
  const autoSaveDraft = useCallback(async () => {
    if (mode !== 'edit' || !form.id) return;

    // 检查内容是否有变化
    const currentContent = JSON.stringify({
      title: form.title,
      excerpt: form.excerpt,
      content: form.content,
      cover_image: form.cover_image,
      tags: form.tags,
      category_id: form.category_id
    });

    if (currentContent === lastContentRef.current) {
      return; // 内容没有变化，不需要保存
    }

    try {
      setAutoSaveStatus('saving');

      // 保存草稿到本地
      DraftService.saveDraft(form.id, {
        title: form.title,
        excerpt: form.excerpt,
        content: form.content,
        cover_image: form.cover_image,
        tags: form.tags,
        category_id: form.category_id,
        status: form.status,
        hidden: form.hidden,
        is_vip_only: form.is_vip_only,
        required_vip_level: form.required_vip_level,
        is_featured: form.is_featured,
        autoSave: true
      });

      setAutoSaveStatus('saved');
      setLastSavedTime(new Date());
      lastContentRef.current = currentContent;

      // 3秒后恢复为idle状态
      setTimeout(() => {
        setAutoSaveStatus('idle');
      }, 3000);

      console.log('✅ 草稿已自动保存到本地');
    } catch (error) {
      setAutoSaveStatus('error');
      console.error('❌ 自动保存出错:', error);
    }
  }, [form, mode]);

  // 设置自动保存定时器
  useEffect(() => {
    if (mode === 'edit' && form.id) {
      // 每30秒自动保存一次到本地
      autoSaveTimerRef.current = setInterval(() => {
        autoSaveDraft();
      }, 30000);

      // 清理定时器
      return () => {
        if (autoSaveTimerRef.current) {
          clearInterval(autoSaveTimerRef.current);
        }
      };
    }
  }, [mode, form.id]); // 移除 autoSaveDraft 依赖，避免不必要的重新渲染

  // 预览模式状态
  const [showPreview, setShowPreview] = useState(false);

  // 基于标题自动生成slug - 使用useCallback优化
  const generateSlug = useCallback((title: string) => {
    return title
        .toLowerCase()
        .trim()
        .replace(/[\s\u3000]+/g, '-')
        .replace(/[^\w-]+/g, '-')
        .replace(/^-+|-+$/g, '');
  }, []);

  useEffect(() => {
    if (mode === 'create' && !form.slug && form.title) {
      const newSlug = generateSlug(form.title);
      setForm(prev => ({...prev, slug: newSlug}));
    }
  }, [form.title, mode]); // 移除 form.slug 和 generateSlug 依赖，避免不必要的重新渲染

  // 使用useCallback优化输入处理函数
  const handleInputChange = useCallback((field: keyof ArticleFormData, value: string | number | boolean | string[] | null) => {
    setForm(prev => ({...prev, [field]: value}));
  }, []);

  // 为内容字段单独优化的处理函数
  const handleContentChange = useCallback((value: string) => {
    setForm(prev => ({...prev, content: value}));

    // 触发自定义事件，通知父组件内容已更新
    const event = new CustomEvent('editorContentChanged', {
      detail: {content: value}
    });
    window.dispatchEvent(event);
  }, []);

  // 优化表单提交 - 使用useCallback
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    // 显示确认对话框
    setShowSaveConfirm(true);
  }, []); // 移除所有依赖，避免不必要的重新渲染

  // 确认保存
  const handleConfirmSave = useCallback(async () => {
    setError(null);
    setIsSubmitting(true);
    setShowSaveConfirm(false);

    try {
      const result = await onSubmit(form, createRevision);

      if (result.success) {
        // 检查是否因为去重而跳过
          if ((result.data as any)?.skipped) {
          // 显示提示信息
          toast({
            title: '✅ 已跳过',
              description: (result.data as any).message || '内容未发生变化，已跳过创建修订版本',
            variant: 'default'
          });
          } else {
            // 只有在实际保存成功时才显示提示
            toast({
              title: '✅ 保存成功',
              description: mode === 'create' ? '文章已创建' : '文章已更新',
              variant: 'default'
            });
        }
        
        // 如果是创建模式，且返回了 article_id，则跳转到编辑页面
        if (mode === 'create' && result.data?.article_id) {
          router.push(`/my/posts/edit?id=${result.data.article_id}`);
        }
        // 注意：移除了 router.refresh()，避免无限刷新循环
        // 编辑模式下不需要刷新页面，用户可以看到当前编辑的内容

        // 提交成功后删除本地草稿
        if (form.id) {
          DraftService.deleteDraft(form.id);
        }
      } else {
        setError(result.error || '提交失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setIsSubmitting(false);
    }
  }, [form, onSubmit, router, mode, createRevision, toast]); // 添加 toast 依赖

  // 取消保存
  const handleCancelSave = useCallback(() => {
    setShowSaveConfirm(false);
  }, []);

  return (
      <>
        {/* 顶部工具栏 - 固定定位 */}
        <div
            className="sticky top-0 z-40 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800 pt-18">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-4">
                <button
                    onClick={onCancel}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    title="返回"
                >
                  <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor"
                       viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/>
                  </svg>
                </button>
                <div className="h-6 w-px bg-gray-200 dark:bg-gray-700"/>
              <div>
                <h1 className="text-sm font-semibold text-gray-900 dark:text-white">
                  {mode === 'create' ? '新建文章' : '编辑文章'}
                </h1>
                {mode === 'edit' && form.id && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">ID: {form.id}</p>
                )}
              </div>
              </div>

              <div className="flex items-center gap-3">
                {/* 自动保存状态 */}
                {mode === 'edit' && (
                    <div className="hidden sm:flex items-center gap-2 text-sm">
                      {autoSaveStatus === 'saving' && (
                          <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      保存中...
                    </span>
                      )}
                      {autoSaveStatus === 'saved' && lastSavedTime && (
                          <span className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                      </svg>
                      已保存 {lastSavedTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}
                    </span>
                      )}
                    </div>
                )}

                {/* 修订历史按钮 */}
                {mode === 'edit' && articleId ? (
                    <button
                        type="button"
                        onClick={() => setShowRevisionsSidebar(true)}
                        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
                        title="查看修订历史"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      <span className="hidden sm:inline">历史版本</span>
                    </button>
                ) : null}

                {/* 保存按钮 */}
                <button
                    type="submit"
                    disabled={isSubmitting || isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                >
                  {isSubmitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path className="opacity-75" fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        {mode === 'create' ? '创建中...' : '保存中...'}
                      </>
                  ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                        </svg>
                        {mode === 'create' ? '发布文章' : '保存更改'}
                      </>
                )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 主内容区域 */}
        <div className="min-h-screen bg-white dark:bg-gray-950">
          <form onSubmit={handleSubmit} className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-0">
              {/* 左侧主要内容区 - 占据更多空间 */}
              <div className="lg:col-span-9 xl:col-span-10">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
                  {/* 标题输入 - 大字号，无框设计 */}
                  <div className="mb-6">
                    <OptimizedInput
                        type="text"
                        value={form.title}
                        onChange={(e) => handleInputChange('title', e.target.value)}
                        className="w-full text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white placeholder-gray-300 dark:placeholder-gray-700 border-none bg-transparent focus:outline-none focus:ring-0 p-0"
                        placeholder="文章标题"
                        required
                    />
                  </div>

                  {/* Slug 输入 - 简洁的内联样式 */}
                  <div className="mb-8 flex items-center gap-2 text-sm">
                    <span className="text-gray-400 dark:text-gray-600">/</span>
                    <OptimizedInput
                        type="text"
                        value={form.slug}
                        onChange={(e) => handleInputChange('slug', e.target.value)}
                        className="flex-1 text-gray-600 dark:text-gray-400 placeholder-gray-300 dark:placeholder-gray-700 border-none bg-transparent focus:outline-none focus:ring-0 p-0"
                        placeholder="article-url-slug"
                    />
                  </div>

                  {/* 摘要 - 可选 */}
                  {form.excerpt && (
                      <div className="mb-8">
                        <OptimizedTextarea
                            value={form.excerpt}
                            onChange={(e) => handleInputChange('excerpt', e.target.value)}
                            rows={2}
                            className="w-full text-base text-gray-600 dark:text-gray-400 placeholder-gray-300 dark:placeholder-gray-700 border-none bg-transparent focus:outline-none focus:ring-0 p-0 resize-none"
                            placeholder="添加文章摘要（可选）..."
                        />
                  </div>
                  )}

                  {/* 封面图预览 - 如果有的话 */}
                  {form.cover_image && (
                      <div className="mb-8 relative group">
                        <img
                            src={form.cover_image}
                            alt="封面"
                            className="w-full h-64 object-cover rounded-xl"
                        />
                        <button
                            type="button"
                            onClick={() => handleInputChange('cover_image', '')}
                            className="absolute top-2 right-2 p-2 bg-black/50 hover:bg-black/70 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                  d="M6 18L18 6M6 6l12 12"/>
                          </svg>
                        </button>
                      </div>
                  )}

                  {/* 内容编辑器 - 全宽无边框 */}
                  <div className="mb-8">
                    <UniversalEditor
                        value={form.content}
                        onChange={handleContentChange}
                        defaultMode="markdown"
                        allowSwitch={true}
                        showPreview={showPreview}
                        onTogglePreview={() => setShowPreview(!showPreview)}
                        minHeight="600px"
                        maxHeight="none"
                        placeholder="开始写作..."
                    />
                  </div>
                </div>
              </div>

              {/* 右侧设置面板 - 可滚动 */}
              <div
                  className="lg:col-span-3 xl:col-span-2 border-t lg:border-t-0 lg:border-l border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                <div className="sticky top-16 max-h-[calc(100vh-4rem)] overflow-y-auto p-6 space-y-6">
                  {/* 发布设置 */}
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                      发布设置
                  </h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                          状态
                        </label>
                        <select
                            value={form.status}
                            onChange={(e) => handleInputChange('status', Number(e.target.value))}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                        >
                          <option value={0}>草稿</option>
                          <option value={1}>已发布</option>
                          <option value={-1}>已删除</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                          分类
                        </label>
                        <select
                            value={form.category_id ?? ''}
                            onChange={(e) => handleInputChange('category_id', e.target.value ? Number(e.target.value) : null)}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                        >
                          <option value="">未分类</option>
                          {categories.map(category => (
                              <option key={category.id} value={category.id}>
                                {category.name}
                              </option>
                          ))}
                        </select>
                      </div>
                  </div>
                </div>

                  {/* 可见性设置 */}
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                      可见性
                  </h3>
                    <div className="space-y-2">
                      <label className="flex items-center justify-between cursor-pointer group">
                      <span
                          className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                        隐藏文章
                      </span>
                        <input
                            type="checkbox"
                            checked={form.hidden}
                            onChange={(e) => handleInputChange('hidden', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer group">
                      <span
                          className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                        设为精选
                      </span>
                        <input
                            type="checkbox"
                            checked={form.is_featured}
                            onChange={(e) => handleInputChange('is_featured', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer group">
                      <span
                          className={`text-sm transition-colors ${form.hidden ? 'text-gray-400' : 'text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white'}`}>
                        VIP专属
                      </span>
                        <input
                            type="checkbox"
                            checked={form.is_vip_only}
                            onChange={(e) => handleInputChange('is_vip_only', e.target.checked)}
                            disabled={form.hidden}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300 disabled:opacity-50"
                        />
                      </label>

                      {form.is_vip_only && !form.hidden && (
                          <div className="mt-2 pl-1">
                            <select
                                value={form.required_vip_level}
                                onChange={(e) => handleInputChange('required_vip_level', Number(e.target.value))}
                                className="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                            >
                              {[0, 1, 2, 3].map(level => (
                                  <option key={level} value={level}>
                                    {level === 0 ? '无限制' : `VIP ${level}级`}
                                  </option>
                              ))}
                            </select>
                          </div>
                      )}
                    </div>
                  </div>

                  {/* 标签 */}
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                      标签
                    </h3>
                    <TagsInput
                        value={form.tags}
                        onChange={(tags) => handleInputChange('tags', tags)}
                    />
                </div>

                  {/* 高级设置（可折叠） */}
                  <details className="group">
                    <summary
                        className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors list-none flex items-center justify-between">
                      <span>高级设置</span>
                      <svg className="w-4 h-4 transform group-open:rotate-180 transition-transform" fill="none"
                           stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
                      </svg>
                    </summary>
                    <div className="mt-3 space-y-4 pt-3 border-t border-gray-200 dark:border-gray-800">
                      {/* 封面图上传 */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          封面图片
                        </label>
                        <CoverImageUploader
                            value={form.cover_image}
                            onChange={(value) => handleInputChange('cover_image', value)}
                            onValidationChange={setCoverValid}
                            placeholder="点击上传封面"
                        />
                      </div>

                      {/* 广告内容 */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                          文章广告
                        </label>
                        <OptimizedTextarea
                            value={form.article_ad}
                            onChange={(e) => handleInputChange('article_ad', e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white resize-none"
                            placeholder="HTML 广告代码..."
                        />
                      </div>
                    </div>
                  </details>
                </div>
              </div>
            </div>
          </form>
        </div>

          {/* 保存确认对话框 */}
          <Dialog open={showSaveConfirm} onOpenChange={setShowSaveConfirm}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>确认保存文章</DialogTitle>
                <DialogDescription>
                  {mode === 'create' ? '您即将创建新文章' : '您即将保存对文章的修改'}
                </DialogDescription>
              </DialogHeader>

              <div className="py-4">
                <label
                    className="flex items-start space-x-3 cursor-pointer p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <input
                      type="checkbox"
                      checked={createRevision}
                      onChange={(e) => setCreateRevision(e.target.checked)}
                      className="mt-1 w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      为本次修改创建历史修订
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      勾选后，系统将保存当前版本到修订历史，方便日后查看和回滚
                    </div>
                  </div>
                </label>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={handleCancelSave}>
                  取消
                </Button>
                <Button onClick={handleConfirmSave} disabled={isSubmitting}>
                  {isSubmitting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path className="opacity-75" fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        保存中...
                      </>
                  ) : (
                      '确认保存'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

        {/* 修订历史侧边栏 */}
        {mode === 'edit' && articleId && (
            <ArticleRevisionsSidebar
                articleId={articleId}
                isOpen={showRevisionsSidebar}
                onClose={() => setShowRevisionsSidebar(false)}
                onRollbackComplete={() => {
                  // 回滚完成后可以刷新数据或显示提示
                  toast({
                    title: '回滚成功',
                    description: '文章内容已恢复到选定版本'
                  });
                }}
            />
        )}
      </>
  );
};

export default ArticleForm;