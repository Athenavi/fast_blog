'use client';

import React, {useRef, useEffect} from 'react';
import {Send, Square} from 'lucide-react';

// ─── Chat Input Props ────────────────────────────

interface ChatInputProps {
  input: string;
  loading: boolean;
  disabled: boolean;
  onInput: (val: string) => void;
  onSend: () => void;
  onInterrupt: () => void;
}

// ─── Chat Input Component ────────────────────────

export default function ChatInput({input, loading, disabled, onInput, onSend, onInterrupt}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
        <div className="relative flex items-end gap-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-violet-500/50 focus-within:border-violet-400 transition-all shadow-sm">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => onInput(e.target.value)}
            onKeyDown={handleKeyDown}
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
