'use client';

import React, {useState, useRef, useEffect, useCallback} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {getConfig} from '@/lib/config';
import {
  Send, Plus, Trash2, Settings, X, Bot, User, Wrench,
  Sparkles, MessageSquare, Loader2, Moon, Sun, PanelLeftOpen,
  PanelLeftClose, FileText, Search, BarChart3, Hash, CornerDownLeft,
  Copy, Check, Undo2, Pause, Play, History,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────

interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  name?: string;
}

interface ToolCall {
  id: string;
  type: string;
  function: {name: string; arguments: string};
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  interrupted?: boolean;
}

interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

interface CheckpointInfo {
  id: string;
  step: number;
  current_node: string;
  messages_count: number;
  interrupted: boolean;
  timestamp: number;
}

const DEFAULT_CONFIG: LLMConfig = {
  endpoint: 'https://api.openai.com/v1',
  apiKey: '',
  model: 'gpt-4o-mini',
  systemPrompt: `你是 FastBlog 的 AI 助手，可以帮助用户管理博客内容。

你可以通过调用工具来执行以下操作：
1. 创建文章 - 提供标题和内容
2. 更新文章 - 指定文章 ID
3. 删除文章 - 指定文章 ID
4. 搜索文章 - 提供关键词
5. 查看分类列表
6. 创建分类
7. 查看系统统计信息

请使用中文回复，保持专业且友好的语气。`,
};

const CFG_KEY = 'fastblog-aichat-config';
const CONS_KEY = 'fastblog-aichat-conversations';

function genId(): string { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
function truncate(s: string, n: number): string { return s.length > n ? s.slice(0, n) + '…' : s; }

function fmtDate(ts: number): string {
  const d = new Date(ts); const now = new Date(); const diff = now.getTime() - d.getTime();
  if (diff < 60_000) return '刚刚'; if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3600_000)} 小时前`;
  return d.toLocaleDateString('zh-CN', {month: 'short', day: 'numeric'});
}

// ─── ChatBubble ────────────────────────────────

function ChatBubble({msg, onCopy}: {msg: ChatMessage; onCopy: (t: string) => void}) {
  const [copied, setCopied] = useState(false);
  const isUser = msg.role === 'user';

  const copyText = useCallback(() => {
    const text = msg.content || '';
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
    onCopy(text);
  }, [msg.content, onCopy]);

  return (
    <div className={`flex gap-3 sm:gap-4 group ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ring-2 ring-white dark:ring-gray-800 ${
        isUser ? 'bg-blue-500' : 'bg-gradient-to-br from-violet-500 to-indigo-500'}`}>
        {isUser ? <span className="text-white text-xs font-bold">U</span> : <Bot className="w-4 h-4 text-white"/>}
      </div>
      <div className={`max-w-[80%] sm:max-w-[70%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`flex items-center gap-2 mb-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-[11px] font-medium text-gray-400 dark:text-gray-500">{isUser ? '你' : 'AI 助手'}</span>
        </div>
        {msg.content && (
          <div className={`relative rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-500 text-white rounded-tr-sm'
              : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700/50 rounded-tl-sm shadow-sm'
          }`}>
            <div className="whitespace-pre-wrap">{msg.content}</div>
            {!isUser && msg.content && (
              <button onClick={copyText}
                      className="absolute -bottom-2 right-2 p-1 rounded-md bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 shadow-sm opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                {copied ? <Check className="w-3 h-3 text-green-500"/> : <Copy className="w-3 h-3"/>}
              </button>
            )}
          </div>
        )}
        {msg.tool_calls && msg.tool_calls.length > 0 && (
          <div className="mt-1.5 space-y-1 w-full">
            {msg.tool_calls.map((tc, j) => {
              let args: any = {}; try { args = JSON.parse(tc.function.arguments); } catch {}
              return (
                <div key={j} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800/50 text-[11px]">
                  <Wrench className="w-3 h-3 text-violet-500"/>
                  <span className="font-medium text-violet-700 dark:text-violet-300">{tc.function.name}</span>
                  <span className="text-gray-400 dark:text-gray-500">{Object.entries(args).map(([k, v]) => `${k}=${typeof v === 'string' ? truncate(v, 20) : JSON.stringify(v)}`).join(', ')}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex gap-3 sm:gap-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-violet-500 to-indigo-500 ring-2 ring-white dark:ring-gray-800">
        <Bot className="w-4 h-4 text-white"/>
      </div>
      <div className="max-w-[80%] flex flex-col">
        <span className="text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-1 px-1">AI 助手</span>
        <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700/50 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '0ms'}}/>
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '150ms'}}/>
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '300ms'}}/>
          </div>
        </div>
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  {icon: FileText, title: '写一篇文章', text: '帮我写一篇关于技术趋势的文章，标题为「2026 年值得关注的十大技术」'},
  {icon: Search, title: '搜索内容', text: '帮我搜索一下标题包含 Python 的文章'},
  {icon: BarChart3, title: '查看统计', text: '我的博客目前有多少篇文章和用户？'},
  {icon: Hash, title: '管理分类', text: '帮我列出所有文章分类'},
];

// ─── Settings Modal ─────────────────────────────

function SettingsModal({config, onChange, onClose}: {
  config: LLMConfig; onChange: (patch: Partial<LLMConfig>) => void; onClose: () => void;
}) {
  const [showKey, setShowKey] = useState(false);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center"><Settings className="w-4 h-4 text-white"/></div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white">LLM 配置</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"><X className="w-5 h-5"/></button>
        </div>
        <div className="px-5 py-5 space-y-4">
          <div><label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">API 端点</label>
            <input type="text" value={config.endpoint} onChange={e => onChange({endpoint: e.target.value})} placeholder="https://api.openai.com/v1"
                   className="w-full px-3.5 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400"/></div>
          <div><label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">API Key</label>
            <div className="relative">
              <input type={showKey ? 'text' : 'password'} value={config.apiKey} onChange={e => onChange({apiKey: e.target.value})} placeholder="sk-..."
                     className="w-full px-3.5 py-2.5 pr-10 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400 font-mono"/>
              <button onClick={() => setShowKey(!showKey)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs font-medium">{showKey ? '隐藏' : '显示'}</button>
            </div></div>
          <div><label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">模型</label>
            <input type="text" value={config.model} onChange={e => onChange({model: e.target.value})} placeholder="gpt-4o-mini"
                   className="w-full px-3.5 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400"/></div>
          <div><label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">系统提示词</label>
            <textarea value={config.systemPrompt} onChange={e => onChange({systemPrompt: e.target.value})} rows={5}
                      className="w-full px-3.5 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 dark:text-white placeholder-gray-400 resize-none font-mono text-[12px]"/></div>
        </div>
        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
          <span className="text-[11px] text-gray-400 dark:text-gray-500">配置保存在浏览器本地</span>
          <button onClick={onClose} className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium rounded-xl transition-colors">完成</button>
        </div>
      </div>
    </div>
  );
}


// ─── Main Component ────────────────────────────

export default function AIChat() {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [checkpoints, setCheckpoints] = useState<CheckpointInfo[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [mounted, setMounted] = useState(false);

  const msgEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const activeConv = conversations.find(c => c.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  // ── Hydrate ──
  useEffect(() => {
    setMounted(true);
    try { const s = localStorage.getItem(CFG_KEY); if (s) setConfig(prev => ({...prev, ...JSON.parse(s)})); } catch {}
    try { const s = localStorage.getItem(CONS_KEY); if (s) { const list: Conversation[] = JSON.parse(s); setConversations(list); if (list.length > 0 && !activeConvId) setActiveConvId(list[0].id); } } catch {}
    setDarkMode(document.documentElement.classList.contains('dark'));
  }, []);

  useEffect(() => { if (!mounted) return; localStorage.setItem(CFG_KEY, JSON.stringify(config)); }, [config, mounted]);
  useEffect(() => { if (!mounted) return; localStorage.setItem(CONS_KEY, JSON.stringify(conversations)); }, [conversations, mounted]);
  useEffect(() => { msgEndRef.current?.scrollIntoView({behavior: 'smooth'}); }, [messages, loading]);

  const toggleDark = useCallback(() => { setDarkMode(p => { const n = !p; document.documentElement.classList.toggle('dark', n); return n; }); }, []);

  const newConversation = useCallback(() => {
    const id = genId(); setConversations(prev => [{id, title: '新对话', messages: [], createdAt: Date.now()}, ...prev]); setActiveConvId(id); setInput(''); setCheckpoints([]); setShowHistory(false);
  }, []);

  const updateConv = useCallback((convId: string, msgs: ChatMessage[], title?: string) => {
    setConversations(prev => prev.map(c => c.id !== convId ? c : {...c, messages: msgs, title: title || c.title, interrupted: false}));
  }, []);

  // ── Send message (SSE streaming via EventSource) ──
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || !config.apiKey) return;
    setInput('');

    let convId = activeConvId;
    if (!convId) {
      const newId = genId();
      convId = newId;
      setConversations(prev => [{id: newId, title: truncate(text, 40), messages: [], createdAt: Date.now()}, ...prev]);
      setActiveConvId(convId);
    }

    const curMsgs = conversations.find(c => c.id === convId)?.messages || [];
    const newMessages = [...curMsgs, {role: 'user', content: text} as ChatMessage];
    updateConv(convId, newMessages, undefined);
    setLoading(true);
    setStreaming(true);

    // Build request body
    const body = JSON.stringify({
      endpoint: config.endpoint,
      api_key: config.apiKey,
      model: config.model,
      messages: newMessages.map(m => ({
        role: m.role, content: m.content || null,
        tool_calls: m.tool_calls, tool_call_id: m.tool_call_id, name: m.name,
      })),
      conversation_id: convId,
      system_prompt: config.systemPrompt,
    });

    const controller = new AbortController();
    abortRef.current = controller;
    const streamingAccumulator: ChatMessage[] = [...newMessages];

    try {
      const apiBase = getConfig().API_BASE_URL;
      const response = await fetch(`${apiBase}/api/v2/mcp/chat/stream`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body,
        signal: controller.signal,
      });

      if (!response.ok) {
        streamingAccumulator.push({role: 'assistant', content: `⚠️ 请求失败 (${response.status})，请检查配置`});
        updateConv(convId, streamingAccumulator);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        streamingAccumulator.push({role: 'assistant', content: '❌ 无法读取响应流'});
        updateConv(convId, streamingAccumulator);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let lastUiUpdate = 0;

      while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = JSON.parse(line.slice(6));

          if (data.type === 'done') break;
          if (data.type === 'error') {
            streamingAccumulator.push({role: 'assistant', content: `❌ ${data.message}`});
            updateConv(convId, streamingAccumulator);
            return;
          }

          // Accumulate content
          if (data.assistant_content) {
            const last = streamingAccumulator[streamingAccumulator.length - 1];
            if (last?.role === 'assistant') {
              last.content = data.assistant_content;
            } else {
              streamingAccumulator.push({role: 'assistant', content: data.assistant_content, tool_calls: data.tool_calls});
            }
          }
          if (data.tool_calls && streamingAccumulator[streamingAccumulator.length - 1]?.role === 'assistant') {
            streamingAccumulator[streamingAccumulator.length - 1].tool_calls = data.tool_calls;
          }
          if (data.tool_results) {
            for (const [name, result] of Object.entries(data.tool_results)) {
              streamingAccumulator.push({role: 'tool', content: JSON.stringify(result, null, 2), name});
            }
          }

          // Throttle UI updates to every 100ms or on interrupt
          const now = Date.now();
          if (now - lastUiUpdate > 100 || data.interrupted) {
            setConversations(prev => prev.map(c => c.id !== convId ? c : {
              ...c, messages: [...streamingAccumulator], interrupted: data.interrupted || false
            }));
            lastUiUpdate = now;
          }
        }
      }

      // Final UI sync
      setConversations(prev => prev.map(c => c.id !== convId ? c : {
        ...c, messages: streamingAccumulator
      }));
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        streamingAccumulator.push({role: 'assistant', content: `❌ ${err?.message || '请求失败'}`});
        updateConv(convId, streamingAccumulator);
      }
    } finally {
      setLoading(false);
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, loading, config, activeConvId, conversations, updateConv]);

  // ── Interrupt ──
  const handleInterrupt = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setLoading(false);
    setStreaming(false);
  }, []);

  // ── Load checkpoints ──
  const loadCheckpoints = useCallback(async () => {
    if (!activeConvId) return;
    try {
      const res = await apiClient.get(`/mcp/chat/${activeConvId}/checkpoints`);
      if (res.success) setCheckpoints(res.data || []);
    } catch {}
  }, [activeConvId]);

  // ── Backtrack to step ──
  const handleBacktrack = useCallback(async (step: number) => {
    if (!activeConvId) return;
    try {
      const res = await apiClient.post(`/mcp/chat/${activeConvId}/backtrack?step=${step}`);
      if (res.success && res.data) {
        setConversations(prev => prev.map(c => c.id !== activeConvId ? c : {...c, messages: res.data.messages || []}));
        setShowHistory(false);
      }
    } catch {}
  }, [activeConvId]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }, [sendMessage]);

  const [toastMsg, setToastMsg] = useState('');
  const showToast = useCallback((t: string) => { setToastMsg(t); setTimeout(() => setToastMsg(''), 2000); }, []);
  const updateConfig = useCallback((patch: Partial<LLMConfig>) => setConfig(prev => ({...prev, ...patch})), []);

  const handleSuggestion = useCallback((text: string) => { setInput(text); }, []);

  return (
    <div className="h-dvh flex bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 overflow-hidden">
      {toastMsg && <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[60] px-4 py-2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm rounded-xl shadow-lg animate-fade-in">{toastMsg}</div>}

      {/* ─── Sidebar ── */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 overflow-hidden flex flex-col`}>
        <div className="flex items-center justify-between h-14 px-4 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center"><Sparkles className="w-3.5 h-3.5 text-white"/></div>
            <span className="font-bold text-sm text-gray-900 dark:text-white">AI Chat</span>
          </div>
          <button onClick={newConversation} className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400"><Plus className="w-4 h-4"/></button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {conversations.length === 0 && (
            <div className="text-center py-8"><MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-300 dark:text-gray-600"/><p className="text-xs text-gray-400 dark:text-gray-500">暂无对话</p></div>
          )}
          {conversations.map(conv => (
            <div key={conv.id} onClick={() => { setActiveConvId(conv.id); setShowHistory(false); }} role="button" tabIndex={0}
                 onKeyDown={(e) => e.key === 'Enter' && setActiveConvId(conv.id)}
                 className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-left text-sm transition-colors group cursor-pointer ${
                   conv.id === activeConvId ? 'bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700' : 'hover:bg-gray-100 dark:hover:bg-gray-800/50 border border-transparent'}`}>
              <MessageSquare className="w-4 h-4 flex-shrink-0 text-gray-400"/>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex items-center gap-1">
                  {conv.title}
                  {conv.interrupted && <Pause className="w-3 h-3 text-amber-500 flex-shrink-0"/>}
                </div>
                <div className="text-[10px] text-gray-400 dark:text-gray-500">{fmtDate(conv.createdAt)}</div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); setConversations(prev => { const n = prev.filter(c => c.id !== conv.id); if (activeConvId === conv.id) setActiveConvId(n.length > 0 ? n[0].id : null); return n; }); }}
                      className="p-1 rounded-md text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0">
                <Trash2 className="w-3.5 h-3.5"/></button>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
          <button onClick={newConversation} className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 text-sm transition-colors">
            <Plus className="w-4 h-4"/><span>新对话</span>
          </button>
        </div>
      </aside>

      {/* ─── Main ── */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="flex items-center gap-2">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
              {sidebarOpen ? <PanelLeftClose className="w-4 h-4"/> : <PanelLeftOpen className="w-4 h-4"/>}
            </button>
            {activeConv && <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-[200px] sm:max-w-sm">{activeConv.title}</h1>}
            {!config.apiKey && <span className="ml-2 px-2 py-0.5 text-[10px] font-medium rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">未配置</span>}
            {activeConv?.interrupted && <span className="ml-2 px-2 py-0.5 text-[10px] font-medium rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">已中断</span>}
          </div>
          <div className="flex items-center gap-1">
            {activeConv && messages.length > 0 && (
              <>
                <button onClick={() => { loadCheckpoints(); setShowHistory(!showHistory); }}
                        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 transition-colors" title="历史状态">
                  <History className="w-4 h-4"/>
                </button>
                <button onClick={() => { setConversations(prev => prev.map(c => c.id === activeConvId ? {...c, messages: []} : c)); setInput(''); }}
                        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-red-500 transition-colors" title="清空">
                  <Trash2 className="w-4 h-4"/>
                </button>
              </>
            )}
            <button onClick={toggleDark} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">{darkMode ? <Sun className="w-4 h-4"/> : <Moon className="w-4 h-4"/>}</button>
            <button onClick={() => setSettingsOpen(true)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"><Settings className="w-4 h-4"/></button>
          </div>
        </header>

        {/* ─── Checkpoint History Panel ── */}
        {showHistory && checkpoints.length > 0 && (
          <div className="border-b border-gray-200 dark:border-gray-800 bg-amber-50/50 dark:bg-amber-900/10 px-4 py-3 animate-slide-down">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-1"><Undo2 className="w-3 h-3"/>状态回溯</span>
              <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-gray-600"><X className="w-3.5 h-3.5"/></button>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {checkpoints.map((cp) => (
                <button key={cp.id} onClick={() => handleBacktrack(cp.step)}
                        className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                          cp.interrupted
                            ? 'border-amber-300 dark:border-amber-700 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                        }`}>
                  <div className="font-medium">#{cp.step} {cp.current_node}</div>
                  <div className="opacity-70">{cp.messages_count} 条消息</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ─── Messages ── */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-100 via-blue-100 to-indigo-100 dark:from-violet-900/30 dark:via-blue-900/30 dark:to-indigo-900/30 flex items-center justify-center mb-6 shadow-lg shadow-violet-200/20 dark:shadow-none">
                  <Sparkles className="w-10 h-10 text-violet-500 dark:text-violet-400"/>
                </div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">有什么我可以帮你的？</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-8 max-w-md">
                  {config.apiKey ? '通过自然语言管理你的博客内容，AI 会自动调用 MCP 工具完成操作' : '请先点击右上角设置按钮配置 LLM API 端点'}
                </p>
                {!config.apiKey ? (
                  <button onClick={() => setSettingsOpen(true)} className="px-6 py-3 bg-gradient-to-r from-violet-600 to-blue-600 text-white text-sm font-medium rounded-xl hover:opacity-90 transition-all shadow-lg shadow-violet-500/20">配置 API</button>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                    {SUGGESTIONS.map((item, i) => (
                      <button key={i} onClick={() => handleSuggestion(item.text)}
                              className="flex items-start gap-3 p-4 rounded-2xl bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 hover:border-violet-200 dark:hover:border-violet-700/50 hover:shadow-md transition-all text-left group">
                        <div className="w-9 h-9 rounded-xl bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center flex-shrink-0 group-hover:bg-violet-100 dark:group-hover:bg-violet-900/30 transition-colors">
                          <item.icon className="text-violet-600 dark:text-violet-400" style={{width: 18, height: 18}}/>
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-gray-900 dark:text-white mb-0.5">{item.title}</div>
                          <div className="text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed line-clamp-2">{item.text}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              messages.map((msg, i) => <ChatBubble key={i} msg={msg} onCopy={showToast}/>)
            )}
            {loading && !streaming && <ThinkingDots/>}
            <div ref={msgEndRef}/>
          </div>
        </div>

        {/* ── Input ── */}
        <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3">
            <div className="flex items-end gap-2 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-violet-500 focus-within:border-violet-500 transition-all">
              <textarea
                value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
                placeholder={config.apiKey ? '输入消息...' : '请先配置 API Key'}
                disabled={!config.apiKey || loading} rows={1}
                className="flex-1 bg-transparent text-sm dark:text-white placeholder-gray-400 resize-none outline-none max-h-32 leading-relaxed"
                onInput={e => { const el = e.currentTarget; el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 128)}px`; }}
              />
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {loading ? (
                  <button onClick={handleInterrupt} className="p-2 rounded-xl bg-red-500 text-white hover:bg-red-600 transition-all flex-shrink-0 shadow-sm">
                    <Pause className="w-4 h-4"/>
                  </button>
                ) : (
                  <button onClick={sendMessage} disabled={!input.trim() || !config.apiKey}
                          className="p-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 text-white hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-sm">
                    <Send className="w-4 h-4"/>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {settingsOpen && <SettingsModal config={config} onChange={updateConfig} onClose={() => setSettingsOpen(false)}/>}

      <style>{`
        @keyframes fade-in { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slide-down { from { opacity: 0; max-height: 0; } to { opacity: 1; max-height: 300px; } }
        .animate-fade-in { animation: fade-in 0.2s ease-out; }
        .animate-slide-down { animation: slide-down 0.3s ease-out; overflow: hidden; }
        .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
      `}</style>
    </div>
  );
}
