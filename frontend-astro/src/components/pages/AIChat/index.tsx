'use client';

import React, {useState, useRef, useEffect, useCallback} from 'react';
import {Menu, Trash2, PanelLeftClose, PanelLeft, Sun, Moon} from 'lucide-react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {getConfig} from '@/lib/config';
import {useDarkMode} from '@/lib/dark-mode-manager';

import type {Conversation, ChatMessage} from './types';
import {DEFAULT_CONFIG, CFG_KEY, CONS_KEY, genId, trunc} from './types';
import Sidebar from './Sidebar';
import ChatBubble, {ThinkingIndicator} from './ChatBubble';
import ChatInput from './ChatInput';
import EmptyState from './EmptyState';
import SettingsModal from './SettingsModal';

// ─── Types ──────────────────────────────────────

interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

// ─── Main Component ────────────────────────────

export default function AIChatGuard() {
  return <AuthGuard><QueryProvider><AIChatInner /></QueryProvider></AuthGuard>;
}

function AIChatInner() {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  const msgEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const {theme, toggleTheme} = useDarkMode();

  const activeConv = conversations.find(c => c.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  // ── Hydrate from localStorage ──
  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem(CFG_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.endpoint || parsed.apiKey || parsed.model) {
          setConfig(prev => ({...prev, ...parsed}));
        }
      }
    } catch { /* ignore */ }
    try {
      const saved = localStorage.getItem(CONS_KEY);
      if (saved) {
        const list: Conversation[] = JSON.parse(saved);
        setConversations(list);
        if (list.length > 0) setActiveConvId(list[0].id);
      }
    } catch { /* ignore */ }
  }, []);

  // ── Persist to localStorage ──
  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem(CFG_KEY, JSON.stringify(config));
  }, [config, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem(CONS_KEY, JSON.stringify(conversations));
  }, [conversations, mounted]);

  // ── Auto-scroll ──
  useEffect(() => {
    msgEndRef.current?.scrollIntoView({behavior: 'smooth'});
  }, [messages, loading]);

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
              acc.push({role: 'tool', content: JSON.stringify({
                name: data.name, args: data.args,
                result: null, done: false,
              })});
              setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
            }
            if (data.type === 'tool_result') {
              for (let i = acc.length - 1; i >= 0; i--) {
                if (acc[i].role === 'tool') {
                  try {
                    const td = JSON.parse(acc[i].content);
                    if (td.name === data.name) {
                      td.result = data.content;
                      td.done = true;
                      acc[i] = {...acc[i], content: JSON.stringify(td)};
                      break;
                    }
                  } catch { /* ignore */ }
                }
              }
              setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: [...acc]}));
            }
          } catch { /* ignore */ }
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

  const handleInterrupt = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }, []);

  const needsConfig = !config.endpoint || !config.model;

  return (
    <div className="h-screen flex bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-950 dark:to-gray-900 text-gray-900 dark:text-gray-100 overflow-hidden">
      {/* ─── Sidebar ── */}
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={setActiveConvId}
        onNew={newConversation}
        onDelete={deleteConversation}
        collapsed={!sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onSettings={() => setSettingsOpen(true)}
      />

      {/* ─── Main Area ── */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Top Bar */}
        <header className="h-14 flex items-center justify-between px-4 border-b border-gray-200/80 dark:border-gray-800/80 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md flex-shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors hidden lg:flex"
              title={sidebarOpen ? '收起侧栏' : '展开侧栏'}
            >
              {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 transition-colors lg:hidden"
            >
              <Menu className="w-4 h-4" />
            </button>
            {activeConv && (
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-[240px] ml-1">
                {activeConv.title}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {activeConv && messages.length > 0 && (
              <button
                onClick={() => {
                  setConversations(prev => prev.map(c => c.id === activeConvId ? {...c, messages: []} : c));
                }}
                className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                title="清空对话"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              title={theme === 'dark' ? '切换亮色模式' : '切换暗色模式'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-4">
            {messages.length === 0 ? (
              <EmptyState
                needsConfig={needsConfig}
                onOpenSettings={() => setSettingsOpen(true)}
                onSuggestionClick={setInput}
              />
            ) : (
              <>
                {/* Context hint */}
                <div className="flex items-center justify-center mb-2">
                  <div className="px-3 py-1 bg-violet-50 dark:bg-violet-900/20 rounded-full border border-violet-100 dark:border-violet-800/30">
                    <span className="text-[10px] text-violet-600 dark:text-violet-400 font-medium">
                      {activeConv?.title || 'AI 对话'}
                    </span>
                  </div>
                </div>
                {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
              </>
            )}
            {loading && <ThinkingIndicator />}
            <div ref={msgEndRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput
          input={input}
          loading={loading}
          disabled={needsConfig}
          onInput={setInput}
          onSend={sendMessage}
          onInterrupt={handleInterrupt}
        />
      </div>

      {/* Settings Modal */}
      <SettingsModal config={config} onChange={updateConfig} onClose={() => setSettingsOpen(false)} show={settingsOpen} />
    </div>
  );
}
