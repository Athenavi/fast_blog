'use client';

import React from 'react';
import Link from 'next/link';

interface ButtonBlockProps {
    attributes: {
        text?: string;
        url?: string;
        style?: 'primary' | 'secondary' | 'outline';
        size?: 'small' | 'medium' | 'large';
        open_in_new_tab?: boolean;
    };
    isSelected?: boolean;
    onChange?: (field: string, value: any) => void;
}

/**
 * 按钮 Block 组件
 */
const ButtonBlock: React.FC<ButtonBlockProps> = ({ 
    attributes, 
    isSelected,
    onChange 
}) => {
    const text = attributes.text || '点击我';
    const url = attributes.url || '#';
    const style = attributes.style || 'primary';
    const size = attributes.size || 'medium';
    const openInNewTab = attributes.open_in_new_tab || false;

    const sizeMap: Record<string, string> = {
        small: 'px-3 py-1.5 text-sm',
        medium: 'px-4 py-2 text-base',
        large: 'px-6 py-3 text-lg',
    };

    const styleMap: Record<string, string> = {
        primary: 'bg-blue-600 hover:bg-blue-700 text-white',
        secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
        outline: 'border-2 border-blue-600 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20',
    };

    const handleChange = (field: string, value: any) => {
        if (onChange) onChange(field, value);
    };

    const buttonClasses = `inline-block rounded transition-colors duration-200 font-medium ${sizeMap[size]} ${styleMap[style]}`;

    return (
        <div className={`py-4 ${isSelected ? 'ring-2 ring-blue-500 rounded p-2' : ''}`}>
            {isSelected ? (
                <div className="space-y-3">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            按钮文本
                        </label>
                        <input
                            type="text"
                            value={text}
                            onChange={(e) => handleChange('text', e.target.value)}
                            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            链接URL
                        </label>
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => handleChange('url', e.target.value)}
                            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="https://example.com"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                样式
                            </label>
                            <select
                                value={style}
                                onChange={(e) => handleChange('style', e.target.value)}
                                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                                    bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="primary">主要</option>
                                <option value="secondary">次要</option>
                                <option value="outline">边框</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                尺寸
                            </label>
                            <select
                                value={size}
                                onChange={(e) => handleChange('size', e.target.value)}
                                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded 
                                    bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="small">小</option>
                                <option value="medium">中</option>
                                <option value="large">大</option>
                            </select>
                        </div>
                    </div>

                    <label className="flex items-center">
                        <input
                            type="checkbox"
                            checked={openInNewTab}
                            onChange={(e) => handleChange('open_in_new_tab', e.target.checked)}
                            className="mr-2 h-4 w-4 text-blue-600 rounded"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">在新标签页打开</span>
                    </label>
                </div>
            ) : (
                <div className="text-center">
                    {url.startsWith('/') || url.startsWith('#') ? (
                        <Link href={url} className={buttonClasses}>
                            {text}
                        </Link>
                    ) : (
                        <a 
                            href={url} 
                            target={openInNewTab ? '_blank' : '_self'}
                            rel={openInNewTab ? 'noopener noreferrer' : undefined}
                            className={buttonClasses}
                        >
                            {text}
                        </a>
                    )}
                </div>
            )}
        </div>
    );
};

export default ButtonBlock;
