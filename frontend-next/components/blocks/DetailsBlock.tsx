'use client';

import React, {useState} from 'react';

interface DetailsBlockProps {
    attributes: {
        title?: string;
        content?: string;
        defaultOpen?: boolean;
        style?: 'default' | 'info' | 'warning' | 'success';
    };
    isSelected?: boolean;
    onChange?: (attributes: any) => void;
}

/**
 * 折叠块组件（Details/Summary）
 * 支持展开/收起动画和多种样式
 */
const DetailsBlock: React.FC<DetailsBlockProps> = ({
                                                       attributes,
                                                       isSelected,
                                                       onChange
                                                   }) => {
    const [isOpen, setIsOpen] = useState(attributes.defaultOpen || false);

    const title = attributes.title || '点击展开';
    const content = attributes.content || '';
    const style = attributes.style || 'default';

    // 样式映射
    const styleClasses = {
        info: 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20',
        warning: 'border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
        success: 'border-l-4 border-green-500 bg-green-50 dark:bg-green-900/20',
        default: 'border-l-4 border-gray-300 dark:border-gray-600'
    };

    const containerClass = `${styleClasses[style]} p-4 rounded-lg my-4 ${isSelected ? 'ring-2 ring-blue-500' : ''}`;

    const handleToggle = () => {
        const newIsOpen = !isOpen;
        setIsOpen(newIsOpen);

        // 通知父组件状态变化
        if (onChange) {
            onChange({
                ...attributes,
                defaultOpen: newIsOpen
            });
        }
    };

    const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onChange) {
            onChange({
                ...attributes,
                title: e.target.value
            });
        }
    };

    const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (onChange) {
            onChange({
                ...attributes,
                content: e.target.value
            });
        }
    };

    return (
        <div className={containerClass}>
            {isSelected ? (
                // 编辑模式
                <div className="space-y-3">
                    <input
                        type="text"
                        value={title}
                        onChange={handleTitleChange}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded 
                            bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                            focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="输入标题..."
                    />
                    <textarea
                        value={content}
                        onChange={handleContentChange}
                        className="w-full min-h-[100px] px-3 py-2 border border-gray-300 dark:border-gray-600 rounded 
                            bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 resize-y
                            focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="输入折叠内容..."
                    />
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-600 dark:text-gray-400">默认状态:</span>
                        <button
                            type="button"
                            onClick={() => setIsOpen(!isOpen)}
                            className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                        >
                            {isOpen ? '收起' : '展开'}
                        </button>
                    </div>
                </div>
            ) : (
                // 预览模式 - 使用原生 details/summary 元素
                <details open={isOpen} onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}>
                    <summary
                        onClick={handleToggle}
                        className="cursor-pointer font-semibold text-gray-900 dark:text-gray-100 
                            hover:text-blue-600 dark:hover:text-blue-400 transition-colors select-none
                            list-none flex items-center justify-between"
                    >
                        <span>{title}</span>
                        <svg
                            className={`w-5 h-5 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
                        </svg>
                    </summary>
                    <div className="mt-3 text-gray-700 dark:text-gray-300 leading-relaxed animate-fadeIn">
                        {content}
                    </div>
                </details>
            )}
        </div>
    );
};

export default DetailsBlock;
