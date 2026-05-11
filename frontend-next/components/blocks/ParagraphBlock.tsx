'use client';

import React from 'react';

interface ParagraphBlockProps {
    attributes: {
        content?: string;
        align?: 'left' | 'center' | 'right';
    };
    isSelected?: boolean;
    onChange?: (content: string) => void;
}

/**
 * 段落 Block 组件
 */
const ParagraphBlock: React.FC<ParagraphBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const content = attributes.content || '';
    const align = attributes.align || 'left';

    const alignMap: Record<string, string> = {
        left: 'text-left',
        center: 'text-center',
        right: 'text-right',
    };

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (onChange) {
            onChange(e.target.value);
        }
    };

    return (
        <div className={`py-2 ${isSelected ? 'ring-2 ring-blue-500 rounded p-2' : ''}`}>
            {isSelected ? (
                <textarea
                    value={content}
                    onChange={handleChange}
                    className={`w-full min-h-[100px] p-2 border border-gray-300 dark:border-gray-600 rounded 
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-y
                        focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    placeholder="输入段落内容..."
                />
            ) : (
                <p className={`${alignMap[align]} text-gray-900 dark:text-gray-100 leading-relaxed whitespace-pre-wrap`}>
                    {content || <span className="text-gray-400 italic">空段落</span>}
                </p>
            )}
        </div>
    );
};

export default ParagraphBlock;
