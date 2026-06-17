/**
 * ComponentLibrary — 组件库/模板选择器浮层
 *
 * 模板卡片底部嵌入 BlockPreview 微型缩略图，让用户预览效果再选择。
 * 单个组件卡片点击直接添加到当前页面。
 */
import React, {useState, useMemo} from 'react';
import {X, Search} from 'lucide-react';
import BlockPreview from './BlockPreview';
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
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
                        <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                               placeholder="搜索模板或组件..."
                               className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                    </div>
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
                                {templates.map(t => {
                                    const firstBlock = t.blocks?.[0];
                                    return (
                                        <div key={t.id} onClick={() => onSelectTemplate(t)}
                                             className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden hover:border-green-400 hover:shadow-md cursor-pointer transition bg-white dark:bg-gray-800 flex flex-col">
                                            {/* 微型预览缩略图 */}
                                            <div className="h-24 bg-gray-50 dark:bg-gray-900 overflow-hidden border-b border-gray-100 dark:border-gray-700">
                                                {firstBlock ? (
                                                    <div className="scale-[0.3] origin-top-left w-[333%] h-[333%] pointer-events-none">
                                                        <BlockPreview type={firstBlock.type}
                                                                      data={firstBlock.props || {}}
                                                                      styles={{}}/>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center justify-center h-full text-gray-300 dark:text-gray-600 text-xs">
                                                        无预览
                                                    </div>
                                                )}
                                            </div>
                                            <div className="p-3 flex-1 flex flex-col">
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-medium text-sm">{t.title || t.name}</span>
                                                    <span className="text-[10px] px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">{t.category}</span>
                                                </div>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2 flex-1">{t.description}</p>
                                                <span className="text-[10px] text-blue-600 font-medium hover:underline">使用此模板 →</span>
                                            </div>
                                        </div>
                                    );
                                })}
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
                                {components.map(c => {
                                    const block = c.blocks?.[0];
                                    return (
                                        <div key={c.name || c.title} onClick={() => onSelectComponent(c)}
                                             className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden hover:border-blue-400 hover:shadow-md cursor-pointer transition bg-white dark:bg-gray-800 flex flex-col">
                                            {/* 微型预览 */}
                                            <div className="h-20 bg-gray-50 dark:bg-gray-900 overflow-hidden border-b border-gray-100 dark:border-gray-700">
                                                {block ? (
                                                    <div className="scale-[0.35] origin-top-left w-[285%] h-[285%] pointer-events-none">
                                                        <BlockPreview type={block.type}
                                                                      data={block.props || {}}
                                                                      styles={{}}/>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center justify-center h-full text-gray-300 dark:text-gray-600 text-xs">
                                                        无预览
                                                    </div>
                                                )}
                                            </div>
                                            <div className="p-3">
                                                <span className="font-medium text-sm">{c.title || c.name}</span>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{c.description}</p>
                                                <span className="text-[10px] text-gray-400 mt-1 block">分类: {c.category}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
    );
}
