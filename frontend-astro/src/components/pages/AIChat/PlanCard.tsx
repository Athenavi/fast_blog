'use client';

import React from 'react';
import {CheckCircle2, Circle, Loader, AlertCircle} from 'lucide-react';
import type {PlanStep} from './types';

// ─── PlanCard ──────────────────────────────────

interface PlanCardProps {
  title?: string;
  steps: PlanStep[];
}

const statusIcon: Record<PlanStep['status'], React.ReactNode> = {
  pending: <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" />,
  in_progress: <Loader className="w-4 h-4 text-violet-500 animate-spin" />,
  completed: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
  failed: <AlertCircle className="w-4 h-4 text-red-500" />,
};

const statusBg: Record<PlanStep['status'], string> = {
  pending: 'border-gray-100 dark:border-gray-700/50',
  in_progress: 'border-violet-200 dark:border-violet-800/30 bg-violet-50/50 dark:bg-violet-900/10',
  completed: 'border-emerald-200 dark:border-emerald-800/30 bg-emerald-50/30 dark:bg-emerald-900/10',
  failed: 'border-red-200 dark:border-red-800/30 bg-red-50/30 dark:bg-red-900/10',
};

export default function PlanCard({title, steps}: PlanCardProps) {
  const doneCount = steps.filter(s => s.status === 'completed').length;

  return (
    <div className="border border-violet-200 dark:border-violet-800/30 rounded-2xl overflow-hidden bg-white dark:bg-gray-900 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border-b border-violet-100 dark:border-violet-800/30">
        <div className="flex items-center gap-2">
          <span className="text-base">📋</span>
          <span className="text-sm font-semibold text-violet-900 dark:text-violet-200">
            {title || '执行计划'}
          </span>
        </div>
        <span className="text-[10px] font-medium text-violet-600 dark:text-violet-400 bg-white/60 dark:bg-gray-800/60 px-2 py-0.5 rounded-full">
          {doneCount}/{steps.length} 完成
        </span>
      </div>

      {/* Steps */}
      <div className="px-4 py-3 space-y-2">
        {steps.map(step => (
          <div
            key={step.id}
            className={`flex items-start gap-3 px-3 py-2.5 rounded-xl border transition-all ${statusBg[step.status]}`}
          >
            <div className="mt-0.5 flex-shrink-0">
              {statusIcon[step.status]}
            </div>
            <div className="min-w-0 flex-1">
              <span className={`text-sm font-medium ${
                step.status === 'completed'
                  ? 'text-emerald-800 dark:text-emerald-300 line-through decoration-emerald-400/50'
                  : step.status === 'failed'
                    ? 'text-red-800 dark:text-red-300'
                    : 'text-gray-800 dark:text-gray-200'
              }`}>
                {step.title}
              </span>
              {step.description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{step.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
