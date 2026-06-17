/**
 * ComponentLibrary — 组件库 / 模板选择器浮层
 *
 * 分两栏：预建页面模板（一键导入）+ 单个组件（追加到当前页面）。
 * 支持分类筛选和搜索。
 */
import React, {useState, useMemo} from 'react';
import {X, Search, Layout} from 'lucide-react';
import type {LibraryItem} from '../types';

interface Props {
    items: LibraryItem[];
    onSelectTemplate: (item: LibraryItem) => void;
    onSelectComponent: (item: LibraryItem) => void;
    onClose: () => void;
}

const CATEGORIES = ['全部', '营销', '企业', '博客', '作品集', '支持'];

export default function ComponentLibrary({items, onSelectTemplate, onSelectComponent, onClose}: Props) {
    const [category, setCategory] = useState('全部');
    const [search, setSearch] = useState('');

    const templates = useMemo(
        () => items.filter(i => i.id).filter(i => category === '全部' || i.category === category)
            .filter(i => !search || i.title?.includes(search) || i.name?.includes(search) || i.description?.includes(search)),
        [items, category, search],
    );

    const components = useMemo(
        () => items.filter(i => !i.id).filter(i => category === '全部' || i.category === category)
            .filter(i => !search || i.title?.includes(search) || i.name?.includes(search) || i.description?.includes(search)),
        [items, category, search],
    );

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
             onClick={onClose}>
            <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-5xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl"
                 onClick={e => e.stopPropagation()}>

                {/* 顶部 */}
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                    <h3 className="font-semibold text-lg">组件库</h3>
                    <button onClick={onClose}
                            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition">
                        <X className="w-4 h-4"/>
                    </button>
                </div>

                {/* 搜索 + 分类 */}
                <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 space-y-3">
                    {/* 搜索框 */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                        <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                               placeholder="搜索模板或组件..."
                               className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                    </div>
                    {/* 分类标签 */}
                    <div className="flex gap-2 text-sm flex-wrap">
                        {CATEGORIES.map(c => (
                            <button key={c} onClick={() => setCategory(c)}
                                    className={`px-3 py-1 rounded-lg transition ${
                                        category === c
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700'
                                    }`}>
                                {c}
                            </button>
                        ))}
                    </div>
                </div>

                {/* 内容 */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    {/* 页面模板 */}
                    <section>
                        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500"/> 预建页面模板
                        </h4>
                        {templates.length === 0 ? (
                            <p className="text-xs text-gray-400 py-4 text-center">无匹配模板</p>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {templates.map(t => (
                                    <div key={t.id}
                                         className="border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-green-400 hover:shadow-md cursor-pointer transition bg-gradient-to-br from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-medium text-sm">{t.title || t.name}</span>
                                            <span
                                                className="text-[10px] px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">{t.category}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">{t.description}</p>
                                        <button onClick={() => onSelectTemplate(t)}
                                                className="w-full px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700 transition">
                                            使用此模板
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* 单个组件 */}
                    <section>
                        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"/> 单个组件
                        </h4>
                        {components.length === 0 ? (
                            <p className="text-xs text-gray-400 py-4 text-center">无匹配组件</p>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {components.map(c => (
                                    <div key={c.name || c.title} onClick={() => onSelectComponent(c)}
                                         className="border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-blue-400 hover:shadow-md cursor-pointer transition">
                                        <div className="flex items-center gap-2 mb-2">
                                            <Layout className="w-4 h-4 text-blue-600"/>
                                            <span className="font-medium text-sm">{c.title || c.name}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{c.description}</p>
                                        <span
                                            className="text-[10px] text-gray-400">分类: {c.category}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
    );
}
