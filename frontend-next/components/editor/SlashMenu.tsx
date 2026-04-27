'use client';

import React, {useEffect, useRef} from 'react';
import {Card} from '@/components/ui/card';
import {ScrollArea} from '@/components/ui/scroll-area';

interface SlashMenuItem {
    id: string;
    label: string;
    description: string;
    icon: string;
    category: 'basic' | 'media' | 'advanced';
}

const menuItems: SlashMenuItem[] = [
    // 基础块
    {id: 'heading1', label: '标题 1', description: '大章节标题', icon: 'H1', category: 'basic'},
    {id: 'heading2', label: '标题 2', description: '子章节标题', icon: 'H2', category: 'basic'},
    {id: 'heading3', label: '标题 3', description: '小节标题', icon: 'H3', category: 'basic'},
    {id: 'bulletList', label: '无序列表', description: '创建项目符号列表', icon: '•', category: 'basic'},
    {id: 'orderedList', label: '有序列表', description: '创建编号列表', icon: '1.', category: 'basic'},
    {id: 'taskList', label: '任务列表', description: '创建待办事项列表', icon: '☑', category: 'basic'},
    {id: 'quote', label: '引用', description: '引用文本块', icon: '"', category: 'basic'},
    {id: 'divider', label: '分隔线', description: '水平分割线', icon: '—', category: 'basic'},

    // 媒体块
    {id: 'image', label: '图片', description: '插入图片', icon: '🖼️', category: 'media'},
    {id: 'video', label: '视频', description: '嵌入视频', icon: '🎥', category: 'media'},

    // 高级块
    {id: 'codeBlock', label: '代码块', description: '带语法高亮的代码', icon: '</>', category: 'advanced'},
    {id: 'table', label: '表格', description: '插入表格', icon: '📊', category: 'advanced'},
];

interface SlashMenuProps {
    position: { x: number; y: number };
    onSelect: (blockType: string) => void;
    onClose: () => void;
}

export function SlashMenu({position, onSelect, onClose}: SlashMenuProps) {
    const menuRef = useRef<HTMLDivElement>(null);
    const [selectedIndex, setSelectedIndex] = React.useState(0);
    const [searchQuery, setSearchQuery] = React.useState('');

    // 过滤菜单项
    const filteredItems = menuItems.filter(item =>
        item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // 点击外部关闭
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    // 键盘导航
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex(prev => (prev + 1) % filteredItems.length);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex(prev => (prev - 1 + filteredItems.length) % filteredItems.length);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (filteredItems[selectedIndex]) {
                    onSelect(filteredItems[selectedIndex].id);
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [filteredItems, selectedIndex, onSelect, onClose]);

    // 分组显示
    const groupedItems = {
        basic: filteredItems.filter(item => item.category === 'basic'),
        media: filteredItems.filter(item => item.category === 'media'),
        advanced: filteredItems.filter(item => item.category === 'advanced'),
    };

    return (
        <div
            ref={menuRef}
            className="fixed z-50 w-80 max-w-[90vw]"
            style={{
                left: Math.min(position.x, window.innerWidth - 340),
                top: Math.min(position.y, window.innerHeight - 400),
                // 移动端居中显示
                ...(window.innerWidth < 768 ? {
                    left: '50%',
                    top: '50%',
                    transform: 'translate(-50%, -50%)'
                } : {})
            }}
        >
            <Card className="shadow-xl border-gray-200 dark:border-gray-700">
                {/* 搜索框 */}
                <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                    <input
                        type="text"
                        placeholder="搜索块类型..."
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value);
                            setSelectedIndex(0);
                        }}
                        className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        autoFocus
                    />
                </div>

                {/* 菜单列表 */}
                <ScrollArea className="max-h-80">
                    <div className="p-2 space-y-3">
                        {/* 基础块 */}
                        {groupedItems.basic.length > 0 && (
                            <div>
                                <div
                                    className="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                                    基础块
                                </div>
                                {groupedItems.basic.map((item) => {
                                    const globalIndex = filteredItems.findIndex(i => i.id === item.id);
                                    return (
                                        <MenuItem
                                            key={item.id}
                                            item={item}
                                            isSelected={globalIndex === selectedIndex}
                                            onClick={() => onSelect(item.id)}
                                        />
                                    );
                                })}
                            </div>
                        )}

                        {/* 媒体块 */}
                        {groupedItems.media.length > 0 && (
                            <div>
                                <div
                                    className="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                                    媒体
                                </div>
                                {groupedItems.media.map((item) => {
                                    const globalIndex = filteredItems.findIndex(i => i.id === item.id);
                                    return (
                                        <MenuItem
                                            key={item.id}
                                            item={item}
                                            isSelected={globalIndex === selectedIndex}
                                            onClick={() => onSelect(item.id)}
                                        />
                                    );
                                })}
                            </div>
                        )}

                        {/* 高级块 */}
                        {groupedItems.advanced.length > 0 && (
                            <div>
                                <div
                                    className="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                                    高级
                                </div>
                                {groupedItems.advanced.map((item) => {
                                    const globalIndex = filteredItems.findIndex(i => i.id === item.id);
                                    return (
                                        <MenuItem
                                            key={item.id}
                                            item={item}
                                            isSelected={globalIndex === selectedIndex}
                                            onClick={() => onSelect(item.id)}
                                        />
                                    );
                                })}
                            </div>
                        )}

                        {filteredItems.length === 0 && (
                            <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                                未找到匹配的块类型
                            </div>
                        )}
                    </div>
                </ScrollArea>

                {/* 底部提示 */}
                <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        使用 <kbd className="px-1 py-0.5 bg-white dark:bg-gray-700 rounded border">↑</kbd>{' '}
                        <kbd className="px-1 py-0.5 bg-white dark:bg-gray-700 rounded border">↓</kbd> 导航，
                        <kbd className="px-1 py-0.5 bg-white dark:bg-gray-700 rounded border ml-1">Enter</kbd> 选择
                    </p>
                </div>
            </Card>
        </div>
    );
}

interface MenuItemProps {
    item: SlashMenuItem;
    isSelected: boolean;
    onClick: () => void;
}

function MenuItem({item, isSelected, onClick}: MenuItemProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`w-full flex items-start gap-3 px-3 py-2 rounded-md transition-colors text-left ${
                isSelected
                    ? 'bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
        >
            <div className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-md ${
                isSelected
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-600'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
            }`}>
                <span className="text-lg">{item.icon}</span>
            </div>
            <div className="flex-1 min-w-0">
                <div className={`font-medium text-sm ${
                    isSelected ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-gray-100'
                }`}>
                    {item.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {item.description}
                </div>
            </div>
        </button>
    );
}
