/**
 * PageListPanel — 左侧页面列表面板（含搜索、状态标识）
 */
import React, {useState, useMemo} from 'react';
import {Plus, Trash2, CheckCircle2, FileText, Search} from 'lucide-react';
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
    const [search, setSearch] = useState('');

    const filtered = useMemo(
        () => search ? pages.filter(p =>
            p.title.toLowerCase().includes(search.toLowerCase()) ||
            p.slug.toLowerCase().includes(search.toLowerCase())
        ) : pages,
        [pages, search],
    );

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

            {/* 搜索框 */}
            <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700/50">
                <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400"/>
                    <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                           placeholder="搜索页面..."
                           className="w-full pl-7 pr-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-gray-400"/>
                </div>
            </div>

            {/* 列表 */}
            {isLoading ? (
                <div className="flex-1 flex items-center justify-center text-xs text-gray-400">
                    <div className="space-y-2 w-full px-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>
                        ))}
                    </div>
                </div>
            ) : filtered.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-xs text-gray-400">
                    {search ? (
                        <>
                            <Search className="w-6 h-6 mb-2 text-gray-300 dark:text-gray-600"/>
                            <p>无匹配页面</p>
                        </>
                    ) : (
                        <>
                            <FileText className="w-8 h-8 mb-2 text-gray-300 dark:text-gray-600"/>
                            <p>暂无页面</p>
                            <p className="mt-1">点击「+」新建</p>
                        </>
                    )}
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700/50">
                    {filtered.map(page => (
                        <div key={page.id}
                             className={`group flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors ${
                                 selectedPage?.id === page.id
                                     ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-l-blue-500'
                                     : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 border-l-2 border-l-transparent'
                             }`}
                             onClick={() => onSelectPage(page)}>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium truncate">{page.title}</span>
                                    {page.is_published ? (
                                        <span className="text-[10px] px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full shrink-0">已发布</span>
                                    ) : (
                                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded-full shrink-0">草稿</span>
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
