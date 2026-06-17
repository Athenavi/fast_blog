'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {MediaService} from '@/lib/api/media-service';
import {AI_RECOMMENDATIONS, MEDIA} from '@/lib/api/api-paths';
import {Image as ImageIcon2, ImageIcon, LayoutGrid, Loader, Palette, Sparkles, Upload, X, Eye, EyeOff} from 'lucide-react';
import {apiClient} from '@/lib/api/base-client';
import {markdownToHtml} from '@/lib/markdown-converter';

interface MarkdownEditorProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  editorRef?: React.MutableRefObject<any>;
}

const AI_TOOLS = [
  {id:'polish',label:'润色'},{id:'grammar',label:'语法'},{id:'titles',label:'标题'},{id:'keywords',label:'关键词'},{id:'continue',label:'续写'},{id:'summary',label:'摘要'},{id:'style',label:'改风格'},
];

/* ── Shared Modals (same as before, pasted from RichEditor) ── */
function PatternLibrary({onSelect, onClose}: { onSelect: (blocks: any) => void; onClose: () => void }) {
  const [patterns, setPatterns] = useState<any[]>([]);
  React.useEffect(() => {
    apiClient.get('/cms/block-patterns/list').then(r => {
      if (r.success) { const d: any = r.data; setPatterns(Array.isArray(d) ? d : (d?.patterns || [])); }
    }).catch(console.error);
  }, []);
  return <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700" onClick={e => e.stopPropagation()}>
      <div className="flex items-center justify-between px-6 py-4 border-b shrink-0"><h3 className="font-bold text-gray-900 dark:text-white">块模式库</h3>
        <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-5 h-5"/></button>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {patterns.map(p => {
            let parsedBlocks: any[];
            try { parsedBlocks = JSON.parse(p.blocks); } catch { parsedBlocks = []; }
            return (<button key={p.id} onClick={() => onSelect(parsedBlocks)} className="group p-4 rounded-xl border hover:border-blue-500 hover:shadow-md transition-all text-left">
              <div className="aspect-video bg-gray-100 dark:bg-gray-800 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                {p.thumbnail ? <img src={p.thumbnail} className="w-full h-full object-cover"/> : <LayoutGrid className="w-8 h-8 text-gray-300"/>}
              </div>
              <h4 className="font-semibold text-sm truncate">{p.title}</h4>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>
            </button>);
          })}
        </div>
      </div>
    </div>
  </div>;
}

function StyleManager({onClose}: { onClose: () => void }) {
  const [styles, setStyles] = useState<any[]>([]);
  React.useEffect(() => { apiClient.get('/cms/global-styles/list').then(r => { if (r.success) setStyles(r.data || []) }).catch(console.error); }, []);
  const activate = (id: number) => { apiClient.post(`/cms/global-styles/${id}/activate`).then(r => { if (r.success) onClose() }); };
  return <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-md flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700" onClick={e => e.stopPropagation()}>
      <div className="flex items-center justify-between px-6 py-4 border-b shrink-0"><h3 className="font-bold text-gray-900 dark:text-white">全局样式方案</h3>
        <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-5 h-5"/></button></div>
      <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
        {styles.map(s => <div key={s.id} className={`p-4 rounded-xl border ${s.is_active ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'} flex items-center justify-between`}>
          <div><h4 className="font-semibold">{s.theme_name}</h4><p className="text-xs text-gray-500 mt-1">创建于 {new Date(s.created_at).toLocaleDateString()}</p></div>
          {!s.is_active && <button onClick={() => activate(s.id)} className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200">应用</button>}
          {s.is_active && <span className="text-xs font-medium text-blue-600">当前激活</span>}
        </div>)}
      </div>
    </div>
  </div>;
}

const AI_ENDPOINTS: Record<string, string> = {
  polish: AI_RECOMMENDATIONS.WRITING_POLISH, grammar: AI_RECOMMENDATIONS.WRITING_GRAMMAR,
  titles: AI_RECOMMENDATIONS.WRITING_GENERATE_TITLES, keywords: AI_RECOMMENDATIONS.RECOMMEND_TAGS,
  continue: AI_RECOMMENDATIONS.WRITING_CONTINUE, summary: AI_RECOMMENDATIONS.WRITING_EXTRACT_SUMMARY,
  style: AI_RECOMMENDATIONS.WRITING_TRANSFORM_STYLE,
};

function MediaBrowser({onSelect, onClose}: { onSelect: (url: string) => void; onClose: () => void }) {
  const [files, setFiles] = useState<any[]>([]); const [loading, setLoading] = useState(true);
  React.useEffect(() => { apiClient.get(MEDIA.FILES_LIST, { page: 1, per_page: 30 }).then(r => { setFiles(r.success && r.data ? ((r.data as any).files || (r.data as any).media_items || []) : []) }).finally(() => setLoading(false)); }, []);
  return <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl border border-gray-200 dark:border-gray-700" onClick={e => e.stopPropagation()}>
      <div className="flex items-center justify-between px-6 py-4 border-b shrink-0"><h3 className="font-bold text-gray-900 dark:text-white">媒体库</h3><button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-5 h-5"/></button></div>
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? <div className="p-12 text-center"><div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" /></div>
          : !files.length ? <div className="p-12 text-center text-gray-400"><ImageIcon className="w-10 h-10 mx-auto mb-3 opacity-40" /><p className="text-sm">暂无媒体文件</p></div>
            : <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">{files.map((f: any, i: number) => (
              <button key={f.id || i} onClick={() => onSelect(f.url)} className="group aspect-square rounded-xl overflow-hidden border hover:border-blue-500 hover:shadow-md transition-all relative">
                {f.mime_type?.startsWith('image/') ? <img src={f.url} alt={f.original_filename} className="w-full h-full object-cover group-hover:scale-105" /> : <div className="w-full h-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-300 text-4xl">🎬</div>}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-1.5 opacity-0 group-hover:opacity-100"><p className="text-white text-xs truncate">{f.original_filename}</p></div>
              </button>
            ))}</div>}
      </div>
    </div>
  </div>;
}

/* ── Insert Markdown at cursor position ── */
function insertAtCursor(ta: HTMLTextAreaElement, before: string, after: string, selectMid?: boolean): void {
  const start = ta.selectionStart, end = ta.selectionEnd;
  const selected = ta.value.substring(start, end);
  const replacement = before + selected + after;
  ta.value = ta.value.substring(0, start) + replacement + ta.value.substring(end);
  if (selectMid) ta.selectionStart = start + before.length;
  else if (selected) ta.selectionStart = start + before.length;
  else ta.selectionStart = start + replacement.length;
  ta.selectionEnd = selectMid ? start + before.length + selected.length : ta.selectionStart;
  ta.focus();
}

/* ── Main Markdown Editor ── */
const MarkdownEditor: React.FC<MarkdownEditorProps> = ({value, onChange, placeholder = '开始写作...', editorRef}) => {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const [showAI, setShowAI] = useState(false);
  const [showMedia, setShowMedia] = useState(false);
  const [showPatterns, setShowPatterns] = useState(false);
  const [showStyles, setShowStyles] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [aiResult, setAiResult] = useState('');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounter = useRef(0);
  const previewRef = useRef<HTMLDivElement>(null);

  // Expose textarea ref as editorRef
  useEffect(() => {
    if (editorRef) editorRef.current = {ta: taRef.current, getHTML: () => markdownToHtml(value), getText: () => value};
  }, [editorRef, value]);

  // Preview: scroll sync
  useEffect(() => {
    if (!showPreview || !previewRef.current) return;
    previewRef.current.innerHTML = markdownToHtml(value);
  }, [value, showPreview]);

  // Paste-upload
  const uploadPastedFiles = useCallback(async (files: File[]) => {
    for (const file of files) {
      setUploadStatus(`正在上传 ${file.name}...`);
      try {
        const resp = await MediaService.uploadMediaFileWithProgress(file, (pct) => {
          setUploadStatus(`正在上传 ${file.name} (${pct}%)`);
        });
        if (!resp.success || !resp.data?.files?.[0]?.url) continue;
        const url = resp.data.files[0].url;
        const md = file.type.startsWith('image/') ? `![${file.name}](${url})` : `[${file.name}](${url})`;
        const ta = taRef.current; if (!ta) continue;
        const pos = ta.selectionStart;
        ta.value = ta.value.substring(0, pos) + (pos === ta.value.length ? '\n' : '') + md + ta.value.substring(pos);
        ta.selectionStart = ta.selectionEnd = pos + md.length;
        ta.focus();
        onChange(ta.value);
      } catch (err) { console.error('Upload failed:', err); }
    }
    setUploadStatus(null);
  }, [onChange]);

  // AI
  const runAI = useCallback(async (mode: string) => {
    const ta = taRef.current; if (!ta) return;
    setShowAI(true); setAiBusy(true); setAiResult('');
    const sel = ta.value.substring(ta.selectionStart, ta.selectionEnd);
    const text = sel || ta.value;
    if (!text.trim()) { setAiResult('请先输入内容'); setAiBusy(false); return; }
    try {
      const r = await apiClient.post(AI_ENDPOINTS[mode], mode === 'titles' ? { content: text } : { text });
      if (r.success && r.data) { const d = r.data as any; setAiResult(d.result || d.text || d.keywords?.join(', ') || d.titles?.join('\n') || JSON.stringify(d)); }
      else setAiResult(r.error || '请求失败');
    } catch { setAiResult('网络错误'); } finally { setAiBusy(false); }
  }, []);

  const applyAI = () => {
    if (!aiResult) return;
    const ta = taRef.current; if (!ta) return;
    const start = ta.selectionStart, end = ta.selectionEnd;
    const selected = ta.value.substring(start, end);
    const replacement = selected ? aiResult : '\n' + aiResult;
    ta.value = ta.value.substring(0, start) + replacement + ta.value.substring(end);
    ta.selectionStart = ta.selectionEnd = start + replacement.length;
    ta.focus();
    onChange(ta.value);
    setShowAI(false); setAiResult('');
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const dt = e.clipboardData;
    let files: File[] = [];
    if (dt?.files?.length) files = Array.from(dt.files);
    else if (dt?.items?.length) { for (let i = 0; i < dt.items.length; i++) { const item = dt.items[i]; if (item.kind === 'file') { const f = item.getAsFile(); if (f) files.push(f); } } }
    if (!files.length) return;
    e.preventDefault();
    uploadPastedFiles(files);
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden relative min-h-[60vh] flex flex-col"
      onDragEnter={e => { e.preventDefault(); dragCounter.current++; if (e.dataTransfer.types?.includes('Files')) setIsDragOver(true); }}
      onDragOver={e => e.preventDefault()}
      onDragLeave={e => { e.preventDefault(); dragCounter.current--; if (dragCounter.current <= 0) { dragCounter.current = 0; setIsDragOver(false); } }}
      onDrop={e => { e.preventDefault(); setIsDragOver(false); dragCounter.current = 0; const files = Array.from(e.dataTransfer?.files || []); if (files.length) uploadPastedFiles(files); }}>

      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-blue-500/10 dark:bg-blue-500/20 backdrop-blur-sm border-2 border-dashed border-blue-400 dark:border-blue-500 rounded-2xl pointer-events-none">
          <div className="flex flex-col items-center gap-2 text-blue-600 dark:text-blue-400">
            <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center"><Upload className="w-6 h-6" /></div>
            <span className="text-sm font-semibold">松手以上传文件</span>
            <span className="text-xs opacity-70">支持图片、视频、文档等</span>
          </div>
        </div>
      )}

      {/* Split: Editor + Preview */}
      <div className="flex flex-1 min-h-0">
        {/* Editor pane */}
        <textarea ref={taRef} value={value} onChange={e => onChange(e.target.value)} onPaste={handlePaste}
          placeholder={placeholder}
          className={`flex-1 min-h-[60vh] font-mono text-sm leading-relaxed px-6 py-4 bg-transparent dark:text-gray-200 placeholder-gray-300 dark:placeholder-gray-600 resize-none focus:outline-none ${showPreview ? 'border-r border-gray-200 dark:border-gray-700 w-1/2' : 'w-full'}`}
          spellCheck={false}
        />

        {/* Preview pane */}
        {showPreview && (
          <div ref={previewRef}
            className="w-1/2 min-h-[60vh] px-6 py-4 overflow-y-auto prose prose-sm dark:prose-invert max-w-none bg-gray-50/50 dark:bg-gray-800/20" />
        )}
      </div>

      {/* Preview toggle button */}
      <button onClick={() => setShowPreview(!showPreview)} title={showPreview ? '关闭预览' : '预览'}
        className={`absolute top-3 right-3 z-30 p-1.5 rounded-lg transition-all ${showPreview ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
        {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>

      {/* Mobile floating toolbar */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 lg:hidden flex items-center gap-2 px-4 py-2.5 bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700">
        <button onClick={() => setShowPatterns(true)} title="块模式" className="w-9 h-9 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl hover:scale-110 transition-all flex items-center justify-center"><LayoutGrid className="w-4 h-4" /></button>
        <button onClick={() => setShowStyles(true)} title="全局样式" className="w-9 h-9 bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400 rounded-xl hover:scale-110 transition-all flex items-center justify-center"><Palette className="w-4 h-4" /></button>
        <button onClick={() => setShowMedia(true)} title="媒体库" className="w-9 h-9 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl hover:scale-110 transition-all flex items-center justify-center"><ImageIcon2 className="w-4 h-4" /></button>
        <div className="w-px h-6 bg-gray-200 dark:bg-gray-700" />
        <button onClick={() => setShowAI(!showAI)} title="AI 助手" className="w-9 h-9 bg-gradient-to-br from-purple-100 to-blue-100 dark:from-purple-900/30 dark:to-blue-900/30 text-purple-600 dark:text-purple-400 rounded-xl hover:scale-110 transition-all flex items-center justify-center"><Sparkles className="w-4 h-4" /></button>
      </div>

      {/* Desktop floating buttons */}
      <div className="hidden lg:block">
        <button onClick={() => setShowPatterns(true)} className="fixed bottom-36 right-6 z-40 w-11 h-11 bg-indigo-600 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center" title="块模式"><LayoutGrid className="w-5 h-5" /></button>
        <button onClick={() => setShowStyles(true)} className="fixed bottom-28 right-6 z-40 w-11 h-11 bg-pink-600 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center" title="全局样式"><Palette className="w-5 h-5" /></button>
        <button onClick={() => setShowMedia(true)} className="fixed bottom-20 right-6 z-40 w-11 h-11 bg-blue-600 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center" title="媒体库"><ImageIcon2 className="w-5 h-5" /></button>
        <button onClick={() => setShowAI(!showAI)} className="fixed bottom-6 right-6 z-40 w-12 h-12 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-full shadow-xl hover:shadow-2xl hover:scale-105 transition-all flex items-center justify-center" title="AI 助手"><Sparkles className="w-5 h-5" /></button>
      </div>

      {/* AI Menu */}
      {showAI && !aiResult && !aiBusy && (
        <div className="fixed bottom-20 right-6 z-40 w-48 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-1.5">
          {AI_TOOLS.map(t => <button key={t.id} onClick={() => runAI(t.id)} disabled={aiBusy} className="w-full text-left px-4 py-2.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"><Sparkles className="w-3.5 h-3.5 text-purple-500" />{t.label}</button>)}
        </div>
      )}

      {/* AI Result */}
      {showAI && aiResult && <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-purple-50 dark:bg-purple-900/10">
        <div className="flex items-center justify-between mb-2"><span className="text-xs font-semibold text-purple-700 uppercase">结果</span>
          <div className="flex gap-2"><button onClick={applyAI} className="px-3 py-1 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700">插入</button>
            <button onClick={() => { setShowAI(false); setAiResult(''); }} className="p-1 text-gray-400"><X className="w-4 h-4" /></button></div>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{aiResult}</p>
      </div>}
      {aiBusy && <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-purple-50 dark:bg-purple-900/10 flex items-center gap-2 text-sm text-purple-600"><Loader className="w-4 h-4 animate-spin" />AI 处理中...</div>}

      {/* Upload Toast */}
      {uploadStatus && <div className="fixed top-4 right-4 z-[100] flex items-center gap-2.5 px-4 py-3 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 text-sm text-blue-600 dark:text-blue-400"><Loader className="w-4 h-4 animate-spin shrink-0" /><span className="truncate max-w-[240px]">{uploadStatus}</span><button onClick={() => setUploadStatus(null)} className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ml-1 shrink-0"><X className="w-3.5 h-3.5" /></button></div>}

      {/* Modals */}
      {showMedia && <MediaBrowser onSelect={(url) => { const ta = taRef.current; if (ta) { const md = `![image](${url})`; ta.value += '\n' + md; onChange(ta.value); } setShowMedia(false); }} onClose={() => setShowMedia(false)} />}
      {showPatterns && <PatternLibrary onSelect={(blocks) => { const ta = taRef.current; if (ta) { ta.value += '\n' + JSON.stringify(blocks) + '\n'; onChange(ta.value); } setShowPatterns(false); }} onClose={() => setShowPatterns(false)} />}
      {showStyles && <StyleManager onClose={() => setShowStyles(false)} />}
    </div>
  );
};

export default MarkdownEditor;
