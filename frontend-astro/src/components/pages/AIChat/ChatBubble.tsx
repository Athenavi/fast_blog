'use client';

import React from 'react';
import {Bot, User, Wrench, Brain, ClipboardList, TestTube} from 'lucide-react';
import type {ChatMessage} from './types';
import {parsePlan, parseEvaluation} from './types';
import ToolCallCard from './ToolCallCard';
import PlanCard from './PlanCard';
import ReflexionCard from './ReflexionCard';

// ─── Message Bubble ─────────────────────────────

export default function ChatBubble({msg}: {msg: ChatMessage}) {
  const isUser = msg.role === 'user';
  const isTool = msg.role === 'tool';
  const dt = msg.displayType;

  // ── Reasoning step (ReAct Thought) ──
  if (dt === 'reasoning') {
    return (
      <div className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-sm">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <div className="max-w-[80%]">
          <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-1">思考</div>
          <div className="text-sm leading-relaxed whitespace-pre-wrap px-4 py-2.5 bg-amber-50 dark:bg-amber-900/10 text-amber-900 dark:text-amber-100 rounded-2xl rounded-tl-md border border-amber-200 dark:border-amber-800/30 shadow-sm italic">
            {msg.content}
          </div>
        </div>
      </div>
    );
  }

  // ── Plan (Plan & Execute) ──
  if (dt === 'plan' && msg.content) {
    const plan = parsePlan(msg.content);
    if (plan) {
      return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
          <PlanCard title={plan.title || '执行计划'} steps={plan.steps} />
        </div>
      );
    }
  }

  // ── Evaluation (Reflexion) ──
  if (dt === 'evaluation' && msg.content) {
    const evalResult = parseEvaluation(msg.content);
    if (evalResult) {
      return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
          <ReflexionCard evaluation={evalResult} />
        </div>
      );
    }
  }

  // ── Tool message ──
  if (isTool) {
    try {
      const toolData = JSON.parse(msg.content);
      return (
        <div className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-sm">
            <Wrench className="w-4 h-4 text-white" />
          </div>
          <div className="max-w-[80%] flex flex-col gap-1.5">
            <ToolCallCard toolCall={{name: toolData.name, args: toolData.args}}
                          result={toolData.result} done={toolData.done !== false} />
          </div>
        </div>
      );
    } catch {
      return null;
    }
  }

  // ── Normal user / assistant message ──
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-sm ${
        isUser
          ? 'bg-gradient-to-br from-blue-500 to-blue-600'
          : 'bg-gradient-to-br from-violet-500 to-purple-600'
      }`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>

      {/* Content */}
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`text-sm leading-relaxed whitespace-pre-wrap px-4 py-2.5 ${
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl rounded-br-md shadow-sm'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-2xl rounded-tl-md border border-gray-100 dark:border-gray-700 shadow-sm'
        }`}>
          {isUser || !msg.content ? (
            msg.content
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">{msg.content}</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Thinking Indicator ─────────────────────────

export function ThinkingIndicator({label}: {label?: string}) {
  return (
    <div className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-sm">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-tl-md px-5 py-3.5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '0ms'}} />
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '150ms'}} />
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce" style={{animationDelay: '300ms'}} />
          </div>
          {label && <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">{label}</span>}
        </div>
      </div>
    </div>
  );
}
