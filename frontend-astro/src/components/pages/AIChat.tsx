'use client';

import React, {useState, useRef, useEffect, useCallback} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {
  Send, Settings, X, Bot, User, Wrench, CheckCircle, AlertCircle,
  Moon, Sun, Trash2, ChevronDown, ChevronUp, Sparkles, MessageSquare,
  Loader2,
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

interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

const DEFAULT_CONFIG: LLMConfig = {
  endpoint: 'https://api.openai.com/v1',
  apiKey: '',
  model: 'gpt-4o-mini',
  systemPrompt: `你是 FastBlog 的 AI 助手，可以帮助用户管理博客内容。

你可以执行以下操作：
1. 创建文章 - 提供标题和内容即可
2. 更新文章 - 指定文章 ID 和要更新的字段
3. 删除文章 - 指定文章 ID
4. 搜索文章 - 提供关键词
5. 查看分类列表
6. 创建分类
7. 查看系统统计信息

请使用中文回复，保持专业且友好的语气。`,
};

const STORAGE_KEY = 'fastblog-ai-chat-config';
const HISTORY_KEY = 'fastblog-ai-chat-history';

// ─── Component ──────────────────────────────────

export default function AIChat() {
  const [config, setConfig] = useState<LLMConfig>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? {...DEFAULT_CONFIG, ...JSON.parse(saved)} : DEFAULT_CONFIG;
    } catch { return DEFAULT_CONFIG; }
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(HISTORY_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfig, setShowConfig] = useState(!config.apiKey);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof document === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  });

  const msgEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Save to localStorage ──
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(config)); }, [config]);
  useEffect(() => { localStorage.setItem(HISTORY_KEY, JSON.stringify(messages)); }, [messages]);

  // ── Auto scroll ──
  useEffect(() => { msgEndRef.current?.scrollIntoView({behavior: 'smooth'}); }, [messages]);

  // ── Dark mode toggle ──
  const toggleDark = useCallback(() => {
    const next = !darkMode;
    setDarkMode(next);
    document.documentElement.classList.toggle('dark', next);
  }, [darkMode]);

  // ── Update config ──
  const updateConfig = useCallback((patch: Partial<LLMConfig>) => {
    setConfig(prev => ({...prev, ...patch}));
  }, []);

  // ── Send message ──
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || !config.apiKey) return;
    setInput('');

    const userMsg: ChatMessage = {role: 'user', content: text};
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setLoading(true);

    try {
      const res = await apiClient.post('/mcp/chat/completions', {
        endpoint: config.endpoint,
        api_key: config.apiKey,
        model: config.model,
        messages: [
          {role: 'system', content: config.systemPrompt},
          ...newMessages.map(m => ({
            role: m.role,
            content: m.content || null,
            tool_calls: m.tool_calls,
            tool_call_id: m.tool_call_id,
            name: m.name,
          })),
        ],
      });

      if (res.success && res.data) {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: res.data.content || '',
          tool_calls: res.data.tool_calls,
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `⚠️ 请求失败：${res.error || res.message || '未知错误'}`,
        }]);
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ 网络错误：${err?.message || '无法连接服务器'}`,
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, config, messages]);

  // ── Keyboard shortcut ──
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // ── Clear history ──
  const clearHistory = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  // ── Render message content with tool calls ──
  const renderMessage = (msg: ChatMessage, i: number) => {
    const isUser = msg.role === 'user';
    const isAssistant = msg.role === 'assistant';
    const isTool = msg.role === 'tool';

    return (
      <div key={i} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-fade-in`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
          isUser ? 'bg-blue-100 dark:bg-blue-900/40' :
          isTool ? 'bg-amber-100 dark:bg-amber-900/40' :
          'bg-purple-100 dark:bg-purple-900/40'
        }`}>
          {isUser ? <User className="w-4 h-4 text-blue-600 dark:text-blue-400"/> :
           isTool ? <Wrench className="w-4 h-4 text-amber-600 dark:text-amber-400"/> :
           <Bot className="w-4 h-4 text-purple-600 dark:text-purple-400"/>}
        </div>

        {/* Content */}
        <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
          {/* Role label */}
          <span className="text-xs text-gray-400 dark:text-gray-500 mb-1 px-1">
            {isUser ? '你' : isTool ? '工具调用' : 'AI'}
          </span>

          {/* Text content */}
          {msg.content && (
            <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
              isUser
                ? 'bg-blue-600 text-white rounded-br-md'
                : isTool
                  ? 'bg-amber-50 dark:bg-amber-900/20 text-gray-700 dark:text-gray-300 border border-amber-200 dark:border-amber-800 rounded-br-md font-mono text-xs'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md'
            }`}>
              {msg.content}
            </div>
          )}

          {/* Tool calls inline */}
          {msg.tool_calls && msg.tool_calls.length > 0 && (
            <div className="mt-2 space-y-1.5 w-full">
              {msg.tool_calls.map((tc, j) => {
                let args: any = {};
                try { args = JSON.parse(tc.function.arguments); } catch {}
                return (
                  <div key={j} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 text-xs">
                    <Wrench className="w-3.5 h-3.5 text-purple-500"/>
                    <span className="font-medium text-purple-700 dark:text-purple-300">{tc.function.name}</span>
                    <span className="text-gray-400 dark:text-gray-500 truncate">
                      {Object.entries(args).map(([k, v]) => `${k}=${typeof v === 'string' ? v.slice(0, 30) : JSON.stringify(v)}`).join(', ')}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      {/* ── Header ── */}
      <header className="h-14 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white"/>
          </div>
          <h1 className="text-base font-bold text-gray-900 dark:text-white">AI Chat</h1>
          {!config.apiKey && (
            <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-medium">未配置</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={clearHistory} disabled={messages.length === 0}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-red-500 disabled:opacity-30" title="清空对话">
            <Trash2 className="w-4 h-4"/>
          </button>
          <button onClick={toggleDark}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
            {darkMode ? <Sun className="w-4 h-4"/> : <Moon className="w-4 h-4"/>}
          </button>
          <button onClick={() => setShowConfig(!showConfig)}
                  className={`p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${showConfig ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-400'}`}>
            <Settings className="w-4 h-4"/>
          </button>
        </div>
      </header>

      {/* ── Config Panel ── */}
      {showConfig && (
        <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-4 space-y-3 animate-slide-down">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
            <Settings className="w-4 h-4"/> LLM 配置
          </h3>
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">API 端点</label>
              <input type="text" value={config.endpoint} onChange={e => updateConfig({endpoint: e.target.value})}
                     placeholder="https://api.openai.com/v1"
                     className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">API Key</label>
              <input type="password" value={config.apiKey} onChange={e => updateConfig({apiKey: e.target.value})}
                     placeholder="sk-..."
                     className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">模型</label>
              <input type="text" value={config.model} onChange={e => updateConfig({model: e.target.value})}
                     placeholder="gpt-4o-mini"
                     className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">系统提示词</label>
              <textarea value={config.systemPrompt} onChange={e => updateConfig({systemPrompt: e.target.value})}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"/>
            </div>
          </div>
          {!config.apiKey && (
            <p className="text-xs text-amber-500 flex items-center gap-1">
              <AlertCircle className="w-3 h-3"/> 请在上方填入 API Key 以开始对话
            </p>
          )}
        </div>
      )}

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-100 to-blue-100 dark:from-purple-900/30 dark:to-blue-900/30 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-purple-500 dark:text-purple-400"/>
            </div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">开始 AI 对话</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-6">
              配置你的 LLM API 后，即可通过自然语言管理博客内容
            </p>
            <div className="grid sm:grid-cols-3 gap-3 max-w-lg w-full">
              {[
                {icon: '📝', title: '创建文章', desc: '让 AI 帮你撰写和发布'},
                {icon: '🔍', title: '搜索内容', desc: '快速查找任何文章'},
                {icon: '📊', title: '查看统计', desc: '了解博客运行状况'},
              ].map((item, i) => (
                <div key={i} className="p-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-left">
                  <div className="text-xl mb-1">{item.icon}</div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">{item.title}</div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => renderMessage(msg, i))
        )}
        {loading && (
          <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin"/>
            <span className="text-sm">AI 思考中...</span>
          </div>
        )}
        <div ref={msgEndRef}/>
      </div>

      {/* ── Input ── */}
      <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3 flex-shrink-0">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={config.apiKey ? '输入消息，Enter 发送，Shift+Enter 换行...' : '请先在上方配置 API Key'}
            disabled={!config.apiKey || loading}
            rows={1}
            className="flex-1 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none max-h-32"
            onInput={e => {
              const el = e.currentTarget;
              el.style.height = 'auto';
              el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
            }}
          />
          <button onClick={sendMessage} disabled={!input.trim() || loading || !config.apiKey}
                  className="p-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:opacity-90 disabled:opacity-40 transition-all flex-shrink-0">
            {loading ? <Loader2 className="w-5 h-5 animate-spin"/> : <Send className="w-5 h-5"/>}
          </button>
        </div>
      </div>

      {/* ── Styles ── */}
      <style>{`
        @keyframes fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slide-down { from { opacity: 0; max-height: 0; } to { opacity: 1; max-height: 400px; } }
        .animate-fade-in { animation: fade-in 0.3s ease-out; }
        .animate-slide-down { animation: slide-down 0.3s ease-out; overflow: hidden; }
      `}</style>
    </div>
  );
}
