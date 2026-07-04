'use client';

import React, {useRef, useEffect, useState} from 'react';
import {Send, Square} from 'lucide-react';

// 快捷操作预设
const QUICK_ACTIONS = [
  {icon: '📝', label: '写文章', prompt: '帮我写一篇关于 '},
  {icon: '👥', label: '用户', prompt: '列出所有用户'},
  {icon: '💬', label: '评论', prompt: '查看待审核的评论'},
  {icon: '📊', label: '统计', prompt: '博客的统计数据'},
  {icon: '⚙️', label: '系统', prompt: '查看系统信息'},
  {icon: '💾', label: '备份', prompt: '创建数据库备份'},
];

// ─── Chat Input Props ────────────────────────────

interface ChatInputProps {
  input: string;
  loading: boolean;
  disabled: boolean;
  onInput: (val: string) => void;
  onSend: () => void;
  onInterrupt: () => void;
}

// ─── Quick Actions ────────────────────────────────

function QuickActions({onSelect, visible}: {onSelect: (prompt: string) => void; visible: boolean}) {
  if (!visible) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mb-2.5 px-0.5">
      {QUICK_ACTIONS.map(action => (
        <button
          key={action.label}
          onClick={() => onSelect(action.prompt)}
          className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 hover:border-violet-200 dark:hover:border-violet-700 hover:text-violet-600 dark:hover:text-violet-400 transition-all whitespace-nowrap"
        >
          <span className="text-xs">{action.icon}</span>
          {action.label}
        </button>
      ))}
    </div>
  );
}

// ─── Chat Input Component ────────────────────────

export default function ChatInput({input, loading, disabled, onInput, onSend, onInterrupt}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [focused, setFocused] = useState(false);
  const showActions = !input.trim() && !loading && focused;

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && input.trim()) onSend();
    }
  };

  return (
    <div className="border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-950 flex-shrink-0">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3">
        <QuickActions onSelect={onInput} visible={showActions} />
        <div className="relative flex items-end gap-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-violet-500/50 focus-within:border-violet-400 transition-all shadow-sm">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => onInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="输入消息，Enter 发送…"
            disabled={loading}
            rows={1}
            className="flex-1 bg-transparent text-sm dark:text-white placeholder-gray-400 dark:placeholder-gray-500 resize-none outline-none max-h-40 leading-relaxed py-0.5 disabled:opacity-50"
          />

          {/* Action buttons */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {loading ? (
              <button
                onClick={onInterrupt}
                className="p-2 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors shadow-sm"
                title="停止生成"
              >
                <Square className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={onSend}
                disabled={!input.trim() || disabled}
                className="p-2 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm"
                title="发送"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
