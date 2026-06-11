'use client';

import React, {useState} from 'react';
import {X, Eye, EyeOff, Check, Sparkles} from 'lucide-react';
import type {LLMConfig} from './types';
import {PRESETS} from './types';

// ─── Settings Modal ─────────────────────────────

interface SettingsModalProps {
  config: LLMConfig;
  onChange: (p: Partial<LLMConfig>) => void;
  onClose: () => void;
  show: boolean;
}

export default function SettingsModal({config, onChange, onClose, show}: SettingsModalProps) {
  const [showKey, setShowKey] = useState(false);
  const [testOk, setTestOk] = useState(false);

  if (!show) return null;

  const applyPreset = (p: typeof PRESETS[number]) => {
    onChange({endpoint: p.endpoint, apiKey: p.apiKey, model: p.model});
    setTestOk(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity" />

      {/* Modal */}
      <div
        className="relative w-full sm:max-w-lg bg-white dark:bg-gray-900 sm:rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 max-h-[90vh] sm:max-h-[85vh] flex flex-col transition-all"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-sm">
              <Sparkles className="w-4.5 h-4.5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 dark:text-white">AI 设置</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">配置 LLM 连接与系统提示</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

          {/* Presets */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2.5">快速配置</label>
            <div className="grid grid-cols-3 gap-2">
              {PRESETS.map(p => (
                <button key={p.label} onClick={() => applyPreset(p)}
                  className={`px-3 py-2.5 rounded-xl text-xs font-medium transition-all border ${
                    config.endpoint === p.endpoint && config.model === p.model && !config.apiKey
                      ? 'border-violet-300 dark:border-violet-700 bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300 shadow-sm'
                      : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-violet-200 dark:hover:border-violet-700 hover:bg-violet-50/50 dark:hover:bg-violet-900/10'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Endpoint */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">API 端点</label>
            <input
              value={config.endpoint} onChange={e => { onChange({endpoint: e.target.value}); setTestOk(false); }}
              placeholder="https://api.openai.com/v1"
              className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-400 transition-all"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={config.apiKey} onChange={e => { onChange({apiKey: e.target.value}); setTestOk(false); }}
                placeholder="sk-..."
                className="w-full px-3.5 py-2.5 pr-10 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-400 transition-all font-mono"
              />
              <button onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Model */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">模型</label>
            <input
              value={config.model} onChange={e => { onChange({model: e.target.value}); setTestOk(false); }}
              placeholder="gpt-4o"
              className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-400 transition-all"
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">系统提示词</label>
            <textarea
              value={config.systemPrompt} onChange={e => onChange({systemPrompt: e.target.value})}
              rows={6}
              className="w-full px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-400 transition-all font-mono leading-relaxed resize-y"
            />
          </div>

          {/* Config confirmation */}
          {config.endpoint && config.model && (
            <button
              onClick={() => setTestOk(!testOk)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-violet-600 dark:hover:text-violet-400 transition-all"
            >
              {testOk ? (
                <><Check className="w-4 h-4 text-emerald-500" /><span className="text-emerald-600 dark:text-emerald-400">配置已确认</span></>
              ) : (
                <><Sparkles className="w-4 h-4" /><span>确认配置</span></>
              )}
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 flex-shrink-0">
          <span className="text-[10px] text-gray-400 dark:text-gray-500">配置仅保存在浏览器本地</span>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gradient-to-br from-violet-500 to-purple-600 text-white text-sm font-medium rounded-xl hover:from-violet-600 hover:to-purple-700 transition-all shadow-sm"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
