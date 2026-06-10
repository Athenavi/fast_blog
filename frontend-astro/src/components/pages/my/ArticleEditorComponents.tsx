import React from 'react';
import {X, Keyboard} from 'lucide-react';

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

