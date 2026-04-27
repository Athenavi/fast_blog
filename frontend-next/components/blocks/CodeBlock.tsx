'use client';

import React from 'react';

interface CodeBlockProps {
    attributes: {
        language?: string;
        content?: string;
        show_line_numbers?: boolean;
    };
    isSelected?: boolean;
    onChange?: (field: string, value: any) => void;
}

/**
 * 代码 Block 组件
 */
const CodeBlock: React.FC<CodeBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const language = attributes.language || 'javascript';
    const content = attributes.content || '';
    const showLineNumbers = attributes.show_line_numbers ?? true;

    const languages = [
        'javascript', 'typescript', 'python', 'java', 'cpp', 'csharp',
        'go', 'rust', 'php', 'ruby', 'html', 'css', 'sql', 'bash', 'json'
    ];

    const handleChange = (field: string, value: any) => {
        if (onChange) onChange(field, value);
    };

    if (isSelected) {
        return (
            <div className="py-2 ring-2 ring-blue-500 rounded p-3">
                <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            语言
                        </label>
                        <select
                            value={language}
                            onChange={(e) => handleChange('language', e.target.value)}
                            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {languages.map((lang) => (
                                <option key={lang} value={lang}>{lang}</option>
                            ))}
                        </select>
                    </div>
                    
                    <div className="flex items-end">
                        <label className="flex items-center">
                            <input
                                type="checkbox"
                                checked={showLineNumbers}
                                onChange={(e) => handleChange('show_line_numbers', e.target.checked)}
                                className="mr-2 h-4 w-4 text-blue-600 rounded"
                            />
                            <span className="text-sm text-gray-700 dark:text-gray-300">显示行号</span>
                        </label>
                    </div>
                </div>

                <textarea
                    value={content}
                    onChange={(e) => handleChange('content', e.target.value)}
                    className="w-full min-h-[200px] p-3 font-mono text-sm border border-gray-300 dark:border-gray-600 rounded 
                        bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100
                        focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                    placeholder="// 输入代码..."
                />
            </div>
        );
    }

    // 预览模式 - 简单代码展示
    const lines = content.split('\n');
    
    return (
        <div className="py-2">
            <div className="relative">
                {/* 语言标签 */}
                <div className="absolute top-0 right-0 px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 
                    text-gray-700 dark:text-gray-300 rounded-bl">
                    {language}
                </div>
                
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                    <code className="font-mono text-sm">
                        {lines.map((line, index) => (
                            <div key={index} className="flex">
                                {showLineNumbers && (
                                    <span className="inline-block w-8 text-right mr-4 text-gray-500 select-none">
                                        {index + 1}
                                    </span>
                                )}
                                <span>{line || ' '}</span>
                            </div>
                        ))}
                    </code>
                </pre>
            </div>
        </div>
    );
};

export default CodeBlock;
