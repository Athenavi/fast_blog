'use client';

import React, {useState, useRef, useEffect, useCallback} from 'react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {getConfig} from '@/lib/config';

// ─── Icons (inline SVG for zero dependencies) ─────────────────────

const Icons = {
  send: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4Z"/></svg>,
  sparkle: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2 15.09 8.26 22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2Z"/></svg>,
  plus: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>,
  trash: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>,
  settings: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>,
  sun: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>,
  moon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>,
  chat: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/></svg>,
  stop: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>,
  history: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>,
};

// ─── Types ──────────────────────────────────────

interface ChatMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: {id: string; type: string; function: {name: string; arguments: string}}[];
  tool_call_id?: string;
  name?: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

const DEFAULT_CONFIG: LLMConfig = {
  endpoint: '',
  apiKey: '',
  model: '',
  systemPrompt: `你是 FastBlog 的 AI 助手，可以通过 MCP 工具管理博客内容。

可用操作：
1. 创建文章 — 提供标题和内容
2. 更新文章 — 指定文章 ID
3. 删除文章 — 指定文章 ID
4. 搜索文章 — 提供关键词
5. 查看/创建分类
6. 查看系统统计

请使用中文回复。`,
};

const CFG_KEY = 'fastblog-aichat-config';
const CONS_KEY = 'fastblog-aichat-conversations';

function genId(): string { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
function trunc(s: string, n: number): string { return s.length > n ? s.slice(0, n) + '…' : s; }

function ago(ts: number): string {
  const d = new Date(ts);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return '刚刚';
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3600_000)} 小时前`;
  return d.toLocaleDateString('zh-CN', {month: 'short', day: 'numeric'});
}

// ─── Preset templates ───────────────────────────

const PRESETS = [
  {endpoint: 'https://api.deepseek.com/v1', apiKey: '', model: 'deepseek-chat', label: 'DeepSeek'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o-mini', label: 'OpenAI'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o', label: 'GPT-4o'},
];

const SUGGESTIONS = [
  {icon: '✍️', title: '写文章', text: '帮我写一篇关于 AI 趋势的文章'},
  {icon: '🔍', title: '找文章', text: '搜索标题包含 Python 的文章'},
  {icon: '📊', title: '看统计', text: '博客现有多少篇文章？'},
  {icon: '📂', title: '看分类', text: '列出所有文章分类'},
];

// ─── Message Bubble ─────────────────────────────

function Bubble({msg}: {msg: ChatMessage}) {
  const isUser = msg.role === 'user';
  const isTool = msg.role === 'tool';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold ${
        isUser ? 'bg-blue-500 text-white' : isTool ? 'bg-amber-100 text-amber-700' : 'bg-violet-500 text-white'
      }`}>
        {isUser ? 'U' : isTool ? '🔧' : 'AI'}
      </div>
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`text-sm leading-relaxed whitespace-pre-wrap px-4 py-2.5 rounded-2xl ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-md'
            : isTool
              ? 'bg-amber-50 dark:bg-amber-900/10 text-gray-600 dark:text-gray-400 border border-amber-200 dark:border-amber-800/30 rounded-tl-md font-mono text-[12px]'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-md'
        }`}>
          {isUser || !msg.content ? msg.content : (
            <div className="prose prose-sm dark:prose-invert max-w-none">{msg.content}</div>
          )}
        </div>
        {!isUser && !isTool && msg.tool_calls && msg.tool_calls.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {msg.tool_calls.map((tc, i) => (
              <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300 rounded-md text-[11px] font-medium">
                🔧 {tc.function.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Thinking dots ──────────────────────────────

function Thinking() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-violet-500 flex items-center justify-center text-white text-[11px] font-semibold">AI</div>
      <div className="px-5 py-3 bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-md">
        <div className="flex gap-1.5">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '0ms'}}/>
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '150ms'}}/>
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '300ms'}}/>
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar ────────────────────────────────────

function Sidebar({conversations, activeId, onSelect, onNew, onDelete, collapsed, onToggle, onSettings}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  onSettings: () => void;
}) {
  return (
    <aside className={`${collapsed ? 'w-0' : 'w-60'} transition-all duration-300 flex-shrink-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 overflow-hidden flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between h-12 px-3 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base" role="img" aria-label="sparkle">✨</span>
          <span className="font-semibold text-sm text-gray-800 dark:text-gray-200">AI Chat</span>
        </div>
        <button onClick={onNew} className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
          {Icons.plus}
        </button>
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {conversations.length === 0 && (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500 text-xs">暂无对话</div>
        )}
        {conversations.map(conv => (
          <div key={conv.id} onClick={() => onSelect(conv.id)} role="button" tabIndex={0}
               onKeyDown={e => e.key === 'Enter' && onSelect(conv.id)}
               className={`flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm cursor-pointer transition-colors group ${
                 conv.id === activeId
                   ? 'bg-white dark:bg-gray-800 shadow-sm'
                   : 'hover:bg-gray-100 dark:hover:bg-gray-800/50'
               }`}>
            <span className="text-gray-400 flex-shrink-0">{Icons.chat}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{conv.title}</div>
              <div className="text-[10px] text-gray-400">{ago(conv.createdAt)}</div>
            </div>
            <button onClick={(e) => onDelete(e, conv.id)}
                    className="p-1 rounded text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0">
              {Icons.trash}
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-gray-200 dark:border-gray-800 flex-shrink-0 space-y-1">
        <button onClick={onNew}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors">
          {Icons.plus}<span>新对话</span>
        </button>
        <button onClick={onSettings}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          {Icons.settings}<span>设置</span>
        </button>
      </div>
    </aside>
  );
}

// ─── Settings Modal ─────────────────────────────

function SettingsModal({config, onChange, onClose, show}: {config: LLMConfig; onChange: (p: Partial<LLMConfig>) => void; onClose: () => void; show: boolean}) {
  const [showKey, setShowKey] = useState(false);
  if (!show) return null;

  const applyPreset = (preset: typeof PRESETS[0]) => {
    onChange({endpoint: preset.endpoint, model: preset.model, apiKey: preset.apiKey});
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">设置</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Presets */}
          <div>
            <label className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 block">快速选择</label>
            <div className="flex gap-2">
              {PRESETS.map((p, i) => (
                <button key={i} onClick={() => applyPreset(p)}
                        className="flex-1 px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Endpoint */}
          <div>
            <label className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5 block">API 端点</label>
            <input value={config.endpoint} onChange={e => onChange({endpoint: e.target.value})} placeholder="https://api.openai.com/v1"
                   className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400"/>
          </div>

          {/* API Key */}
          <div>
            <label className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5 block">API Key</label>
            <div className="relative">
              <input type={showKey ? 'text' : 'password'} value={config.apiKey} onChange={e => onChange({apiKey: e.target.value})} placeholder="sk-..."
                     className="w-full px-3 py-2 pr-16 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400 font-mono"/>
              <button onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600">{showKey ? '隐藏' : '显示'}</button>
            </div>
          </div>

          {/* Model */}
          <div>
            <label className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5 block">模型</label>
            <input value={config.model} onChange={e => onChange({model: e.target.value})} placeholder="gpt-4o-mini"
                   className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400"/>
          </div>

          {/* System Prompt */}
          <div>
            <label className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5 block">系统提示</label>
            <textarea value={config.systemPrompt} onChange={e => onChange({systemPrompt: e.target.value})} rows={4}
                      className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white resize-none"/>
          </div>
        </div>

        <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
          <span className="text-[10px] text-gray-400">配置仅保存在浏览器本地</span>
          <button onClick={onClose} className="px-4 py-1.5 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors">完成</button>
        </div>
      </div>
    </div>
  );
}


// ─── Main Component ────────────────────────────

export default function AIChatGuard() {
  return <AuthGuard><QueryProvider><AIChatInner/></QueryProvider></AuthGuard>;
}

function AIChatInner() {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [mounted, setMounted] = useState(false);

  const msgEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const activeConv = conversations.find(c => c.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  // ── Hydrate ──
  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem(CFG_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.endpoint || parsed.apiKey || parsed.model) setConfig(prev => ({...prev, ...parsed}));
      }
    } catch {}
    try {
      const saved = localStorage.getItem(CONS_KEY);
      if (saved) {
        const list: Conversation[] = JSON.parse(saved);
        setConversations(list);
        if (list.length > 0) setActiveConvId(list[0].id);
      }
    } catch {}
    setDarkMode(document.documentElement.classList.contains('dark'));
  }, []);

  useEffect(() => { if (!mounted) return; localStorage.setItem(CFG_KEY, JSON.stringify(config)); }, [config, mounted]);
  useEffect(() => { if (!mounted) return; localStorage.setItem(CONS_KEY, JSON.stringify(conversations)); }, [conversations, mounted]);
  useEffect(() => { msgEndRef.current?.scrollIntoView({behavior: 'smooth'}); }, [messages, loading]);

  const toggleDark = useCallback(() => {
    setDarkMode(p => { const n = !p; document.documentElement.classList.toggle('dark', n); return n; });
  }, []);

  const newConversation = useCallback(() => {
    const id = genId();
    setConversations(prev => [{id, title: '新对话', messages: [], createdAt: Date.now()}, ...prev]);
    setActiveConvId(id);
  }, []);

  const deleteConversation = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id);
      if (activeConvId === id) setActiveConvId(next.length > 0 ? next[0].id : null);
      return next;
    });
  }, [activeConvId]);

  const updateConfig = useCallback((patch: Partial<LLMConfig>) => {
    setConfig(prev => ({...prev, ...patch}));
  }, []);

  // ── Send message ──
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');

    // Validate config
    if (!config.endpoint || !config.model) {
      setSettingsOpen(true);
      return;
    }

    const finalConvId = activeConvId || genId();
    const isNew = !activeConvId;
    if (isNew) {
      setConversations(prev => [{id: finalConvId, title: trunc(text, 40), messages: [], createdAt: Date.now()}, ...prev]);
      setActiveConvId(finalConvId);
    }

    const curMsgs = conversations.find(c => c.id === finalConvId)?.messages || [];
    const newMessages: ChatMessage[] = [...curMsgs, {role: 'user', content: text}];
    setConversations(prev => prev.map(c => c.id !== finalConvId ? c : {...c, messages: newMessages, title: c.messages.length === 0 ? trunc(text, 40) : c.title}));
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;
    const acc: ChatMessage[] = [...newMessages];

    const body = JSON.stringify({
      endpoint: config.endpoint,
      api_key: config.apiKey,
      model: config.model,
      messages: newMessages.map(m => ({role: m.role, content: m.content})),
      conversation_id: finalConvId,
      system_prompt: config.systemPrompt,
    });

    try {
      const base = getConfig().API_BASE_URL;
      const resp = await fetch(`${base}/api/v2/mcp/chat/stream`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body, signal: controller.signal,
        credentials: 'include',
      });
      if (!resp.ok) {
        acc.push({role: 'assistant', content: `⚠️ 请求失败 (${resp.status})`});
        setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
        return;
      }

      const reader = resp.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += decoder.decode(value, {stream: true});
        const lines = buf.split('\n');
        buf = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'done') break;
            if (data.type === 'error') {
              acc.push({role: 'assistant', content: `❌ ${data.message}`});
              setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
              return;
            }
            if (data.type === 'token' && data.content) {
              const last = acc[acc.length - 1];
              if (last?.role === 'assistant') {
                last.content = (last.content || '') + data.content;
              } else {
                acc.push({role: 'assistant', content: data.content});
              }
              setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
            }
            if (data.type === 'tool_call') {
              // Show tool call
            }
          } catch {}
        }
      }
      setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        acc.push({role: 'assistant', content: `❌ ${err?.message || '请求失败'}`});
        setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [input, loading, config, activeConvId, conversations]);

  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }, [sendMessage]);

  const handleInterrupt = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }, []);

  const needsConfig = !config.endpoint || !config.model;

  return (
    <div className="h-dvh flex bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 overflow-hidden">
      {/* ─── Sidebar ── */}
      <Sidebar conversations={conversations} activeId={activeConvId} onSelect={setActiveConvId}
               onNew={newConversation} onDelete={deleteConversation}
               collapsed={!sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)}
               onSettings={() => setSettingsOpen(true)}/>

      {/* ─── Main ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-12 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="flex items-center gap-2">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
            </button>
            {activeConv && <span className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate max-w-[200px]">{activeConv.title}</span>}
          </div>
          <div className="flex items-center gap-1">
            {activeConv && messages.length > 0 && (
              <button onClick={() => {
                setConversations(prev => prev.map(c => c.id === activeConvId ? {...c, messages: []} : c));
              }} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-red-500 transition-colors" title="清空">
                {Icons.trash}
              </button>
            )}
            <button onClick={toggleDark} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 transition-colors">
              {darkMode ? Icons.sun : Icons.moon}
            </button>
            <button onClick={() => setSettingsOpen(true)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 transition-colors">
              {Icons.settings}
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="text-5xl mb-4">✨</div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">开始 AI 对话</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
                  {needsConfig ? '请先点击右上角设置 API 端点和模型' : '通过自然语言管理博客内容'}
                </p>

                {needsConfig ? (
                  <button onClick={() => setSettingsOpen(true)} className="px-5 py-2.5 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors shadow-sm">
                    打开设置
                  </button>
                ) : (
                  <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                    {SUGGESTIONS.map((item, i) => (
                      <button key={i} onClick={() => setInput(item.text)}
                              className="flex items-center gap-2 p-3 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-violet-300 dark:hover:border-violet-700 text-left text-sm transition-colors group">
                        <span className="text-lg">{item.icon}</span>
                        <div>
                          <div className="font-medium text-gray-800 dark:text-gray-200 text-xs">{item.title}</div>
                          <div className="text-[10px] text-gray-400 line-clamp-2">{item.text}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              messages.map((msg, i) => <Bubble key={i} msg={msg}/>)
            )}
            {loading && <Thinking/>}
            <div ref={msgEndRef}/>
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="max-w-2xl mx-auto px-4 py-3">
            <div className="flex items-end gap-2 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-violet-500 transition-all">
              <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
                        placeholder="输入消息，Enter 发送" disabled={loading} rows={1}
                        className="flex-1 bg-transparent text-sm dark:text-white placeholder-gray-400 resize-none outline-none max-h-32 leading-relaxed"
                        onInput={e => { const el = e.currentTarget; el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 120)}px`; }}/>
              <div className="flex items-center gap-1">
                {loading ? (
                  <button onClick={handleInterrupt} className="p-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors">
                    {Icons.stop}
                  </button>
                ) : (
                  <button onClick={sendMessage} disabled={!input.trim() || needsConfig}
                          className="p-2 rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                    {Icons.send}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {settingsOpen && <SettingsModal config={config} onChange={updateConfig} onClose={() => setSettingsOpen(false)} show={settingsOpen}/>}
    </div>
  );
}
