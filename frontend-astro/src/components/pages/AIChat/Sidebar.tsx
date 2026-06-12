'use client';

import React from 'react';
import {MessageSquare, MessageSquarePlus, Settings, Sparkles, Trash2} from 'lucide-react';
import {ago, type Conversation} from './types';

// ─── Sidebar Props ────────────────────────────────

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  onSettings: () => void;
}

// ─── Sidebar Component ────────────────────────────

export default function Sidebar({
                                  conversations, activeId, onSelect, onNew, onDelete,
                                  collapsed, onToggle, onSettings,
                                }: SidebarProps) {
  return (
    <>
      {/* Mobile toggle overlay */}
      {!collapsed && (
        <div className="fixed inset-0 z-30 bg-black/20 backdrop-blur-sm lg:hidden" onClick={onToggle}/>
      )}

      <aside className={`
        fixed lg:relative inset-y-0 left-0 z-40
        flex flex-col bg-white dark:bg-gray-950
        border-r border-gray-200 dark:border-gray-800
        transition-all duration-300 ease-in-out
        ${collapsed ? '-translate-x-full lg:translate-x-0 lg:w-0 lg:overflow-hidden lg:border-0' : 'w-72 translate-x-0'}
      `}>
        {/* Header */}
        <div
          className="flex items-center justify-between h-14 px-4 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4 text-white"/>
            </div>
            <span className="font-bold text-sm text-gray-900 dark:text-white">AI Chat</span>
          </div>
          <button
            onClick={onNew}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors"
            title="新对话"
          >
            <MessageSquarePlus className="w-4 h-4"/>
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center mb-3">
                <MessageSquare className="w-6 h-6 text-gray-300 dark:text-gray-600"/>
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500">暂无对话</p>
              <button
                onClick={onNew}
                className="mt-3 text-xs text-violet-600 dark:text-violet-400 font-medium hover:underline"
              >
                开始新对话
              </button>
            </div>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && onSelect(conv.id)}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-all duration-150 ${
                  conv.id === activeId
                    ? 'bg-violet-50 dark:bg-violet-900/20 ring-1 ring-violet-200 dark:ring-violet-800/30'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  conv.id === activeId
                    ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'
                }`}>
                  <MessageSquare className="w-4 h-4"/>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-sm font-medium truncate ${
                      conv.id === activeId ? 'text-violet-900 dark:text-violet-200' : 'text-gray-800 dark:text-gray-200'
                    }`}>
                      {conv.title}
                    </span>
                    <span
                      className="text-[10px] text-gray-400 dark:text-gray-500 flex-shrink-0">{ago(conv.createdAt)}</span>
                  </div>
                </div>
                <button
                  onClick={(e) => onDelete(e, conv.id)}
                  className="p-1 rounded text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                  title="删除"
                >
                  <Trash2 className="w-3.5 h-3.5"/>
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer actions */}
        <div className="p-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0 space-y-1">
          <button
            onClick={onNew}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 text-sm text-gray-400 hover:text-violet-600 dark:hover:text-violet-400 hover:border-violet-300 dark:hover:border-violet-700 transition-all"
          >
            <MessageSquarePlus className="w-4 h-4"/>
            <span className="font-medium">新对话</span>
          </button>
          <button
            onClick={onSettings}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all"
          >
            <Settings className="w-4 h-4"/>
            <span className="font-medium">设置</span>
          </button>
        </div>
      </aside>
    </>
  );
}
