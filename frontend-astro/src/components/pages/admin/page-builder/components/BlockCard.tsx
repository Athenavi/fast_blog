/**
 * BlockCard — 单个块卡片（可拖拽 + 编辑 + 样式 + 删除 + 复制）
 */
import React, {useState, memo} from 'react';
import {GripVertical, Edit3, Trash2, Palette, Copy} from 'lucide-react';
import BlockFieldEditor from './BlockFieldEditor';
import StylePanel from './StylePanel';

interface Props {
    block: any;
    index: number;
    onDelete: (index: number) => void;
    onCopy: (index: number) => void;
    onDataChange: (index: number, data: any) => void;
    onStylesChange: (index: number, styles: any) => void;
}

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

/** 据块类型提取人类可读的数据摘要 */
function blockSummary(block: any): string {
    const d = block.data || {};
    switch (block.type) {
        case 'hero':
        case 'hero-section':
            return d.title || d.subtitle || '(Hero)';
        case 'text':
            return (d.content || d.text || '').slice(0, 80) || '(空文本)';
        case 'heading':
            return d.text || '(标题)';
        case 'image':
            return d.alt || d.src?.slice(0, 40) || '(图片)';
        case 'video':
            return d.title || d.url?.slice(0, 40) || '(视频)';
        case 'button':
            return d.text || '(按钮)';
        case 'cta':
        case 'cta-section':
            return d.title || '(CTA)';
        case 'features-grid':
        case 'grid':
            return `特性列表 (${(d.features || []).length}项)`;
        case 'testimonial':
        case 'testimonials':
            return `评价 (${(d.testimonials || []).length}条)`;
        case 'faq':
        case 'faq-section':
            return `FAQ (${(d.faqs || []).length}条)`;
        case 'team':
        case 'team-members':
            return `团队成员 (${(d.members || []).length}人)`;
        case 'pricing':
        case 'pricing-table':
            return `定价方案 (${(d.plans || []).length}项)`;
        case 'contact-form':
        case 'form':
            return `联系表单 (${(d.fields || []).length}个字段)`;
        case 'newsletter':
            return '邮件订阅';
        case 'stats':
        case 'stats-counter':
            return `统计 (${(d.items || []).length}项)`;
        case 'icon-list':
            return `图标列表 (${(d.items || []).length}项)`;
        case 'columns':
            return `多列布局 (${d.count || 2}列)`;
        case 'divider':
            return '分隔线';
        case 'code':
            return (d.language || '').toUpperCase() + (d.code ? ` ${d.code.slice(0, 40)}` : '');
        case 'quote':
            return d.text?.slice(0, 60) || '(引用)';
        case 'progress':
            return `${d.label || ''} ${d.value ?? ''}%`;
        default:
            const keys = Object.keys(d);
            if (keys.length === 0) return '(无数据)';
            const first = d[keys[0]];
            return typeof first === 'string' ? first.slice(0, 80) : JSON.stringify(d).slice(0, 80);
    }
}

function BlockCardInner({block, index, onDelete, onCopy, onDataChange, onStylesChange}: Props) {
    const [expanded, setExpanded] = useState(false);
    const [showStyle, setShowStyle] = useState(false);
    const colorClass = TYPE_COLORS[block.type] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

    return (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-all duration-150">
            {/* 头部 */}
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-gray-100 dark:border-gray-700/50">
                {/* 拖拽手柄 — 始终半透明可见 */}
                <div className="cursor-grab active:cursor-grabbing text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-300 transition-colors">
                    <GripVertical className="w-4 h-4"/>
                </div>

                <span className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${colorClass} shrink-0`}>
                    {block.type}
                </span>

                {/* 块数据摘要 */}
                <span className="text-xs text-gray-400 dark:text-gray-500 truncate min-w-0">
                    {blockSummary(block)}
                </span>

                <div className="flex-1 min-w-[4px]"/>

                {block.styles?.backgroundColor && (
                    <span className="w-3 h-3 rounded-full border border-gray-200 shrink-0"
                          style={{backgroundColor: block.styles.backgroundColor}}/>
                )}

                {/* 操作按钮 */}
                <div className="flex items-center gap-0.5">
                    <button onClick={() => onCopy(index)}
                            className="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition"
                            title="复制块">
                        <Copy className="w-3.5 h-3.5"/>
                    </button>
                    <button onClick={() => setShowStyle(!showStyle)}
                            className={`p-1 rounded transition ${showStyle ? 'bg-purple-100 text-purple-600' : 'text-gray-400 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'}`}
                            title="样式设置 (调色板)">
                        <Palette className="w-3.5 h-3.5"/>
                    </button>
                    <button onClick={() => setExpanded(!expanded)}
                            className={`p-1 rounded transition ${expanded ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20'}`}
                            title="编辑内容">
                        <Edit3 className="w-3.5 h-3.5"/>
                    </button>
                    <button onClick={() => onDelete(index)}
                            className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                            title="删除块">
                        <Trash2 className="w-3.5 h-3.5"/>
                    </button>
                </div>
            </div>

            {/* 编辑器（折叠时隐藏） */}
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
