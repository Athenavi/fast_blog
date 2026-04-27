'use client';

import { useState, useMemo } from 'react';
import { getAvailableEmotes } from '@/lib/emoteService';
import { Search } from 'lucide-react';

interface EmotePickerProps {
  onSelect: (emoteCode: string) => void;
}

export function EmotePicker({ onSelect }: EmotePickerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const emotes = useMemo(() => getAvailableEmotes(), []);

  const filteredEmotes = emotes.filter(emote => 
    emote.code.includes(searchTerm.toLowerCase()) || 
    emote.category.includes(searchTerm)
  );

  // 按分类分组
  const groupedEmotes = useMemo(() => {
    const groups: Record<string, typeof emotes> = {};
    filteredEmotes.forEach(emote => {
      if (!groups[emote.category]) {
        groups[emote.category] = [];
      }
      groups[emote.category].push(emote);
    });
    return groups;
  }, [filteredEmotes]);

  return (
    <div className="w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl p-3">
      {/* 搜索框 */}
      <div className="relative mb-3">
        <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
        <input
          type="text"
          placeholder="搜索表情..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-8 pr-2 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
      </div>

      {/* 表情列表 */}
      <div className="max-h-64 overflow-y-auto space-y-3">
        {Object.entries(groupedEmotes).map(([category, categoryEmotes]) => (
          <div key={category}>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">{category}</h4>
            <div className="grid grid-cols-6 gap-1">
              {categoryEmotes.map((emote) => (
                <button
                  key={emote.code}
                  onClick={() => onSelect(emote.code)}
                  title={emote.code}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-xl flex items-center justify-center"
                >
                  {emote.emoji}
                </button>
              ))}
            </div>
          </div>
        ))}
        
        {filteredEmotes.length === 0 && (
          <div className="text-center py-4 text-sm text-gray-500 dark:text-gray-400">
            未找到相关表情
          </div>
        )}
      </div>
    </div>
  );
}
