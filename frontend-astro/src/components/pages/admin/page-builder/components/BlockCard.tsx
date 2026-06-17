/**
 * BlockCard — 单个块卡片（可拖拽 + 编辑 + 样式 + 删除）
 */
import React, {useState, memo} from 'react';
import {GripVertical, Edit3, Trash2, Palette} from 'lucide-react';
import BlockFieldEditor from './BlockFieldEditor';
import StylePanel from './StylePanel';

interface Props {
    block: any;
    index: number;
    onDelete: (index: number) => void;
    onDataChange: (index: number, data: any) => void;
    onStylesChange: (index: number, styles: any) => void;
}

/** 块类型 → 显示颜色标签 */
const TYPE_COLORS: Record<string, string> = {
    'hero-section': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    hero: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    'features-grid': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    grid: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    'cta-section': 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    cta: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    text: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    image: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
    video: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
    button: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    testimonials: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
    'pricing-table': 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    pricing: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    'faq-section': 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
    faq: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
    'contact-form': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
    'team-members': 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    'icon-list': 'bg-lime-100 text-lime-700 dark:bg-lime-900/40 dark:text-lime-300',
    columns: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    stats: 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300',
    code: 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-300',
    divider: 'bg-gray-50 text-gray-400 dark:bg-gray-800 dark:text-gray-500',
};

function BlockCardInner({block, index, onDelete, onDataChange, onStylesChange}: Props) {
    const [expanded, setExpanded] = useState(false);
    const [showStyle, setShowStyle] = useState(false);
    const colorClass = TYPE_COLORS[block.type] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

    return (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow">
            {/* 头部 */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700/50">
                <div className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 transition-colors">
                    <GripVertical className="w-4 h-4"/>
                </div>
                <span className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${colorClass}`}>
                    {block.type}
                </span>
                <div className="flex-1"/>
                {block.styles?.backgroundColor && (
                    <span className="w-3 h-3 rounded-full border border-gray-200" style={{
                        backgroundColor: block.styles.backgroundColor
                    }}/>
                )}
                <button onClick={() => setShowStyle(!showStyle)}
                        className={`p-1 rounded transition ${showStyle ? 'bg-purple-100 text-purple-600' : 'text-gray-400 hover:text-purple-600'}`}
                        title="样式">
                    <Palette className="w-3.5 h-3.5"/>
                </button>
                <button onClick={() => setExpanded(!expanded)}
                        className={`p-1 rounded transition ${expanded ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-blue-600'}`}
                        title="编辑">
                    <Edit3 className="w-3.5 h-3.5"/>
                </button>
                <button onClick={() => onDelete(index)}
                        className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                        title="删除">
                    <Trash2 className="w-3.5 h-3.5"/>
                </button>
            </div>

            {/* 数据摘要 */}
            {!expanded && !showStyle && (
                <div className="px-4 py-2 text-[11px] text-gray-400 dark:text-gray-500 line-clamp-2 font-mono">
                    {JSON.stringify(block.data).slice(0, 120)}
                </div>
            )}

            {/* 编辑器 */}
            {expanded && (
                <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50">
                    <BlockFieldEditor type={block.type} data={block.data || {}}
                                      onChange={(d) => onDataChange(index, d)}/>
                </div>
            )}

            {/* 样式面板 */}
            {showStyle && (
                <div className="px-4 py-3">
                    <StylePanel styles={block.styles || {}}
                                onChange={(s) => onStylesChange(index, s)}
                                onClose={() => setShowStyle(false)}/>
                </div>
            )}
        </div>
    );
}

export default memo(BlockCardInner);
