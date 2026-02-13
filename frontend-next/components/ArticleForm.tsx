'use client';

import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useRouter} from 'next/navigation';
import dynamic from 'next/dynamic';
import {Category, MediaFile} from "@/lib/api";
import {OptimizedInput, OptimizedTextarea} from '@/components/ui/optimized-input';
import CoverImageUploader from '@/components/CoverImageUploader';

// 动态导入优化后的组件
const OptimizedMarkdownEditor = dynamic(
  () => import('@/components/editor/OptimizedMarkdownEditor'),
  {
    ssr: false,
    loading: () => (
      <div className="h-96 animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg" />
    )
  }
);

const TagsInput = dynamic(
  () => import('./TagsInput'),
  { ssr: false }
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
}

interface ArticleFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<ArticleFormData>;
  categories: Category[];
  onSubmit: (data: ArticleFormData) => Promise<{ success: boolean; error?: string }>;
  onCancel: () => void;
  isLoading?: boolean;
}

const ArticleForm: React.FC<ArticleFormProps> = ({
  mode,
  initialData = {},
  categories,
  onSubmit,
  onCancel,
  isLoading = false
}) => {
  const router = useRouter();
  
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
    ...initialData
  }), [initialData]);

  const [form, setForm] = useState<ArticleFormData>(initialFormState);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [coverValid, setCoverValid] = useState<boolean>(true);

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
      setForm(prev => ({ ...prev, slug: newSlug }));
    }
  }, [form.title, form.slug, mode, generateSlug]);

  // 使用useCallback优化输入处理函数
  const handleInputChange = useCallback((field: keyof ArticleFormData, value: string | number | boolean | string[] | null) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  // 为内容字段单独优化的处理函数
  const handleContentChange = useCallback((value: string) => {
    setForm(prev => ({ ...prev, content: value }));
  }, []);

  // 处理媒体文件插入到编辑器（支持单个或多个文件）
  const handleInsertMedia = useCallback((media: MediaFile | MediaFile[]) => {
    // 处理单个文件或多个文件
    const mediaFiles = Array.isArray(media) ? media : [media];
    
    // 为每个文件生成对应的Markdown格式
    const mediaMarkdowns = mediaFiles.map(singleMedia => {
      const mediaUrl = `/api/v1/media/${singleMedia.id}`;
      
      if (singleMedia.mime_type.startsWith('image/')) {
        // 图片格式：![alt](url)
        return `![${singleMedia.original_filename}](${mediaUrl})`;
      } else if (singleMedia.mime_type.startsWith('video/')) {
        // 视频格式：<video controls><source src="url" type="mime_type">您的浏览器不支持视频标签。</video>
        return `<video controls><source src="${mediaUrl}" type="${singleMedia.mime_type}">您的浏览器不支持视频标签。</video>`;
      } else if (singleMedia.mime_type.startsWith('audio/')) {
        // 音频格式：<audio controls><source src="url" type="mime_type">您的浏览器不支持音频标签。</audio>
        return `<audio controls><source src="${mediaUrl}" type="${singleMedia.mime_type}">您的浏览器不支持音频标签。</audio>`;
      } else {
        // 其他文件类型：[文件名](url)
        return `[${singleMedia.original_filename}](${mediaUrl})`;
      }
    });
    
    // 将所有Markdown内容连接，用换行分隔
    const combinedMarkdown = mediaMarkdowns.join('\n\n');
    
    // 将内容插入到现有内容末尾
    setForm(prev => ({
      ...prev,
      content: prev.content + '\n\n' + combinedMarkdown + '\n\n'
    }));
  }, []);

  // 优化表单提交 - 使用useCallback
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const result = await onSubmit(form);

      if (result.success) {
        router.refresh();
      } else {
        setError(result.error || '提交失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setIsSubmitting(false);
    }
  }, [form, onSubmit, router]);

  // 使用useMemo优化渲染函数
  const renderField = useMemo(() => (
    function renderFieldComponent(label: string, children: React.ReactNode, required = false) {
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          {children}
        </div>
      );
    }
  ), []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 头部 */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {mode === 'create' ? '创建文章' : '编辑文章'}
              </h1>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {mode === 'create' ? '填写信息创建新文章' : '修改并更新文章内容'}
              </p>
            </div>
            {mode === 'edit' && form.id && (
              <div className="text-sm text-gray-500">ID: {form.id}</div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* 左侧主要内容 */}
            <div className="lg:col-span-2 space-y-6">
              {/* 基本信息卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  基本信息
                </h3>

                <div className="space-y-6">
                  {renderField('标题',
                    <OptimizedInput
                      type="text"
                      value={form.title}
                      onChange={(e) => handleInputChange('title', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white transition-colors duration-200"
                      placeholder="输入文章标题"
                      required
                    />,
                    true
                  )}

                  {renderField('URL标识符',
                    <OptimizedInput
                      type="text"
                      value={form.slug}
                      onChange={(e) => handleInputChange('slug', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white transition-colors duration-200"
                      placeholder="article-url"
                    />
                  )}

                  {renderField('摘要',
                    <OptimizedTextarea
                      value={form.excerpt}
                      onChange={(e) => handleInputChange('excerpt', e.target.value)}
                      rows={3}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white transition-colors duration-200"
                      placeholder="输入文章摘要"
                    />
                  )}
                </div>
              </div>

              {/* 内容编辑器卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  文章内容
                </h3>
                <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
                  <OptimizedMarkdownEditor
                    value={form.content}
                    onChange={handleContentChange}
                    onInsertMedia={handleInsertMedia}
                    debounceDelay={500} // 500ms防抖延迟
                    minHeight="500px"
                    maxHeight="1000px"
                    placeholder="开始编写您的文章内容..."
                  />
                </div>
              </div>
            </div>

            {/* 右侧侧边栏 */}
            <div className="space-y-6">
              {/* 分类与标签卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  分类与标签
                </h3>

                <div className="space-y-6">
                  {renderField('分类',
                    <select
                      value={form.category_id ?? ''}
                      onChange={(e) => handleInputChange('category_id', e.target.value ? Number(e.target.value) : null)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
                    >
                      <option value="">选择分类</option>
                      {categories.map(category => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  )}

                  {renderField('标签',
                    <TagsInput
                      value={form.tags}
                      onChange={(tags) => handleInputChange('tags', tags)}
                    />
                  )}
                </div>
              </div>

              {/* 发布设置卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  发布设置
                </h3>

                <div className="space-y-4">
                  {renderField('状态',
                    <select
                      value={form.status}
                      onChange={(e) => handleInputChange('status', Number(e.target.value))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
                    >
                      <option value={0}>草稿</option>
                      <option value={1}>发布</option>
                      <option value={-1}>删除</option>
                    </select>
                  )}

                  <div className="space-y-3">
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.hidden}
                        onChange={(e) => handleInputChange('hidden', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        隐藏文章
                      </span>
                    </label>

                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.is_featured}
                        onChange={(e) => handleInputChange('is_featured', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        设为精选
                      </span>
                    </label>

                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.is_vip_only}
                        onChange={(e) => handleInputChange('is_vip_only', e.target.checked)}
                        disabled={form.hidden}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        VIP专属
                      </span>
                    </label>

                    {form.is_vip_only && !form.hidden && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          所需VIP等级
                        </label>
                        <select
                          value={form.required_vip_level}
                          onChange={(e) => handleInputChange('required_vip_level', Number(e.target.value))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
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
              </div>

              {/* 媒体与广告卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  媒体与广告
                </h3>

                <div className="space-y-6">
                  {renderField('封面图片',
                    <CoverImageUploader
                      value={form.cover_image}
                      onChange={(value) => handleInputChange('cover_image', value)}
                      onValidationChange={setCoverValid}
                      placeholder="点击上传或选择图片作为封面"
                    />
                  )}

                  {renderField('广告内容',
                    <OptimizedTextarea
                      value={form.article_ad}
                      onChange={(e) => handleInputChange('article_ad', e.target.value)}
                      rows={3}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white transition-colors duration-200"
                      placeholder="输入广告内容"
                    />
                  )}
                </div>
              </div>

              {/* 操作按钮卡片 */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <div className="space-y-3">
                  <button
                    type="submit"
                    disabled={isSubmitting || isLoading}
                    className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSubmitting ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        {mode === 'create' ? '创建中...' : '保存中...'}
                      </span>
                    ) : (
                      mode === 'create' ? '创建文章' : '保存文章'
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={onCancel}
                    disabled={isSubmitting}
                    className="w-full py-3 px-4 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
                  >
                    取消
                  </button>
                </div>

                {error && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
                    {error}
                  </div>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ArticleForm;