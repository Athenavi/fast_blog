'use client';

import { useState, useRef, useEffect } from 'react';
import { Smile } from 'lucide-react';
import { EmotePicker } from './EmotePicker';
import { parseEmotes } from '@/lib/emoteService';

interface CommentInputProps {
  onSubmit: (content: string) => void;
  placeholder?: string;
}

export function CommentInput({ onSubmit, placeholder = '发表评论...' }: CommentInputProps) {
  const [content, setContent] = useState('');
  const [showPicker, setShowPicker] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭表情选择器
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleEmoteSelect = (emoteCode: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newContent = content.substring(0, start) + emoteCode + content.substring(end);
    
    setContent(newContent);
    setShowPicker(false);
    
    // 恢复焦点并设置光标位置
    setTimeout(() => {
      textarea.focus();
      const newPos = start + emoteCode.length;
      textarea.setSelectionRange(newPos, newPos);
    }, 0);
  };

  const handleSubmit = () => {
    if (!content.trim()) return;
    onSubmit(content);
    setContent('');
  };

  // 预览渲染（将表情代码转换为 Emoji）
  const previewContent = parseEmotes(content);

  return (
    <div className="relative">
      <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className="w-full p-3 resize-none focus:outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
        />
        
        {/* 工具栏 */}
        <div className="flex justify-between items-center px-3 py-2 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600">
          <div className="relative" ref={pickerRef}>
            <button
              type="button"
              onClick={() => setShowPicker(!showPicker)}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title="插入表情"
            >
              <Smile size={20} />
            </button>
            
            {/* 表情选择器弹窗 */}
            {showPicker && (
              <div className="absolute bottom-full left-0 mb-2 z-10">
                <EmotePicker onSelect={handleEmoteSelect} />
              </div>
            )}
          </div>
          
          <button
            onClick={handleSubmit}
            disabled={!content.trim()}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            发表评论
          </button>
        </div>
      </div>

      {/* 实时预览 */}
      {content && (
        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">预览：</p>
          <p className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">{previewContent}</p>
        </div>
      )}
    </div>
  );
}
