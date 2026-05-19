'use client';

import React from 'react';
import {useEditor, EditorContent} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import ImageExt from '@tiptap/extension-image';
import LinkExt from '@tiptap/extension-link';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import Typography from '@tiptap/extension-typography';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
// @tiptap/extension-table and related exports are ESM with named exports only
import {Table} from '@tiptap/extension-table';
import {TableRow} from '@tiptap/extension-table-row';
import {TableCell} from '@tiptap/extension-table-cell';
import {TableHeader} from '@tiptap/extension-table-header';
import {Bold, Italic, Strikethrough, Code, Heading1, Heading2, Heading3, List, ListOrdered, Quote, Undo, Redo, Image, Link, Table2, CheckSquare, AlignLeft, AlignCenter, AlignRight, Highlighter} from 'lucide-react';

interface RichEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const MenuBtn: React.FC<{onClick: () => void; active?: boolean; title: string; children: React.ReactNode}> = ({onClick, active, title, children}) => (
  <button type="button" onClick={onClick} title={title}
    className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors ${active ? 'bg-gray-200 dark:bg-gray-700 text-blue-600' : 'text-gray-600 dark:text-gray-300'}`}>
    {children}
  </button>
);

const Divider = () => <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1" />;

const RichEditor: React.FC<RichEditorProps> = ({value, onChange, placeholder = '开始写作...'}) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({heading: {levels: [1,2,3]}}),
      Placeholder.configure({placeholder}),
      Underline, Typography,
      TextAlign.configure({types: ['heading', 'paragraph']}),
      Highlight, ImageExt, LinkExt.configure({openOnClick: false}),
      Table.configure({resizable: true}), TableRow, TableCell, TableHeader,
      TaskList, TaskItem.configure({nested: true}),
    ],
    content: value || '',
    onUpdate: ({editor}) => onChange(editor.getHTML()),
    editorProps: {
      attributes: {class: 'prose prose-lg dark:prose-invert max-w-none focus:outline-none min-h-[400px] px-6 py-4'},
    },
  });

  const addImage = () => {const url = prompt('图片 URL:'); if (url && editor) editor.chain().focus().setImage({src: url}).run();};
  const addLink = () => {const url = prompt('链接 URL:'); if (url && editor) editor.chain().focus().setLink({href: url}).run();};
  const addTable = () => editor?.chain().focus().insertTable({rows:3,cols:3,withHeaderRow:true}).run();

  if (!editor) return <div className="h-[400px] bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
        <MenuBtn onClick={() => editor.chain().focus().undo().run()} title="撤销"><Undo className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().redo().run()} title="重做"><Redo className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="粗体"><Bold className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="斜体"><Italic className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="下划线"><span className="text-sm font-bold">U</span></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="删除线"><Strikethrough className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="行内代码"><Code className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleHighlight().run()} active={editor.isActive('highlight')} title="高亮"><Highlighter className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={() => editor.chain().focus().toggleHeading({level:1}).run()} active={editor.isActive('heading',{level:1})} title="标题1"><Heading1 className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleHeading({level:2}).run()} active={editor.isActive('heading',{level:2})} title="标题2"><Heading2 className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleHeading({level:3}).run()} active={editor.isActive('heading',{level:3})} title="标题3"><Heading3 className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="无序列表"><List className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="有序列表"><ListOrdered className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleTaskList().run()} active={editor.isActive('taskList')} title="任务列表"><CheckSquare className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="引用"><Quote className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({textAlign:'left'})} title="左对齐"><AlignLeft className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({textAlign:'center'})} title="居中"><AlignCenter className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={() => editor.chain().focus().setTextAlign('right').run()} active={editor.isActive({textAlign:'right'})} title="右对齐"><AlignRight className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={addImage} title="插入图片"><Image className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={addLink} active={editor.isActive('link')} title="插入链接"><Link className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={addTable} title="插入表格"><Table2 className="w-4 h-4"/></MenuBtn>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
};

export default RichEditor;
