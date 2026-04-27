'use client';

import React, {useEffect, useState} from 'react';
import dynamic from 'next/dynamic';
import OptimizedMarkdownEditor from './OptimizedMarkdownEditor';

// 动态导入富文本编辑器(只在客户端加载)
const RichTextEditor = dynamic(
    () => import('./RichTextEditor'),
    {
        ssr: false,
        loading: () => (
            <div
                className="h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg">
                <div className="text-center">
                    <div
                        className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载编辑器中...</p>
                </div>
            </div>
        )
    }
);

// 动态导入块编辑器
const BlockEditor = dynamic(
    () => import('./BlockEditor'),
    {
        ssr: false,
        loading: () => (
            <div
                className="h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg">
                <div className="text-center">
                    <div
                        className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载块编辑器中...</p>
                </div>
            </div>
        )
    }
);

interface UniversalEditorProps {
    value: string;
    onChange: (value: string) => void;
    defaultMode?: 'markdown' | 'wysiwyg' | 'block'; // 添加块编辑器模式
    allowSwitch?: boolean; // 是否允许切换模式
    minHeight?: string;
    maxHeight?: string;
    placeholder?: string;
    disabled?: boolean;
    onInsertMedia?: (media: any) => void; // 媒体插入回调
    showPreview?: boolean; // 是否显示预览面板
    onTogglePreview?: () => void; // 切换预览回调
}

const UniversalEditor: React.FC<UniversalEditorProps> = ({
                                                             value,
                                                             onChange,
                                                             defaultMode = 'block', // 默认使用块编辑器
                                                             allowSwitch = true,
                                                             minHeight,
                                                             maxHeight,
                                                             placeholder,
                                                             disabled,
                                                             onInsertMedia,
                                                             showPreview = false,
                                                             onTogglePreview
                                                         }) => {
    const [editorMode, setEditorMode] = useState<'markdown' | 'wysiwyg' | 'block'>(defaultMode);
    const [markdownValue, setMarkdownValue] = useState(value);
    const [htmlValue, setHtmlValue] = useState(value);

    // 当外部value变化时,根据当前模式更新对应的值
    useEffect(() => {
        if (editorMode === 'markdown') {
            setMarkdownValue(value);
        } else {
            setHtmlValue(value);
        }
    }, [value, editorMode]);

    // 处理Markdown编辑器变化
    const handleMarkdownChange = (markdown: string) => {
        setMarkdownValue(markdown);
        onChange(markdown);
    };

    // 处理富文本编辑器变化
    const handleHtmlChange = (html: string) => {
        setHtmlValue(html);
        onChange(html);
    };

    // 切换编辑器模式
    const handleModeSwitch = () => {
        if (editorMode === 'markdown') {
            // 从Markdown切换到块编辑器
            setEditorMode('block');
        } else if (editorMode === 'block') {
            // 从块编辑器切换到富文本
            setEditorMode('wysiwyg');
        } else {
            // 从富文本切换到Markdown
            setEditorMode('markdown');
        }
    };

    return (
        <div className="space-y-2">
            {/* 模式切换和预览按钮 */}
            {(allowSwitch || onTogglePreview) && (
                <div className="flex justify-end gap-2">
                    {onTogglePreview && (
                        <button
                            type="button"
                            onClick={onTogglePreview}
                            className={`px-3 py-1 text-sm rounded-md transition-colors ${
                                showPreview
                                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                                    : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300'
                            }`}
                        >
                            {showPreview ? '👁️❌ 关闭预览' : '👁️ 分屏预览'}
                        </button>
                    )}
                    {allowSwitch && (
                        <button
                            type="button"
                            onClick={handleModeSwitch}
                            className="px-3 py-1 text-sm rounded-md bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-gray-700 dark:text-gray-300"
                        >
                            {editorMode === 'markdown' ? '切换到块编辑器' :
                                editorMode === 'block' ? '切换到富文本' : '切换到Markdown'}
                        </button>
                    )}
                </div>
            )}

            {/* 编辑器 */}
            {editorMode === 'markdown' ? (
                <OptimizedMarkdownEditor
                    value={markdownValue}
                    onChange={handleMarkdownChange}
                    minHeight={minHeight}
                    maxHeight={maxHeight}
                    placeholder={placeholder}
                    disabled={disabled}
                />
            ) : editorMode === 'block' ? (
                <BlockEditor
                    value={htmlValue}
                    onChange={handleHtmlChange}
                    minHeight={minHeight}
                    maxHeight={maxHeight}
                    placeholder={placeholder}
                    disabled={disabled}
                />
            ) : (
                <RichTextEditor
                    value={htmlValue}
                    onChange={handleHtmlChange}
                    minHeight={minHeight}
                    maxHeight={maxHeight}
                    placeholder={placeholder}
                    disabled={disabled}
                    mode="wysiwyg"
                    showPreview={showPreview}
                />
            )}

            {/* 提示信息 */}
            {editorMode === 'wysiwyg' && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                    💡 提示: 使用可视化工具栏格式化文本,或点击"切换到Markdown"使用Markdown语法
                </p>
            )}
            {editorMode === 'block' && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                    💡 提示: 输入 "/" 可以快速插入各种块类型（标题、列表、图片等）
                </p>
            )}
        </div>
    );
};

export default UniversalEditor;
