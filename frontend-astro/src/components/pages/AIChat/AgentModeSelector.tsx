'use client';

import React from 'react';
import {Brain, ClipboardList, TestTube} from 'lucide-react';
import type {AgentMode} from './types';
import {AGENT_MODES} from './types';

// ─── Agent Mode Selector ───────────────────────

interface AgentModeSelectorProps {
  mode: AgentMode;
  onChange: (mode: AgentMode) => void;
}

const modeIcons: Record<AgentMode, React.ElementType> = {
  'react': Brain,
  'plan-execute': ClipboardList,
  'reflexion': TestTube,
};

export default function AgentModeSelector({mode, onChange}: AgentModeSelectorProps) {
  return (
    <div className="flex items-center gap-1 bg-gray-50 dark:bg-gray-800/50 rounded-xl p-0.5 border border-gray-100 dark:border-gray-700/50">
      {AGENT_MODES.map(m => {
        const Icon = modeIcons[m.id];
        const isActive = mode === m.id;
        return (
          <button
            key={m.id}
            onClick={() => onChange(m.id)}
            title={`${m.label} — ${m.desc}`}
            className={`
              flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200
              ${isActive
                ? 'bg-white dark:bg-gray-700 text-violet-700 dark:text-violet-300 shadow-sm border border-violet-200 dark:border-violet-700'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50'
              }
            `}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}
