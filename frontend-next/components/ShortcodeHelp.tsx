'use client';

import React from 'react';

interface ShortcodeHelpProps {
    shortcodeName?: string;
}

/**
 * Shortcode帮助组件
 * 显示短代码使用说明和示例
 */
const ShortcodeHelp: React.FC<ShortcodeHelpProps> = ({shortcodeName}) => {
    const shortcodes = [
        {
            name: 'gallery',
            description: '图片画廊',
            usage: '[gallery ids="1,2,3" columns="3"]',
            example: '[gallery ids="1,2,3,4" columns="2"]'
        },
        {
            name: 'embed',
            description: '嵌入视频',
            usage: '[embed url="https://youtube.com/watch?v=<video-id>"]',
            example: '[embed]https://www.youtube.com/watch?v=dQw4w9WgXcQ[/embed]'
        },
        {
            name: 'button',
            description: '按钮',
            usage: '[button url="#" style="primary"]Text[/button]',
            example: '[button url="/contact" style="primary"]联系我们[/button]'
        },
        {
            name: 'columns',
            description: '分栏布局',
            usage: '[columns count="2"][column]Content[/column][/columns]',
            example: `[columns count="2"]
[column span="1"]左侧内容[/column]
[column span="1"]右侧内容[/column]
[/columns]`
        },
        {
            name: 'caption',
            description: '图片说明',
            usage: '[caption align="center"]Caption text[/caption]',
            example: '[caption align="center"]这是一张图片的说明[/caption]'
        }
    ];

    const filteredShortcodes = shortcodeName
        ? shortcodes.filter(s => s.name === shortcodeName)
        : shortcodes;

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-semibold">Shortcode 短代码</h3>
            
            <div className="grid gap-4">
                {filteredShortcodes.map((shortcode) => (
                    <div key={shortcode.name} className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
                        <div className="flex items-center gap-2 mb-2">
                            <code className="text-blue-600 dark:text-blue-400 font-bold">
                                [{shortcode.name}]
                            </code>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                                {shortcode.description}
                            </span>
                        </div>
                        
                        <div className="space-y-2">
                            <div>
                                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">用法:</p>
                                <code className="block bg-white dark:bg-gray-900 p-2 rounded text-sm overflow-x-auto">
                                    {shortcode.usage}
                                </code>
                            </div>
                            
                            <div>
                                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">示例:</p>
                                <pre className="block bg-white dark:bg-gray-900 p-2 rounded text-sm overflow-x-auto whitespace-pre-wrap">
                                    {shortcode.example}
                                </pre>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
            
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>提示:</strong> Shortcode可以嵌套使用,例如在columns中使用button。
                    确保正确闭合所有标签。
                </p>
            </div>
        </div>
    );
};

export default ShortcodeHelp;
