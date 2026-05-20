'use client';

import React, {useState, useCallback} from 'react';
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
import {Table} from '@tiptap/extension-table';
import {TableRow} from '@tiptap/extension-table-row';
import {TableCell} from '@tiptap/extension-table-cell';
import {TableHeader} from '@tiptap/extension-table-header';
import {Bold, Italic, Strikethrough, Code, Heading1, Heading2, Heading3, List, ListOrdered, Quote, Undo, Redo, Image, Link, Table2, CheckSquare, AlignLeft, AlignCenter, AlignRight, Highlighter, Sparkles, PanelRightOpen, X, Loader, ImageIcon, Search, FileType} from 'lucide-react';
import {apiClient} from '@/lib/api';

interface RichEditorProps {value:string;onChange:(v:string)=>void;placeholder?:string;}

const MenuBtn: React.FC<{onClick:()=>void;active?:boolean;title:string;children:React.ReactNode}> = ({onClick,active,title,children}) => (
  <button type="button" onClick={onClick} title={title}
    className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors ${active?'bg-gray-200 dark:bg-gray-700 text-blue-600':'text-gray-600 dark:text-gray-300'}`}>{children}</button>
);
const Divider = () => <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1"/>;

/* ── AI Panel ── */
const AI_TOOLS = [
  {id:'polish',label:'润色'},{id:'grammar',label:'语法'},{id:'titles',label:'标题'},{id:'keywords',label:'关键词'},{id:'continue',label:'续写'},{id:'summary',label:'摘要'},{id:'style',label:'改风格'},
];
const AI_ENDPOINTS: Record<string,string> = {
  polish:'/ext/ai-recommendations/writing/polish',grammar:'/ext/ai-recommendations/writing/check-grammar',
  titles:'/ext/ai-recommendations/writing/generate-titles',keywords:'/ext/ai-recommendations/recommend-tags',
  continue:'/ext/ai-recommendations/writing/continue',summary:'/ext/ai-recommendations/extract-summary',
  style:'/ext/ai-recommendations/writing/transform-style',
};

/* ── Media Browser ── */
function MediaBrowser({onSelect, onClose}:{onSelect:(url:string)=>void;onClose:()=>void}) {
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  React.useEffect(()=>{
    apiClient.get('/media/files/list',{page:1,per_page:30}).then(r=>{
      const d=r.success&&r.data?r.data:{};
      setFiles(Array.isArray(d.files)?d.files:d.media_items||[]);
    }).finally(()=>setLoading(false));
  },[]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl" onClick={e=>e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0"><h3 className="font-bold text-gray-900 dark:text-white">媒体库</h3><button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-5 h-5"/></button></div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div> :
          !files.length ? <div className="p-12 text-center text-gray-400"><ImageIcon className="w-10 h-10 mx-auto mb-3 opacity-40"/><p className="text-sm">暂无媒体文件</p><p className="text-xs text-gray-500 mt-1">请先在媒体库上传</p></div> :
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {files.map((f:any,i:number)=>{
              const isImg = f.mime_type?.startsWith('image/');
              return (
                <button key={f.id||i} onClick={()=>onSelect(f.url)} className="group aspect-square rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:shadow-md transition-all relative">
                  {isImg ? <img src={f.url} alt={f.original_filename} className="w-full h-full object-cover group-hover:scale-105 transition-transform"/> :
                  <div className="w-full h-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center"><VideoIcon className="w-8 h-8 text-gray-300"/></div>}
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <p className="text-white text-xs truncate">{f.original_filename}</p></div>
                </button>
              );
            })}
          </div>}
        </div>
      </div>
    </div>
  );
}

const VideoIcon = ({className}:{className?:string})=><svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>;

/* ── RichEditor ── */
const RichEditor: React.FC<RichEditorProps> = ({value, onChange, placeholder = '开始写作...'}) => {
  const [showAI, setShowAI] = useState(false);
  const [showMedia, setShowMedia] = useState(false);
  const [aiMode, setAiMode] = useState('');
  const [aiResult, setAiResult] = useState('');
  const [aiBusy, setAiBusy] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({heading:{levels:[1,2,3]}}), Placeholder.configure({placeholder}),
      Underline,Typography,TextAlign.configure({types:['heading','paragraph']}),Highlight,ImageExt,
      LinkExt.configure({openOnClick:false}),Table.configure({resizable:true}),TableRow,TableCell,TableHeader,
      TaskList,TaskItem.configure({nested:true}),
    ],
    content: value || '',
    onUpdate: ({editor}) => onChange(editor.getHTML()),
    editorProps: {attributes:{class:'prose prose-lg dark:prose-invert max-w-none focus:outline-none min-h-[400px] px-6 py-4'}},
  });

  const addImage = (url?:string) => {const u=url||prompt('图片 URL:'); if(u&&editor) editor.chain().focus().setImage({src:u}).run();};
  const addLink = () => {const url=prompt('链接 URL:'); if(url&&editor) editor.chain().focus().setLink({href:url}).run();};
  const addTable = () => editor?.chain().focus().insertTable({rows:3,cols:3,withHeaderRow:true}).run();

  const runAI = useCallback(async (mode:string)=>{
    if (!editor) return;
    setAiMode(mode); setAiBusy(true); setAiResult('');
    const selected = editor.state.selection.empty ? editor.getText() : editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to);
    const text = selected || editor.getText();
    if (!text.trim()) { setAiResult('请先输入内容'); setAiBusy(false); return; }
    try {
      const ep = AI_ENDPOINTS[mode];
      const body = mode==='titles'?{content:text}:{text};
      const r = await apiClient.post(ep, body);
      if (r.success && r.data) {
        const d = r.data as any;
        setAiResult(d.result||d.text||d.keywords?.join(', ')||d.titles?.join('\n')||JSON.stringify(d));
      } else setAiResult(r.error||'请求失败');
    } catch { setAiResult('网络错误'); }
    finally { setAiBusy(false); setShowAI(true); }
  },[editor]);

  const applyAIResult = () => {
    if (!editor || !aiResult) return;
    const {from,to} = editor.state.selection;
    if (from !== to) editor.chain().focus().deleteRange({from,to}).insertContent(aiResult).run();
    else editor.chain().focus().insertContentAt(editor.state.selection.head, '\n' + aiResult).run();
    setShowAI(false); setAiResult('');
  };

  if (!editor) return <div className="h-[400px] bg-gray-50 dark:bg-gray-800 rounded-xl animate-pulse" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden relative">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
        <MenuBtn onClick={()=>editor.chain().focus().undo().run()} title="撤销"><Undo className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().redo().run()} title="重做"><Redo className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={()=>editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="粗体"><Bold className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="斜体"><Italic className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleUnderline().run()} active={editor.isActive('underline')} title="下划线"><span className="text-sm font-bold">U</span></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="删除线"><Strikethrough className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="代码"><Code className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleHighlight().run()} active={editor.isActive('highlight')} title="高亮"><Highlighter className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={()=>editor.chain().focus().toggleHeading({level:1}).run()} active={editor.isActive('heading',{level:1})} title="标题1"><Heading1 className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleHeading({level:2}).run()} active={editor.isActive('heading',{level:2})} title="标题2"><Heading2 className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleHeading({level:3}).run()} active={editor.isActive('heading',{level:3})} title="标题3"><Heading3 className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={()=>editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="列表"><List className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="有序"><ListOrdered className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleTaskList().run()} active={editor.isActive('taskList')} title="任务"><CheckSquare className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="引用"><Quote className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={()=>editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({textAlign:'left'})} title="左对齐"><AlignLeft className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({textAlign:'center'})} title="居中"><AlignCenter className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={()=>editor.chain().focus().setTextAlign('right').run()} active={editor.isActive({textAlign:'right'})} title="右对齐"><AlignRight className="w-4 h-4"/></MenuBtn>
        <Divider />
        <MenuBtn onClick={()=>setShowMedia(true)} title="媒体库"><Image className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={addLink} active={editor.isActive('link')} title="链接"><Link className="w-4 h-4"/></MenuBtn>
        <MenuBtn onClick={addTable} title="表格"><Table2 className="w-4 h-4"/></MenuBtn>
        <Divider />
        {/* AI Button */}
        <div className="relative">
          <button onClick={()=>setShowAI(!showAI)} className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors ${showAI?'bg-purple-100 dark:bg-purple-900/30 text-purple-600':'text-gray-600 dark:text-gray-300'}`} title="AI 助手"><Sparkles className="w-4 h-4"/></button>
          {/* AI Dropdown */}
          {showAI && <div className="absolute top-full right-0 mt-1 w-44 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5 z-20">
            {AI_TOOLS.map(t=>(
              <button key={t.id} onClick={()=>{runAI(t.id);}} disabled={aiBusy} className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-purple-500"/>{t.label}
              </button>
            ))}
          </div>}
        </div>
      </div>

      <EditorContent editor={editor} />

      {/* AI Result Panel */}
      {showAI && aiResult && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-purple-50 dark:bg-purple-900/10">
          <div className="flex items-center justify-between mb-2"><span className="text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase">{aiMode} 结果</span>
            <div className="flex gap-2"><button onClick={applyAIResult} className="px-3 py-1 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700">插入</button>
            <button onClick={()=>{setShowAI(false);setAiResult('');}} className="p-1 text-gray-400 hover:text-gray-600"><X className="w-4 h-4"/></button></div>
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{aiResult}</p>
        </div>
      )}

      {/* AI Loading */}
      {aiBusy && <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-purple-50 dark:bg-purple-900/10 flex items-center gap-2 text-sm text-purple-600"><Loader className="w-4 h-4 animate-spin"/>AI 处理中...</div>}

      {/* Media Browser Modal */}
      {showMedia && <MediaBrowser onSelect={(url)=>{addImage(url);setShowMedia(false);}} onClose={()=>setShowMedia(false)}/>}
    </div>
  );
};

export default RichEditor;
