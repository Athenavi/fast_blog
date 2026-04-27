'use client';

import { useState } from 'react';
import { ArticleService } from '@/lib/api/index';
import { useHotkeys } from '@/hooks/useHotkeys';

export function QuickDraft() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Ctrl+D 聚焦标题
  useHotkeys({
    'ctrl+d': (e) => {
      e.preventDefault();
      document.getElementById('quick-draft-title')?.focus();
    },
  });

  const handleSave = async () => {
    if (!title.trim()) {
      setMessage({ type: 'error', text: '请输入标题' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('content', content || '');
      formData.append('status', '0'); // 0 表示草稿

      const response = await ArticleService.createArticle(formData);

      if (response.success) {
        setMessage({ type: 'success', text: '草稿已保存！' });
        setTitle('');
        setContent('');
      } else {
        setMessage({ type: 'error', text: response.error || '保存失败' });
      }
    } catch (error) {
      console.error('Failed to save draft:', error);
      setMessage({ type: 'error', text: '网络错误，请重试' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">快速草稿</h3>
      
      <div className="space-y-4">
        <div>
          <label htmlFor="quick-draft-title" className="sr-only">标题</label>
          <input
            id="quick-draft-title"
            type="text"
            placeholder="标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <label htmlFor="quick-draft-content" className="sr-only">内容</label>
          <textarea
            id="quick-draft-content"
            placeholder="写点什么..."
            rows={4}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none"
          />
        </div>

        {message && (
          <div className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </div>
        )}

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '保存中...' : '保存草稿'}
          </button>
        </div>
      </div>
    </div>
  );
}
