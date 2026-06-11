'use client';

import React from 'react';
import {Star, AlertTriangle, Lightbulb, ChevronDown} from 'lucide-react';
import type {Evaluation} from './types';

// ─── ReflexionCard ─────────────────────────────

interface ReflexionCardProps {
  evaluation: Evaluation;
}

function ScoreBadge({score}: {score: number}) {
  const color = score >= 8 ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800/30'
    : score >= 5 ? 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/30'
    : 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/30';

  const stars = Math.round(score / 2);
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold ${color}`}>
      <Star className="w-3.5 h-3.5 fill-current" />
      <span>{score}/10</span>
      <span className="text-[10px] opacity-60">{'★'.repeat(stars)}{'☆'.repeat(5 - stars)}</span>
    </div>
  );
}

export default function ReflexionCard({evaluation}: ReflexionCardProps) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="border border-violet-200 dark:border-violet-800/30 rounded-2xl overflow-hidden bg-white dark:bg-gray-900 shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-b border-violet-100 dark:border-violet-800/30 hover:bg-opacity-80 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-base">🪞</span>
          <span className="text-sm font-semibold text-purple-900 dark:text-purple-200">自我评估</span>
          <ScoreBadge score={evaluation.score} />
        </div>
        <ChevronDown className={`w-4 h-4 text-purple-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 py-3 space-y-3">
          {/* Summary */}
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {evaluation.summary}
          </p>

          {/* Issues */}
          {evaluation.issues.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">问题</span>
              </div>
              <ul className="space-y-1">
                {evaluation.issues.map((issue, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <span className="text-amber-400 mt-0.5">•</span>
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions */}
          {evaluation.suggestions.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-violet-500" />
                <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">改进建议</span>
              </div>
              <ul className="space-y-1">
                {evaluation.suggestions.map((sug, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <span className="text-violet-400 mt-0.5">•</span>
                    {sug}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
