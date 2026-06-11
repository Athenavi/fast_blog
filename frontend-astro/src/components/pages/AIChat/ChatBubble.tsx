'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Bot, User, Wrench, Brain} from 'lucide-react';
import type {ChatMessage} from './types';
import {parsePlan, parseEvaluation} from './types';
import ToolCallCard from './ToolCallCard';
import PlanCard from './PlanCard';
import ReflexionCard from './ReflexionCard';

// ─── Markdown 渲染配置 ─────────────────────────

const mdComponents = {
  // 代码块：带暗色模式自适应
  code: ({node, inline, className, children, ...props}: any) => {
    const match = /language-(\w+)/.exec(className || '');
    if (inline) {
      return (
        <code className="bg-gray-100 dark:bg-gray-700 text-pink-600 dark:text-pink-400 px-1.5 py-0.5 rounded text-[0.85em] font-mono" {...props}>
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-gray-900 dark:bg-gray-950 text-gray-100 rounded-xl p-4 overflow-x-auto text-sm leading-relaxed my-3 border border-gray-700/50">
        <code className={className} {...props}>{children}</code>
      </pre>
    );
  },
  // 链接：新标签打开
  a: ({href, children}: any) => (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className="text-blue-600 dark:text-blue-400 hover:underline">
      {children}
    </a>
  ),
  // 表格
  table: ({children}: any) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full border-collapse border border-gray-200 dark:border-gray-700 text-sm">
        {children}
      </table>
    </div>
  ),
  th: ({children}: any) => (
    <th className="border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({children}: any) => (
    <td className="border border-gray-200 dark:border-gray-700 px-3 py-2">{children}</td>
  ),
  // 引用块
  blockquote: ({children}: any) => (
    <blockquote className="border-l-4 border-violet-300 dark:border-violet-700 pl-4 my-3 text-gray-600 dark:text-gray-400 italic">
      {children}
    </blockquote>
  ),
  // 列表
  ul: ({children}: any) => (
    <ul className="list-disc pl-6 my-2 space-y-1">{children}</ul>
  ),
  ol: ({children}: any) => (
    <ol className="list-decimal pl-6 my-2 space-y-1">{children}</ol>
  ),
  li: ({children}: any) => (
    <li className="text-gray-700 dark:text-gray-300 leading-relaxed">{children}</li>
  ),
  // 标题
  h1: ({children}: any) => <h1 className="text-xl font-bold mt-6 mb-3 text-gray-900 dark:text-white">{children}</h1>,
  h2: ({children}: any) => <h2 className="text-lg font-bold mt-5 mb-2 text-gray-900 dark:text-white">{children}</h2>,
  h3: ({children}: any) => <h3 className="text-base font-semibold mt-4 mb-2 text-gray-900 dark:text-white">{children}</h3>,
  // 段落
  p: ({children}: any) => <p className="my-2 leading-relaxed text-gray-800 dark:text-gray-200 last:mb-0">{children}</p>,
  // 分隔线
  hr: () => <hr className="my-4 border-gray-200 dark:border-gray-700" />,
};

// ─── Markdown 渲染组件 ──────────────────────────

function MarkdownContent({content}: {content: string}) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={mdComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ─── 纯文本渲染（用户消息）────────────────────

function PlainContent({content}: {content?: string}) {
  return <span className="whitespace-pre-wrap break-words">{content}</span>;
}

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
          <div className="text-sm leading-relaxed px-4 py-2.5 bg-amber-50 dark:bg-amber-900/10 text-amber-900 dark:text-amber-100 rounded-2xl rounded-tl-md border border-amber-200 dark:border-amber-800/30 shadow-sm italic">
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
        <div className={`text-sm leading-relaxed px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl rounded-br-md shadow-sm'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-2xl rounded-tl-md border border-gray-100 dark:border-gray-700 shadow-sm'
        }`}>
          {isUser || !msg.content ? (
            <PlainContent content={msg.content} />
          ) : (
            <MarkdownContent content={msg.content} />
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
