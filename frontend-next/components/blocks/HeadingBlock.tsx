'use client';

import React from 'react';

interface HeadingBlockProps {
    attributes: {
        level?: number;
        content?: string;
        align?: 'left' | 'center' | 'right';
    };
    isSelected?: boolean;
    onChange?: (content: string) => void;
}

/**
 * 标题 Block 组件
 */
const HeadingBlock: React.FC<HeadingBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const level = attributes.level || 2;
    const content = attributes.content || '';
    const align = attributes.align || 'left';

    const alignMap: Record<string, string> = {
        left: 'text-left',
        center: 'text-center',
        right: 'text-right',
    };

    const headingMap: Record<number, any> = {
        1: 'h1',
        2: 'h2',
        3: 'h3',
        4: 'h4',
        5: 'h5',
        6: 'h6',
    };

    const sizeMap: Record<number, string> = {
        1: 'text-4xl font-bold',
        2: 'text-3xl font-bold',
        3: 'text-2xl font-semibold',
        4: 'text-xl font-semibold',
        5: 'text-lg font-medium',
        6: 'text-base font-medium',
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onChange) {
            onChange(e.target.value);
        }
    };

    const HeadingTag = headingMap[level] || 'h2';

    return (
        <div className={`py-2 ${isSelected ? 'ring-2 ring-blue-500 rounded p-2' : ''}`}>
            {isSelected ? (
                <div className="space-y-2">
                    <div className="flex gap-2">
                        {[1, 2, 3, 4, 5, 6].map((l) => (
                            <button
                                key={l}
                                onClick={() => onChange && onChange(content)} // 触发更新以改变level
                                className={`px-2 py-1 text-sm rounded ${
                                    level === l 
                                        ? 'bg-blue-500 text-white' 
                                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                                }`}
                            >
                                H{l}
                            </button>
                        ))}
                    </div>
                    <input
                        type="text"
                        value={content}
                        onChange={handleChange}
                        className={`w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                            bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                            focus:outline-none focus:ring-2 focus:ring-blue-500 ${sizeMap[level]}`}
                        placeholder={`H${level} 标题内容...`}
                    />
                </div>
            ) : (
                <HeadingTag className={`${sizeMap[level]} ${alignMap[align]} text-gray-900 dark:text-gray-100`}>
                    {content || <span className="text-gray-400 italic">空标题</span>}
                </HeadingTag>
            )}
        </div>
    );
};

export default HeadingBlock;
