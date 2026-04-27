'use client';

import React, {useCallback, useEffect, useState} from 'react';
import {EditorContent, useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import TextAlign from '@tiptap/extension-text-align';
import Underline from '@tiptap/extension-underline';
import {TextStyle} from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import Highlight from '@tiptap/extension-highlight';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import {Table} from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Placeholder from '@tiptap/extension-placeholder';
import Typography from '@tiptap/extension-typography';
import Dropcursor from '@tiptap/extension-dropcursor';
import Gapcursor from '@tiptap/extension-gapcursor';
import {common, createLowlight} from 'lowlight';
import MediaSelectorModal from '@/components/ui/MediaSelectorModal';
import type {MediaFile} from '@/lib/api';
import {getMediaUrlSync} from '@/lib/media-url';

// 创建语法高亮
const lowlight = createLowlight(common);

interface RichTextEditorProps {
    value: string;
    onChange: (value: string) => void;
    minHeight?: string;
    maxHeight?: string;
    placeholder?: string;
    disabled?: boolean;
    mode?: 'wysiwyg' | 'markdown' | 'both'; // 编辑器模式
    showPreview?: boolean; // 是否显示预览面板
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
                                                           value,
                                                           onChange,
                                                           minHeight = '400px',
                                                           maxHeight = '800px',
                                                           placeholder = '开始编写您的文章...',
                                                           disabled = false,
                                                           mode = 'wysiwyg',
                                                           showPreview = false
                                                       }) => {
    const [showMediaSelector, setShowMediaSelector] = useState(false);
    const [mediaType, setMediaType] = useState<'image' | 'video' | 'all'>('image');
    const [editorMode, setEditorMode] = useState<'visual' | 'code'>(mode === 'markdown' ? 'code' : 'visual');

    const editor = useEditor({
        immediatelyRender: false, // 避免SSR水合不匹配
        extensions: [
            StarterKit.configure({
                codeBlock: false, // 使用带语法高亮的代码块
            }),
            Link.configure({
                openOnClick: false,
                HTMLAttributes: {
                    class: 'text-blue-600 underline',
                },
            }),
            Image.configure({
                HTMLAttributes: {
                    class: 'max-w-full h-auto rounded-lg',
                },
            }),
            TextAlign.configure({
                types: ['heading', 'paragraph'],
            }),
            Underline,
            TextStyle,
            Color,
            Highlight.configure({
                multicolor: true,
            }),
            CodeBlockLowlight.configure({
                lowlight,
            }),
            Table.configure({
                resizable: true,
            }),
            TableRow,
            TableHeader,
            TableCell,
            // 新增块类型
            TaskList,
            TaskItem.configure({
                nested: true,
            }),
            Placeholder.configure({
                placeholder: () => {
                    return placeholder;
                },
            }),
            Typography, // 自动转换特殊字符
            Dropcursor, // 拖拽指示器
            Gapcursor, // 间隙光标
        ],
        content: value,
        editable: !disabled,
        editorProps: {
            attributes: {
                class: `prose prose-sm sm:prose lg:prose-lg xl:prose-xl focus:outline-none min-h-[${minHeight}] max-h-[${maxHeight}] overflow-y-auto p-4`,
            },
        },
        onUpdate: ({editor}) => {
            const html = editor.getHTML();
            onChange(html);
        },
    });

    // 同步外部value变化
    useEffect(() => {
        if (editor && value !== editor.getHTML()) {
            editor.commands.setContent(value);
        }
    }, [value, editor]);

    // 插入媒体文件
    const handleMediaSelect = useCallback((media: MediaFile | MediaFile[]) => {
        if (!editor) return;

        const mediaFiles = Array.isArray(media) ? media : [media];

        mediaFiles.forEach((file) => {
            const mediaUrl = getMediaUrlSync(String(file.id));

            if (file.mime_type.startsWith('image/')) {
                editor.chain().focus().setImage({src: mediaUrl, alt: file.original_filename}).run();
            } else if (file.mime_type.startsWith('video/')) {
                const videoHtml = `<video controls src="${mediaUrl}"></video>`;
                editor.chain().focus().insertContent(videoHtml).run();
            } else if (file.mime_type.startsWith('audio/')) {
                const audioHtml = `<audio controls src="${mediaUrl}"></audio>`;
                editor.chain().focus().insertContent(audioHtml).run();
            }
        });

        setShowMediaSelector(false);
    }, [editor]);

    // 工具栏按钮组件
    const ToolbarButton = ({
                               onClick,
                               active,
                               disabled,
                               title,
                               children
                           }: {
        onClick: () => void;
        active?: boolean;
        disabled?: boolean;
        title: string;
        children: React.ReactNode;
    }) => (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            title={title}
            className={`p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                active ? 'bg-blue-100 dark:bg-blue-900 text-blue-600' : 'text-gray-700 dark:text-gray-300'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
            {children}
        </button>
    );

    if (!editor) {
        return (
            <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-center">
                    <div
                        className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载编辑器中...</p>
                </div>
            </div>
        );
    }

    return (
        <div
            className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white dark:bg-gray-900">
            {/* 工具栏 */}
            <div
                className="border-b border-gray-300 dark:border-gray-600 p-2 bg-gray-50 dark:bg-gray-800 flex flex-wrap gap-1">
                {/* 文本格式 */}
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleBold().run()}
                    active={editor.isActive('bold')}
                    title="粗体"
                >
                    <strong>B</strong>
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleItalic().run()}
                    active={editor.isActive('italic')}
                    title="斜体"
                >
                    <em>I</em>
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleUnderline().run()}
                    active={editor.isActive('underline')}
                    title="下划线"
                >
                    <u>U</u>
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleStrike().run()}
                    active={editor.isActive('strike')}
                    title="删除线"
                >
                    <s>S</s>
                </ToolbarButton>

                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>

                {/* 标题 */}
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleHeading({level: 1}).run()}
                    active={editor.isActive('heading', {level: 1})}
                    title="标题1"
                >
                    H1
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleHeading({level: 2}).run()}
                    active={editor.isActive('heading', {level: 2})}
                    title="标题2"
                >
                    H2
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleHeading({level: 3}).run()}
                    active={editor.isActive('heading', {level: 3})}
                    title="标题3"
                >
                    H3
                </ToolbarButton>

                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>

                {/* 列表 */}
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleBulletList().run()}
                    active={editor.isActive('bulletList')}
                    title="无序列表"
                >
                    • List
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleOrderedList().run()}
                    active={editor.isActive('orderedList')}
                    title="有序列表"
                >
                    1. List
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => (editor.chain().focus() as any).toggleTaskList().run()}
                    active={editor.isActive('taskList')}
                    title="任务列表"
                >
                    ☑️ Task
                </ToolbarButton>

                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>

                {/* 对齐 */}
                <ToolbarButton
                    onClick={() => editor.chain().focus().setTextAlign('left').run()}
                    active={editor.isActive({textAlign: 'left'})}
                    title="左对齐"
                >
                    ←
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().setTextAlign('center').run()}
                    active={editor.isActive({textAlign: 'center'})}
                    title="居中对齐"
                >
                    ↔
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().setTextAlign('right').run()}
                    active={editor.isActive({textAlign: 'right'})}
                    title="右对齐"
                >
                    →
                </ToolbarButton>

                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>

                {/* 插入 */}
                <ToolbarButton
                    onClick={() => {
                        setMediaType('image');
                        setShowMediaSelector(true);
                    }}
                    title="插入图片"
                >
                    🖼️
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => {
                        const url = window.prompt('输入链接URL:');
                        if (url) {
                            editor.chain().focus().setLink({href: url}).run();
                        }
                    }}
                    active={editor.isActive('link')}
                    title="插入链接"
                >
                    🔗
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                    active={editor.isActive('codeBlock')}
                    title="代码块"
                >
                    {'</>'}
                </ToolbarButton>

                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>

                {/* 其他 */}
                <ToolbarButton
                    onClick={() => editor.chain().focus().toggleBlockquote().run()}
                    active={editor.isActive('blockquote')}
                    title="引用"
                >
                    ❝
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => editor.chain().focus().setHorizontalRule().run()}
                    title="水平线"
                >
                    —
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => {
                        const url = window.prompt('输入视频URL:');
                        if (url) {
                            const videoHtml = `<video controls src="${url}" class="max-w-full rounded-lg"></video>`;
                            editor.chain().focus().insertContent(videoHtml).run();
                        }
                    }}
                    title="插入视频"
                >
                    🎥
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => {
                        const url = window.prompt('输入音频URL:');
                        if (url) {
                            const audioHtml = `<audio controls src="${url}" class="w-full"></audio>`;
                            editor.chain().focus().insertContent(audioHtml).run();
                        }
                    }}
                    title="插入音频"
                >
                    🎵
                </ToolbarButton>
                <ToolbarButton
                    onClick={() => {
                        const columns = window.prompt('列数:', '2');
                        if (columns && parseInt(columns) > 0) {
                            editor.chain().focus().insertTable({
                                rows: 3,
                                cols: parseInt(columns),
                                withHeaderRow: true
                            }).run();
                        }
                    }}
                    title="插入表格"
                >
                    📊
                </ToolbarButton>

                <div className="flex-1"/>

                {/* 预览切换按钮 */}
                <ToolbarButton
                    onClick={() => {
                    }} // 这个功能需要在父组件控制
                    active={showPreview}
                    title={showPreview ? '关闭预览' : '分屏预览'}
                >
                    {showPreview ? '👁️❌' : '👁️'}
                </ToolbarButton>

                {/* 模式切换 */}
                {mode === 'both' && (
                    <div className="flex gap-1">
                        <ToolbarButton
                            onClick={() => setEditorMode('visual')}
                            active={editorMode === 'visual'}
                            title="可视化编辑"
                        >
                            👁️
                        </ToolbarButton>
                        <ToolbarButton
                            onClick={() => setEditorMode('code')}
                            active={editorMode === 'code'}
                            title="源代码"
                        >
                            {'</>'}
                        </ToolbarButton>
                    </div>
                )}
            </div>

            {/* 编辑器内容区域 */}
            {showPreview ? (
                // 分屏预览模式
                <div className="grid grid-cols-2 gap-0 h-[600px]">
                    {/* 左侧编辑区 */}
                    <div className="border-r border-gray-300 dark:border-gray-600 overflow-y-auto">
                        {editorMode === 'visual' ? (
                            <EditorContent editor={editor} className="min-h-full p-4"/>
                        ) : (
                            <textarea
                                value={value}
                                onChange={(e) => onChange(e.target.value)}
                                className="w-full h-full p-4 font-mono text-sm bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none focus:outline-none"
                                placeholder={placeholder}
                            />
                        )}
                    </div>

                    {/* 右侧预览区 */}
                    <div className="overflow-y-auto bg-white dark:bg-gray-900">
                        <div
                            className="p-4 prose prose-sm sm:prose lg:prose-lg xl:prose-xl dark:prose-invert max-w-none">
                            <div dangerouslySetInnerHTML={{__html: value}}/>
                        </div>
                    </div>
                </div>
            ) : (
                // 单栏编辑模式
                editorMode === 'visual' ? (
                    <>
                        <EditorContent editor={editor} className="min-h-[400px]"/>
                    </>
                ) : (
                    <textarea
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        className="w-full h-[400px] p-4 font-mono text-sm bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none focus:outline-none"
                        placeholder={placeholder}
                    />
                )
            )}

            {/* 媒体选择器 */}
            <MediaSelectorModal
                isOpen={showMediaSelector}
                onClose={() => setShowMediaSelector(false)}
                onSelect={handleMediaSelect}
                allowedTypes={[mediaType === 'all' ? 'image' : mediaType]}
            />
        </div>
    );
};

export default RichTextEditor;
