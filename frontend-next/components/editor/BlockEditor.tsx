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
import {all, createLowlight} from 'lowlight';
import {SlashMenu} from './SlashMenu';
import {MediaFile} from '@/lib/api';
import {getMediaUrlSync} from '@/lib/media-url';
import MediaSelectorModal from '@/components/ui/MediaSelectorModal';
import AIAssistant from '@/components/AIAssistant';

const lowlight = createLowlight(all);

interface BlockEditorProps {
    value: string;
    onChange: (value: string) => void;
    minHeight?: string;
    maxHeight?: string;
    placeholder?: string;
    disabled?: boolean;
}

export default function BlockEditor({
                                        value,
                                        onChange,
                                        minHeight = '400px',
                                        maxHeight = '800px',
                                        placeholder = '输入 "/" 唤起块菜单...',
                                        disabled = false
                                    }: BlockEditorProps) {
    const [showSlashMenu, setShowSlashMenu] = useState(false);
    const [slashMenuPosition, setSlashMenuPosition] = useState({x: 0, y: 0});
    const [showMediaSelector, setShowMediaSelector] = useState(false);
    const [mediaType, setMediaType] = useState<'image' | 'video' | 'all'>('image');
    const [showAIAssistant, setShowAIAssistant] = useState(false);
    const [selectedText, setSelectedText] = useState('');

    // 防抖定时器
    const changeTimerRef = React.useRef<NodeJS.Timeout | null>(null);

    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit.configure({
                codeBlock: false,
            }),
            Link.configure({
                openOnClick: false,
                HTMLAttributes: {
                    class: 'text-blue-600 underline',
                },
            }),
            Image.configure({
                HTMLAttributes: {
                    class: 'max-w-full h-auto rounded-lg my-4',
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
            TaskList,
            TaskItem.configure({
                nested: true,
            }),
            Placeholder.configure({
                placeholder: () => placeholder,
            }),
            Typography,
            Dropcursor,
            Gapcursor,
        ],
        content: value,
        editable: !disabled,
        editorProps: {
            attributes: {
                class: `prose prose-sm sm:prose lg:prose-lg xl:prose-xl focus:outline-none min-h-[${minHeight}] max-h-[${maxHeight}] overflow-y-auto p-4`,
            },
            handleKeyDown: (view, event) => {
                // 检测 "/" 键
                if (event.key === '/') {
                    const {state} = view;
                    const {selection} = state;
                    const coords = view.coordsAtPos(selection.from);

                    setSlashMenuPosition({
                        x: coords.left,
                        y: coords.bottom + window.scrollY
                    });
                    setShowSlashMenu(true);
                }

                // ESC关闭菜单
                if (event.key === 'Escape') {
                    setShowSlashMenu(false);
                }

                return false;
            },
            handleClick: () => {
                setShowSlashMenu(false);
            },
        },
        onUpdate: ({editor}) => {
            // 防抖处理，300ms后触发onChange
            if (changeTimerRef.current) {
                clearTimeout(changeTimerRef.current);
            }

            changeTimerRef.current = setTimeout(() => {
                const html = editor.getHTML();
                onChange(html);
            }, 300);
        },
    });

    // 同步外部value变化
    useEffect(() => {
        if (editor && value !== editor.getHTML()) {
            editor.commands.setContent(value);
        }
    }, [value, editor]);

    // 清理定时器
    useEffect(() => {
        return () => {
            if (changeTimerRef.current) {
                clearTimeout(changeTimerRef.current);
            }
        };
    }, []);

    // 插入块类型
    const insertBlock = useCallback((blockType: string) => {
        if (!editor) return;

        switch (blockType) {
            case 'heading1':
                editor.chain().focus().toggleHeading({level: 1}).run();
                break;
            case 'heading2':
                editor.chain().focus().toggleHeading({level: 2}).run();
                break;
            case 'heading3':
                editor.chain().focus().toggleHeading({level: 3}).run();
                break;
            case 'bulletList':
                editor.chain().focus().toggleBulletList().run();
                break;
            case 'orderedList':
                editor.chain().focus().toggleOrderedList().run();
                break;
            case 'taskList':
                (editor.chain().focus() as any).toggleTaskList().run();
                break;
            case 'quote':
                editor.chain().focus().toggleBlockquote().run();
                break;
            case 'codeBlock':
                editor.chain().focus().toggleCodeBlock().run();
                break;
            case 'divider':
                editor.chain().focus().setHorizontalRule().run();
                break;
            case 'table':
                editor.chain().focus().insertTable({
                    rows: 3,
                    cols: 3,
                    withHeaderRow: true
                }).run();
                break;
            case 'image':
                setMediaType('image');
                setShowMediaSelector(true);
                break;
            case 'video':
                setMediaType('video');
                setShowMediaSelector(true);
                break;
        }

        setShowSlashMenu(false);
    }, [editor]);

    // 插入媒体文件
    const handleMediaSelect = useCallback((media: MediaFile | MediaFile[]) => {
        if (!editor) return;

        const mediaFiles = Array.isArray(media) ? media : [media];

        mediaFiles.forEach((file) => {
            const mediaUrl = getMediaUrlSync(String(file.id));

            if (file.mime_type.startsWith('image/')) {
                editor.chain().focus().setImage({
                    src: mediaUrl,
                    alt: file.original_filename
                }).run();
            } else if (file.mime_type.startsWith('video/')) {
                const videoHtml = `<video controls src="${mediaUrl}" class="max-w-full rounded-lg my-4"></video>`;
                editor.chain().focus().insertContent(videoHtml).run();
            }
        });

        setShowMediaSelector(false);
    }, [editor]);

    // AI助手 - 插入文本
    const handleAIInsert = useCallback((text: string) => {
        if (!editor) return;
        editor.chain().focus().insertContent(text).run();
        setShowAIAssistant(false);
    }, [editor]);

    // AI助手 - 替换选中文本
    const handleAIReplace = useCallback((text: string) => {
        if (!editor) return;
        editor.chain().focus().deleteSelection().insertContent(text).run();
        setShowAIAssistant(false);
    }, [editor]);

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
        <div className="relative">
            {/* Slash命令菜单 */}
            {showSlashMenu && (
                <SlashMenu
                    position={slashMenuPosition}
                    onSelect={insertBlock}
                    onClose={() => setShowSlashMenu(false)}
                />
            )}

            {/* 浮动菜单 - 选中文本时显示 */}
            {/* TODO: Tiptap v3 FloatingMenu API需要调整
            <FloatingMenu
                editor={editor}
                tippyOptions={{
                    duration: 100,
                    placement: 'top',
                }}
                className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg p-2 flex gap-1"
            >
                <button
                    type="button"
                    onClick={() => editor.chain().focus().toggleBold().run()}
                    className={`p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        editor.isActive('bold') ? 'bg-blue-100 dark:bg-blue-900 text-blue-600' : ''
                    }`}
                    title="粗体"
                >
                    <strong>B</strong>
                </button>
                <button
                    type="button"
                    onClick={() => editor.chain().focus().toggleItalic().run()}
                    className={`p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        editor.isActive('italic') ? 'bg-blue-100 dark:bg-blue-900 text-blue-600' : ''
                    }`}
                    title="斜体"
                >
                    <em>I</em>
                </button>
                <button
                    type="button"
                    onClick={() => editor.chain().focus().toggleLink({href: ''}).run()}
                    className={`p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        editor.isActive('link') ? 'bg-blue-100 dark:bg-blue-900 text-blue-600' : ''
                    }`}
                    title="链接"
                >
                    🔗
                </button>
                <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1"/>
                <button
                    type="button"
                    onClick={() => {
                        const selection = editor.state.selection;
                        const text = editor.state.doc.textBetween(selection.from, selection.to);
                        if (text) {
                            setSelectedText(text);
                            setShowAIAssistant(true);
                        }
                    }}
                    className="p-2 rounded hover:bg-purple-100 dark:hover:bg-purple-900 text-purple-600"
                    title="AI助手"
                >
                    ✨ AI
                </button>
            </FloatingMenu>
            */}

            {/* 编辑器内容 */}
            <EditorContent editor={editor}/>

            {/* 媒体选择器 */}
            <MediaSelectorModal
                isOpen={showMediaSelector}
                onClose={() => setShowMediaSelector(false)}
                onSelect={handleMediaSelect}
                allowedTypes={[mediaType === 'all' ? 'image' : mediaType]}
            />

            {/* AI助手 */}
            {showAIAssistant && (
                <AIAssistant
                    selectedText={selectedText}
                    context={editor.getHTML()}
                    onInsert={handleAIInsert}
                    onReplace={handleAIReplace}
                    onClose={() => setShowAIAssistant(false)}
                />
            )}

            {/* 提示信息 */}
            <div
                className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-900 dark:text-blue-100">
                    💡 <strong>提示：</strong>输入 <kbd
                    className="px-2 py-1 bg-white dark:bg-gray-800 rounded border">/</kbd> 可以快速插入块（标题、列表、图片等）
                </p>
                <p className="text-xs text-blue-700 dark:text-blue-300 mt-2">
                    📱 <strong>移动端：</strong>长按文本可选择，工具栏会自动显示
                </p>
            </div>
        </div>
    );
}
