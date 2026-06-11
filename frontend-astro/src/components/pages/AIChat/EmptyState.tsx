'use client';

import React from 'react';
import {Sparkles, Settings} from 'lucide-react';
import {SUGGESTIONS} from './types';

// ─── Empty State Props ───────────────────────────

interface EmptyStateProps {
  needsConfig: boolean;
  onOpenSettings: () => void;
  onSuggestionClick: (text: string) => void;
}

// ─── Empty State Component ───────────────────────

export default function EmptyState({needsConfig, onOpenSettings, onSuggestionClick}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      {/* Icon */}
      <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-100 to-purple-100 dark:from-violet-900/20 dark:to-purple-900/20 flex items-center justify-center mb-6 shadow-inner">
        <Sparkles className="w-10 h-10 text-violet-500 dark:text-violet-400" />
      </div>

      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">开始 AI 对话</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-8 max-w-md">
        {needsConfig
          ? '请先完成 API 配置，连接你的 LLM 模型'
          : '通过自然语言管理博客内容，让 AI 帮你完成各项工作'}
      </p>

      {needsConfig ? (
        <button
          onClick={onOpenSettings}
          className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-violet-500 to-purple-600 text-white text-sm font-medium rounded-xl hover:from-violet-600 hover:to-purple-700 transition-all shadow-lg shadow-violet-200 dark:shadow-violet-900/30"
        >
          <Settings className="w-4 h-4" />
          打开设置
        </button>
      ) : (
        <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
          {SUGGESTIONS.map((item, i) => (
            <button
              key={i}
              onClick={() => onSuggestionClick(item.text)}
              className="group flex items-center gap-3 p-4 rounded-2xl border border-gray-200 dark:border-gray-700 hover:border-violet-300 dark:hover:border-violet-700 bg-white dark:bg-gray-900 text-left text-sm transition-all hover:shadow-md hover:-translate-y-0.5"
            >
              <span className="text-xl flex-shrink-0">{item.icon}</span>
              <div>
                <div className="font-semibold text-gray-800 dark:text-gray-200 text-xs group-hover:text-violet-600 dark:group-hover:text-violet-400 transition-colors">{item.title}</div>
                <div className="text-[11px] text-gray-400 dark:text-gray-500 line-clamp-2 mt-0.5">{item.text}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
