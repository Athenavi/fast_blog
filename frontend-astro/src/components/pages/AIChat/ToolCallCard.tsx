'use client';

import React, {useState} from 'react';
import {ChevronDown} from 'lucide-react';

// ─── Tool Call Card ────────────────────────────

interface ToolCallCardProps {
  toolCall: {name: string; args: Record<string, any>};
  result?: string;
  done: boolean;
}

export default function ToolCallCard({toolCall, result, done}: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`border rounded-xl overflow-hidden transition-colors ${
      done
        ? 'border-emerald-200 dark:border-emerald-800/30 bg-emerald-50/50 dark:bg-emerald-900/5'
        : 'border-violet-200 dark:border-violet-800/30 bg-violet-50/50 dark:bg-violet-900/5'
    }`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <span className="text-base">{done ? '✅' : '⏳'}</span>
        <span className="font-mono font-semibold text-sm">{toolCall.name}</span>
        <span className={`text-[10px] ml-auto font-medium ${
          done ? 'text-emerald-500' : 'text-violet-500'
        }`}>
          {done ? '完成' : '执行中…'}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Expanded: args + result */}
      {expanded && (
        <div className="px-3 pb-2.5 space-y-2">
          {/* Parameters */}
          <div>
            <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1">参数</div>
            <pre className="text-[11px] bg-white/60 dark:bg-black/20 rounded-lg p-2.5 overflow-x-auto text-gray-600 dark:text-gray-400 font-mono leading-relaxed border border-black/5 dark:border-white/5">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>

          {/* Result (only when done) */}
          {done && result && (
            <div>
              <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1">结果</div>
              <pre className="text-[11px] bg-white/60 dark:bg-black/20 rounded-lg p-2.5 overflow-x-auto text-gray-600 dark:text-gray-400 font-mono leading-relaxed max-h-40 overflow-y-auto border border-black/5 dark:border-white/5">
                {(() => {
                  try { return JSON.stringify(JSON.parse(result), null, 2); }
                  catch { return result; }
                })()}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Inline progress indicator when not expanded and not done */}
      {!expanded && !done && (
        <div className="px-3 pb-2.5">
          <div className="h-1 bg-violet-100 dark:bg-violet-900/30 rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-gradient-to-r from-violet-400 to-violet-600 rounded-full animate-pulse" />
          </div>
        </div>
      )}
    </div>
  );
}
