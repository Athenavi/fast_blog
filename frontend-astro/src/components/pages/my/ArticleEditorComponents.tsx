import React, {useState, useRef, useEffect, useMemo} from 'react';
import {Check, ChevronDown, X, Keyboard, Loader, Clock, AlertCircle} from 'lucide-react';

export const ShortcutsModal: React.FC<{ onClose: () => void }> = ({onClose}) => {
    const shortcuts = [
        {
            category: '基础格式', items: [
                {keys: 'Ctrl + B', desc: '粗体'}, {keys: 'Ctrl + I', desc: '斜体'},
                {keys: 'Ctrl + U', desc: '下划线'}, {keys: 'Ctrl + Shift + S', desc: '删除线'},
                {keys: 'Ctrl + Shift + H', desc: '高亮'},
            ]
        },
        {
            category: '标题与段落', items: [
                {keys: 'Ctrl + Alt + 1', desc: '一级标题'}, {keys: 'Ctrl + Alt + 2', desc: '二级标题'},
                {keys: 'Ctrl + Alt + 3', desc: '三级标题'}, {keys: 'Ctrl + Shift + 8', desc: '无序列表'},
                {keys: 'Ctrl + Shift + 7', desc: '有序列表'}, {keys: 'Ctrl + Shift + 9', desc: '引用'},
            ]
        },
        {
            category: '通用操作', items: [
                {keys: 'Ctrl + S', desc: '保存草稿'}, {keys: 'Ctrl + Shift + P', desc: '发布文章'},
                {keys: 'Ctrl + K', desc: '插入链接'}, {keys: 'Ctrl + Shift + I', desc: '插入图片'},
                {keys: 'Ctrl + Z', desc: '撤销'}, {keys: 'Ctrl + Shift + Z', desc: '重做'},
            ]
        },
    ];
    return (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/50 backdrop-blur-sm"
             onClick={onClose}>
            <div
                className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"
                onClick={e => e.stopPropagation()}>
                <div
                    className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
                    <div className="flex items-center gap-2">
                        <Keyboard className="w-5 h-5 text-blue-600"/>
                        <h3 className="font-bold text-gray-900 dark:text-white text-lg">键盘快捷键</h3>
                    </div>
                    <button onClick={onClose}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                        <X className="w-5 h-5 text-gray-400"/>
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {shortcuts.map(group => (
                        <div key={group.category}>
                          <h4
                            className="text-xs font-bold text-gray-400 dark:text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">{group.category}</h4>
                            <div className="space-y-1.5">
                                {group.items.map(s => (
                                    <div key={s.keys}
                                         className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                        <span className="text-sm text-gray-700 dark:text-gray-300">{s.desc}</span>
                                        <div className="flex gap-1">
                                            {s.keys.split(' + ').map((k, i) => (
                                                <React.Fragment key={i}>
                                                    {i > 0 && <span
                                                        className="text-gray-300 dark:text-gray-600 text-xs self-center">+</span>}
                                                    <kbd
                                                        className="px-2 py-0.5 text-xs font-mono bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md text-gray-600 dark:text-gray-400 shadow-sm">{k}</kbd>
                                                </React.Fragment>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

/* ── Toolbar Dropdown ── */



export function useWritingStats(content: string) {
    return useMemo(() => {
        const text = content.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
        const chars = text.length;
        const words = text ? text.split(/[\s,，。！？；：、]+/).filter(Boolean).length : 0;
        const sentences = text ? text.split(/[。！？.!?\n]+/).filter(Boolean).length : 0;
        const paragraphs = content ? content.split(/<\/p>|<br\s*\/?>/gi).filter(p => p.replace(/<[^>]*>/g, '').trim()).length : 0;
        const readingTime = Math.max(1, Math.ceil(chars / 500)); // ~500 chars/min for Chinese
        return {chars, words, sentences, paragraphs, readingTime};
    }, [content]);
}

/* ── Keyboard Shortcuts Modal ── */



export const ToolbarDropdown: React.FC<{
    trigger: React.ReactNode;
    children: React.ReactNode;
    align?: 'left' | 'right';
}> = ({trigger, children, align = 'left'}) => {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    return (
        <div className="relative" ref={ref}>
            <div onClick={() => setOpen(!open)}>{trigger}</div>
            {open && (
                <div
                    className={`absolute top-full mt-1 ${align === 'right' ? 'right-0' : 'left-0'} z-50 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5 min-w-[180px] animate-in fade-in slide-in-from-top-2 duration-150`}
                    onClick={() => setOpen(false)}>
                    {children}
                </div>
            )}
        </div>
    );
};

/* ── Section Component ── */



export const Section: React.FC<{
  icon: React.ComponentType<{ className?: string }>;
    title: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
    badge?: string | number
}> = ({
          icon: Icon, title, children, defaultOpen = true, badge
      }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div
            className="border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-800/50 mb-3">
            <button type="button" onClick={() => setIsOpen(!isOpen)}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/80 transition-colors">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                        <Icon className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400"/>
                    </div>
                    <span
                        className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">{title}</span>
                    {badge !== undefined && (
                        <span
                            className="px-1.5 py-0.5 text-[10px] font-bold bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full">{badge}</span>
                    )}
                </div>
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}/>
            </button>
            <div
                className={`transition-all duration-200 ${isOpen ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'} overflow-hidden`}>
                <div className="px-4 pb-4">{children}</div>
            </div>
        </div>
    );
};

/* ── Save Status Indicator ── */



export const SaveStatus: React.FC<{ saving: boolean; lastSaved: number | null }> = ({saving, lastSaved}) => {
    const [showCheck, setShowCheck] = useState(false);

    useEffect(() => {
        if (lastSaved) {
            setShowCheck(true);
            const t = setTimeout(() => setShowCheck(false), 2000);
            return () => clearTimeout(t);
        }
    }, [lastSaved]);

    if (saving) {
        return (
            <div className="flex items-center gap-1.5 text-xs text-blue-500">
                <Loader className="w-3.5 h-3.5 animate-spin"/>
                <span>保存中...</span>
            </div>
        );
    }

    if (showCheck) {
        return (
            <div className="flex items-center gap-1.5 text-xs text-emerald-500 animate-in fade-in duration-200">
                <Check className="w-3.5 h-3.5"/>
                <span>已保存</span>
            </div>
        );
    }

    if (lastSaved) {
        const ago = Date.now() - lastSaved;
        const label = ago < 60000 ? '刚刚' : ago < 3600000 ? `${Math.floor(ago / 60000)} 分钟前` : `${Math.floor(ago / 3600000)} 小时前`;
        return <span className="text-xs text-gray-400">{label} 已自动保存</span>;
    }

    return null;
};

/* ── Main Editor Component ── */
