/**
 * PageListPanel — 左侧页面列表面板
 */
import React from 'react';
import {Plus, Trash2, CheckCircle2, FileText} from 'lucide-react';
import type {PageData} from '../types';

interface Props {
    pages: PageData[];
    isLoading: boolean;
    selectedPage: PageData | null;
    onSelectPage: (page: PageData) => void;
    onDeletePage: (page: PageData) => void;
    onCreatePage: () => void;
}

export default function PageListPanel({pages, isLoading, selectedPage, onSelectPage, onDeletePage, onCreatePage}: Props) {
    return (
        <div className="w-60 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col shrink-0">
            {/* 头部 */}
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">页面列表</span>
                <button onClick={onCreatePage}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition"
                        title="新建页面">
                    <Plus className="w-4 h-4"/>
                </button>
            </div>

            {/* 列表 */}
            {isLoading ? (
                <div className="flex-1 flex items-center justify-center text-xs text-gray-400">加载中...</div>
            ) : pages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-xs text-gray-400">
                    <FileText className="w-8 h-8 mb-2 text-gray-300 dark:text-gray-600"/>
                    <p>暂无页面</p>
                    <p className="mt-1">点击「+」新建</p>
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700/50">
                    {pages.map(page => (
                        <div key={page.id}
                             className={`group flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors ${
                                 selectedPage?.id === page.id
                                     ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-l-blue-500'
                                     : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 border-l-2 border-l-transparent'
                             }`}
                             onClick={() => onSelectPage(page)}>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-sm font-medium truncate">{page.title}</span>
                                    {page.is_published && (
                                        <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0"/>
                                    )}
                                </div>
                                <div className="text-[11px] text-gray-400 dark:text-gray-500 font-mono truncate mt-0.5">
                                    /{page.slug}
                                </div>
                            </div>
                            <button onClick={(e) => {
                                e.stopPropagation();
                                onDeletePage(page);
                            }}
                                    className="p-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                                    title="删除">
                                <Trash2 className="w-3 h-3"/>
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
