'use client';

import React from 'react';

interface ListItem {
    id: string;
    content: string;
}

interface ListBlockProps {
    attributes: {
        items?: ListItem[];
        ordered?: boolean;
    };
    isSelected?: boolean;
    onChange?: (items: ListItem[]) => void;
}

/**
 * 列表 Block 组件
 */
const ListBlock: React.FC<ListBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const items = attributes.items || [];
    const ordered = attributes.ordered || false;

    const addItem = () => {
        const newItem: ListItem = {
            id: `item-${Date.now()}`,
            content: ''
        };
        if (onChange) {
            onChange([...items, newItem]);
        }
    };

    const removeItem = (index: number) => {
        if (onChange) {
            onChange(items.filter((_, i) => i !== index));
        }
    };

    const updateItem = (index: number, content: string) => {
        if (onChange) {
            const newItems = [...items];
            newItems[index] = { ...newItems[index], content };
            onChange(newItems);
        }
    };

    if (isSelected) {
        return (
            <div className="py-2 ring-2 ring-blue-500 rounded p-3">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {ordered ? '有序列表' : '无序列表'}
                    </span>
                    <button
                        onClick={addItem}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    >
                        + 添加项
                    </button>
                </div>
                
                <div className="space-y-2">
                    {items.map((item, index) => (
                        <div key={item.id} className="flex gap-2">
                            <span className="text-gray-500 dark:text-gray-400 pt-2 min-w-[24px]">
                                {ordered ? `${index + 1}.` : '•'}
                            </span>
                            <input
                                type="text"
                                value={item.content}
                                onChange={(e) => updateItem(index, e.target.value)}
                                className="flex-1 p-2 border border-gray-300 dark:border-gray-600 rounded 
                                    bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder={`列表项 ${index + 1}...`}
                            />
                            <button
                                onClick={() => removeItem(index)}
                                className="px-2 py-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                    
                    {items.length === 0 && (
                        <p className="text-gray-400 italic text-center py-4">
                            点击"添加项"开始创建列表
                        </p>
                    )}
                </div>
            </div>
        );
    }

    // 预览模式
    if (items.length === 0) {
        return (
            <div className="py-2">
                <p className="text-gray-400 italic">空列表</p>
            </div>
        );
    }

    const ListTag = ordered ? 'ol' : 'ul';
    const listStyle = ordered ? 'list-decimal' : 'list-disc';

    return (
        <div className="py-2">
            <ListTag className={`${listStyle} list-inside space-y-1 text-gray-900 dark:text-gray-100`}>
                {items.map((item) => (
                    <li key={item.id} className="pl-2">
                        {item.content || <span className="text-gray-400">空项</span>}
                    </li>
                ))}
            </ListTag>
        </div>
    );
};

export default ListBlock;
