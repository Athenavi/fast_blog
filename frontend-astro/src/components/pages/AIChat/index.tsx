'use client';

import React, {useState, useRef, useEffect, useCallback} from 'react';
import {Menu, Trash2, PanelLeftClose, PanelLeft, Sun, Moon} from 'lucide-react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {getConfig} from '@/lib/config';
import {useDarkMode} from '@/lib/dark-mode-manager';

import type {Conversation, ChatMessage, AgentMode, PlanStep} from './types';
import {
  DEFAULT_CONFIG, CFG_KEY, CONS_KEY, genId, trunc,
  REACT_SYSTEM_PROMPT, PLAN_EXECUTE_SYSTEM_PROMPT, REFLEXION_SYSTEM_PROMPT,
  parsePlan, parseEvaluation, stripXmlTags,
} from './types';
import {parseToolCalls, executeToolCall} from './tools';
import Sidebar from './Sidebar';
import ChatBubble, {ThinkingIndicator} from './ChatBubble';
import ChatInput from './ChatInput';
import EmptyState from './EmptyState';
import SettingsModal from './SettingsModal';
import AgentModeSelector from './AgentModeSelector';

// ─── Types ──────────────────────────────────────

interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

const MAX_REACT_ITERATIONS = 5;

// ─── System prompt per mode ────────────────────

function getSystemPrompt(mode: AgentMode): string {
  switch (mode) {
    case 'plan-execute': return PLAN_EXECUTE_SYSTEM_PROMPT;
    case 'reflexion':    return REFLEXION_SYSTEM_PROMPT;
    default:             return REACT_SYSTEM_PROMPT;
  }
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

  // 代理模式
  const [agentMode, setAgentMode] = useState<AgentMode>('react');
  // Plan-and-Execute 状态
  const [planSteps, setPlanSteps] = useState<PlanStep[]>([]);
  const [planPhase, setPlanPhase] = useState<'idle' | 'planning' | 'executing' | 'done'>('idle');
  // Reflexion 状态
  const [reflexionPhase, setReflexionPhase] = useState<'idle' | 'evaluating' | 'improving' | 'done'>('idle');

  const msgEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const {theme, toggleTheme} = useDarkMode();

  const activeConv = conversations.find(c => c.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  // ── Hydrate ──
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

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem(CFG_KEY, JSON.stringify(config));
  }, [config, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem(CONS_KEY, JSON.stringify(conversations));
  }, [conversations, mounted]);

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({behavior: 'smooth'});
  }, [messages, loading]);

  const newConversation = useCallback(() => {
    const id = genId();
    setConversations(prev => [{id, title: '新对话', messages: [], createdAt: Date.now(), mode: agentMode}, ...prev]);
    setActiveConvId(id);
    setPlanSteps([]);
    setPlanPhase('idle');
    setReflexionPhase('idle');
  }, [agentMode]);

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

  const handleModeChange = useCallback((mode: AgentMode) => {
    setAgentMode(mode);
    // 同步更新 system prompt
    setConfig(prev => ({...prev, systemPrompt: getSystemPrompt(mode)}));
    // 重置模式相关状态
    setPlanSteps([]);
    setPlanPhase('idle');
    setReflexionPhase('idle');
  }, []);

  // ── doStream ──
  const doStream = useCallback(async (
    finalConvId: string,
    msgs: ChatMessage[],
    controller: AbortController,
    onUpdate: (updated: ChatMessage[]) => void,
    promptOverride?: string,
  ): Promise<ChatMessage[]> => {
    const acc: ChatMessage[] = [...msgs];
    const sp = promptOverride || config.systemPrompt;

    const body = JSON.stringify({
      endpoint: config.endpoint,
      api_key: config.apiKey,
      model: config.model,
      messages: msgs.map(m => ({role: m.role, content: m.content})),
      conversation_id: finalConvId,
      system_prompt: sp,
    });

    try {
      const base = getConfig().API_BASE_URL;
      const resp = await fetch(`${base}/api/v2/mcp/chat/stream`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body, signal: controller.signal,
        credentials: 'include',
      });
      if (!resp.ok) {
        acc.push({role: 'assistant', content: `⚠️ 请求失败 (${resp.status})`});
        return acc;
      }

      const reader = resp.body?.getReader();
      if (!reader) return acc;
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
              onUpdate([...acc]);
              return acc;
            }
            if (data.type === 'token' && data.content) {
              const last = acc[acc.length - 1];
              if (last?.role === 'assistant') {
                last.content = (last.content || '') + data.content;
              } else {
                acc.push({role: 'assistant', content: data.content});
              }
              onUpdate([...acc]);
            }
            if (data.type === 'tool_call') {
              acc.push({role: 'tool', content: JSON.stringify({
                name: data.name, args: data.args, result: null, done: false,
              })});
              onUpdate([...acc]);
            }
            if (data.type === 'tool_result') {
              for (let i = acc.length - 1; i >= 0; i--) {
                if (acc[i].role === 'tool') {
                  try {
                    const td = JSON.parse(acc[i].content);
                    if (td.name === data.name) {
                      td.result = data.content; td.done = true;
                      acc[i] = {...acc[i], content: JSON.stringify(td)};
                      break;
                    }
                  } catch { /* ignore */ }
                }
              }
              onUpdate([...acc]);
            }
          } catch { /* ignore */ }
        }
      }
      return acc;
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        acc.push({role: 'assistant', content: `❌ ${err?.message || '请求失败'}`});
        onUpdate([...acc]);
      }
      return acc;
    }
  }, [config]);

  // ── ReAct 子循环（在 assistant 文本中检测并执行工具调用）──
  const reactSubLoop = useCallback(async (
    finalConvId: string,
    msgs: ChatMessage[],
    promptOverride?: string,
  ): Promise<ChatMessage[]> => {
    let currentMsgs = [...msgs];

    for (let iter = 0; iter < MAX_REACT_ITERATIONS; iter++) {
      setLoading(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const onUpdate = (updated: ChatMessage[]) => {
        setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: updated}));
      };

      currentMsgs = await doStream(finalConvId, currentMsgs, controller, onUpdate, promptOverride);
      abortRef.current = null;
      setLoading(false);

      // 更新 UI
      setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: currentMsgs}));

      // 检查文本工具调用
      const lastMsg = currentMsgs[currentMsgs.length - 1];
      if (!lastMsg || lastMsg.role !== 'assistant') break;

      const toolCalls = parseToolCalls(lastMsg.content || '');
      if (toolCalls.length === 0) break;

      // 清洗原始工具调用文本
      let cleanContent = (lastMsg.content || '')
        .replace(/<tool_calls>[\s\S]*?<\/tool_calls>/g, '')
        .replace(/```(?:json)?\s*\{[\s\S]*?\}\s*```/g, '')
        .replace(/\{\s*"(?:function|name|tool)"\s*:\s*"[^"]+"[\s\S]*?\}/g, '')
        .trim();

      // 检测并分离 <thought> 标签作为 reasoning 步骤
      const thoughtContents: string[] = [];
      cleanContent = cleanContent.replace(/<thought>([\s\S]*?)<\/thought>/g, (_, thought) => {
        thoughtContents.push(thought.trim());
        return '';
      }).trim();

      const hasCleanContent = cleanContent.length > 0;

      // 执行工具
      setLoading(true);
      for (const tc of toolCalls) {
        const toolResult = await executeToolCall(tc.name, tc.args);
        const toolMsg: ChatMessage = {
          role: 'tool',
          content: JSON.stringify({name: tc.name, args: tc.args, result: toolResult.success ? toolResult.result : null, done: true}),
        };

        // 如果有清干净的文本，更新最后一条 assistant 消息
        if (hasCleanContent && (toolCalls.length === 1 || tc === toolCalls[0])) {
          currentMsgs[currentMsgs.length - 1] = {
            ...currentMsgs[currentMsgs.length - 1],
            content: cleanContent,
          };
        }

        // 插入 reasoning 步骤
        for (const thought of thoughtContents) {
          currentMsgs.push({role: 'assistant', content: thought, displayType: 'reasoning'});
        }

        currentMsgs.push(toolMsg);
        setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: currentMsgs}));
      }
      setLoading(false);

      // 进下一轮让 LLM 看到工具结果
      promptOverride = undefined; // 后续轮次使用当前 system prompt
    }

    return currentMsgs;
  }, [doStream]);

  // ── 发送消息 ──
  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');

    if (!config.endpoint || !config.model) {
      setSettingsOpen(true);
      return;
    }

    const finalConvId = activeConvId || genId();
    const isNew = !activeConvId;
    if (isNew) {
      setConversations(prev => [{
        id: finalConvId, title: trunc(text, 40), messages: [], createdAt: Date.now(), mode: agentMode,
      }, ...prev]);
      setActiveConvId(finalConvId);
    }

    const latestConv = isNew ? null : conversations.find(c => c.id === finalConvId);
    let msgs: ChatMessage[] = latestConv
      ? [...latestConv.messages, {role: 'user', content: text}]
      : [{role: 'user', content: text}];

    const mode = agentMode;

    // ═══════════════════════════════════════════
    // Mode 1: ReAct
    // ═══════════════════════════════════════════
    if (mode === 'react') {
      msgs = await reactSubLoop(finalConvId, msgs);
      setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: msgs}));
      return;
    }

    // ═══════════════════════════════════════════
    // Mode 2: Plan & Execute
    // ═══════════════════════════════════════════
    if (mode === 'plan-execute') {
      // Phase 1: 生成计划
      setPlanPhase('planning');
      const planSysPrompt = `${PLAN_EXECUTE_SYSTEM_PROMPT}\n\n用户请求: ${text}\n请先制定一个详细的执行计划（用 <plan> 标签包裹），然后开始执行第一步。`;

      const planMsgs = await reactSubLoop(finalConvId, msgs, planSysPrompt);
      msgs = planMsgs;

      // 从最后一条 assistant 消息中解析计划
      const lastAssistant = [...msgs].reverse().find(m => m.role === 'assistant');
      if (lastAssistant) {
        const plan = parsePlan(lastAssistant.content || '');
        if (plan) {
          // 标记该消息为 plan 类型
          const planMsg: ChatMessage = {
            role: 'assistant',
            content: lastAssistant.content,
            displayType: 'plan',
          };
          msgs[msgs.indexOf(lastAssistant)] = planMsg;
          setPlanSteps(plan.steps.map(s => ({...s, status: 'pending' as const})));
          setPlanPhase('executing');

          // Phase 2: 逐条执行计划
          for (let i = 0; i < plan.steps.length; i++) {
            // 标记当前步骤
            setPlanSteps(prev => prev.map((s, idx) => ({
              ...s,
              status: idx === i ? 'in_progress' as const : s.status,
            })));

            // 执行当前步骤的提示
            const stepPrompt = `继续执行计划。当前是第 ${i + 1} 步: ${plan.steps[i].title}。完成这一步后，进行下一步，直到所有步骤完成。完成后给出总结。`;

            msgs = await reactSubLoop(finalConvId, msgs, stepPrompt);

            // 标记完成
            setPlanSteps(prev => prev.map((s, idx) => ({
              ...s,
              status: idx === i ? 'completed' as const : s.status,
            })));
          }

          setPlanPhase('done');
        }
      }

      setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: msgs}));
      return;
    }

    // ═══════════════════════════════════════════
    // Mode 3: Reflexion
    // ═══════════════════════════════════════════
    if (mode === 'reflexion') {
      // Phase 1: 执行 ReAct
      setReflexionPhase('evaluating');
      msgs = await reactSubLoop(finalConvId, msgs);

      // Phase 2: 评估
      setReflexionPhase('evaluating');
      const evalPrompt = `请评估你上一步执行的质量，使用以下格式：

<evaluation>
  <score>1-10</score>
  <summary>整体评价</summary>
  <issues>
    <issue>问题描述</issue>
  </issues>
  <suggestions>
    <suggestion>改进建议</suggestion>
  </suggestions>
</evaluation>

请务必包含完整的 <evaluation> 标签块。`;

      msgs = await reactSubLoop(finalConvId, msgs, evalPrompt);

      // 分析评估结果
      const evalMsg = [...msgs].reverse().find(m => m.role === 'assistant');
      if (evalMsg) {
        const evaluation = parseEvaluation(evalMsg.content || '');
        if (evaluation) {
          // 标记为 evaluation 类型
          const idx = msgs.indexOf(evalMsg);
          msgs[idx] = {...msgs[idx], displayType: 'evaluation'};
          setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: msgs}));

          // Phase 3: 如果评分不足，优化
          if (evaluation.score < 9) {
            setReflexionPhase('improving');
            const improvePrompt = `根据你的自我评估（评分 ${evaluation.score}/10），请生成一个优化后的最终回复，解决以下问题：${evaluation.issues.join('；')}。给出更完善的版本。`;

            msgs = await reactSubLoop(finalConvId, msgs, improvePrompt);
          }
        }
      }

      setReflexionPhase('done');
      setConversations(p => p.map(c => c.id !== finalConvId ? c : {...c, messages: msgs}));
      return;
    }
  }, [input, loading, config, activeConvId, conversations, agentMode, planPhase, reactSubLoop]);

  const handleInterrupt = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }, []);

  const needsConfig = !config.endpoint || !config.model;

  // 获取当前阶段标签
  const phaseLabel = loading
    ? (agentMode === 'plan-execute'
        ? (planPhase === 'planning' ? '制定计划中…' : planPhase === 'executing' ? '执行计划中…' : '处理中…')
        : agentMode === 'reflexion'
          ? (reflexionPhase === 'evaluating' ? '自我评估中…' : reflexionPhase === 'improving' ? '优化回复中…' : '思考中…')
          : '思考中…')
    : undefined;

  return (
    <div className="h-screen flex bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-950 dark:to-gray-900 text-gray-900 dark:text-gray-100 overflow-hidden">
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

      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Top Bar */}
        <header className="h-14 flex items-center justify-between px-4 border-b border-gray-200/80 dark:border-gray-800/80 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md flex-shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors hidden lg:flex"
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
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-[180px] ml-1">
                {activeConv.title}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Agent Mode Selector */}
            <AgentModeSelector mode={agentMode} onChange={handleModeChange} />

            <div className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-0.5" />

            {activeConv && messages.length > 0 && (
              <button
                onClick={() => {
                  setConversations(prev => prev.map(c => c.id === activeConvId ? {...c, messages: []} : c));
                  setPlanSteps([]); setPlanPhase('idle'); setReflexionPhase('idle');
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
            {loading && <ThinkingIndicator label={phaseLabel} />}
            <div ref={msgEndRef} />
          </div>
        </div>

        <ChatInput
          input={input}
          loading={loading}
          disabled={needsConfig}
          onInput={setInput}
          onSend={sendMessage}
          onInterrupt={handleInterrupt}
        />
      </div>

      <SettingsModal config={config} onChange={updateConfig} onClose={() => setSettingsOpen(false)} show={settingsOpen} />
    </div>
  );
}
