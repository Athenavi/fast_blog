/**
 * Code Block Component with Syntax Highlighting
 * 代码块组件 - 支持语法高亮和复制功能
 */
'use client';

import React, {useState} from 'react';
import {useTheme} from '@/hooks/useTheme';

interface CodeBlockProps {
    code: string;
    language?: string;
    showLineNumbers?: boolean;
    showCopyButton?: boolean;
}

const CodeBlock: React.FC<CodeBlockProps> = ({
                                                 code,
                                                 language = 'plaintext',
                                                 showLineNumbers = true,
                                                 showCopyButton = true,
                                             }) => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = (themeConfig as any).colors || {};
    const features = (themeConfig as any).features || {};

    const [copied, setCopied] = useState(false);

    // 检查是否启用行号和复制按钮
    const shouldShowLineNumbers = showLineNumbers && (features.showCodeLineNumbers ?? true);
    const shouldShowCopyButton = showCopyButton && (features.showCopyButton ?? true);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const lines = code.split('\n');

    return (
        <div
            className="code-block rounded-lg overflow-hidden my-4 transition-colors duration-300"
            style={{
                backgroundColor: colors.code_background || '#1e293b',
                color: colors.code_text || '#e2e8f0',
            }}
        >
            {/* 代码块头部 */}
            {(shouldShowCopyButton || language) && (
                <div
                    className="flex items-center justify-between px-4 py-2 border-b"
                    style={{borderColor: colors.border || '#334155'}}
                >
                    <span className="text-sm opacity-75">{language}</span>
                    {shouldShowCopyButton && (
                        <button
                            onClick={handleCopy}
                            className="text-xs px-3 py-1 rounded hover:opacity-80 transition-opacity"
                            style={{
                                backgroundColor: colors.primary || '#3b82f6',
                                color: '#ffffff',
                            }}
                        >
                            {copied ? '已复制!' : '复制'}
                        </button>
                    )}
                </div>
            )}

            {/* 代码内容 */}
            <div className="overflow-x-auto">
        <pre className="p-4 text-sm leading-relaxed">
          <code className="font-mono">
            {lines.map((line, index) => (
                <div key={index} className="flex">
                    {shouldShowLineNumbers && (
                        <span
                            className="inline-block w-8 text-right mr-4 select-none opacity-50"
                        >
                    {index + 1}
                  </span>
                    )}
                    <span>{line}</span>
                </div>
            ))}
          </code>
        </pre>
            </div>
        </div>
    );
};

export default CodeBlock;
