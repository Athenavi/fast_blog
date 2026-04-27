'use client';

import React from 'react';

interface QuoteBlockProps {
    attributes: {
        content?: string;
        citation?: string;
        style?: 'default' | 'large';
    };
    isSelected?: boolean;
    onChange?: (field: 'content' | 'citation', value: string) => void;
}

/**
 * 引用 Block 组件
 */
const QuoteBlock: React.FC<QuoteBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const content = attributes.content || '';
    const citation = attributes.citation || '';
    const style = attributes.style || 'default';

    const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (onChange) onChange('content', e.target.value);
    };

    const handleCitationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onChange) onChange('citation', e.target.value);
    };

    return (
        <div className={`py-4 ${isSelected ? 'ring-2 ring-blue-500 rounded p-2' : ''}`}>
            {isSelected ? (
                <div className="space-y-3">
                    <textarea
                        value={content}
                        onChange={handleContentChange}
                        className="w-full min-h-[80px] p-3 border-l-4 border-blue-500 bg-gray-50 dark:bg-gray-800 
                            text-gray-900 dark:text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="输入引用内容..."
                    />
                    <input
                        type="text"
                        value={citation}
                        onChange={handleCitationChange}
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                            bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm
                            focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="引用来源..."
                    />
                </div>
            ) : (
                <blockquote className={`border-l-4 border-blue-500 pl-4 py-2 ${
                    style === 'large' ? 'text-xl italic' : 'text-lg italic'
                }`}>
                    <p className="text-gray-700 dark:text-gray-300 mb-2">
                        "{content || <span className="text-gray-400 not-italic">空引用</span>}"
                    </p>
                    {citation && (
                        <footer className="text-sm text-gray-500 dark:text-gray-400">
                            —— {citation}
                        </footer>
                    )}
                </blockquote>
            )}
        </div>
    );
};

export default QuoteBlock;
