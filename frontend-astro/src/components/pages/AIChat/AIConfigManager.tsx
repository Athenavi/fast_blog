'use client';

import React, {useState, useEffect, useCallback} from 'react';
import {Plus, Pencil, Trash2, Check, X, Eye, EyeOff, Loader, AlertCircle} from 'lucide-react';
import {apiClient} from '@/lib/api/base-client';

interface AIConfig {
  id: number;
  name: string;
  api_url: string;
  model: string;
  provider: string;
  is_active: boolean;
  api_key?: string;
  sort_order: number;
  created_at: string;
  updated_at?: string;
}

const PROVIDERS = [
  {value: 'openai', label: 'OpenAI'},
  {value: 'deepseek', label: 'DeepSeek'},
  {value: 'anthropic', label: 'Anthropic'},
  {value: 'custom', label: '自定义'},
];

const MAX_CONFIGS = 10;

export default function AIConfigManager({onConfigSelect}: {onConfigSelect?: (config: AIConfig) => void}) {
  const [configs, setConfigs] = useState<AIConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showKeys, setShowKeys] = useState<Record<number, boolean>>({});

  // Form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formKey, setFormKey] = useState('');
  const [formModel, setFormModel] = useState('');
  const [formProvider, setFormProvider] = useState('openai');
  const [formBusy, setFormBusy] = useState(false);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient.get('/ai/configs');
    if (res.success && Array.isArray(res.data)) {
      setConfigs(res.data);
    } else {
      setError(res.error || '加载配置失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  const resetForm = () => {
    setFormName(''); setFormUrl(''); setFormKey(''); setFormModel('');
    setFormProvider('openai'); setEditingId(null); setShowForm(false);
  };

  const startEdit = (c: AIConfig) => {
    setEditingId(c.id); setFormName(c.name); setFormUrl(c.api_url);
    setFormModel(c.model); setFormProvider(c.provider); setFormKey('');
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!formName.trim() || !formUrl.trim() || (!editingId && !formKey.trim()) || !formModel.trim()) {
      setError('请填写所有必填字段');
      return;
    }
    setFormBusy(true);
    setError(null);

    const params = new URLSearchParams();
    params.set('name', formName.trim());
    params.set('api_url', formUrl.trim());
    params.set('model', formModel.trim());
    params.set('provider', formProvider);
    if (formKey.trim()) params.set('api_key', formKey.trim());

    const res = editingId
      ? await apiClient.put(`/ai/configs/${editingId}?${params}`)
      : await apiClient.post(`/ai/configs?${params}`);

    if (res.success) {
      resetForm();
      await loadConfigs();
    } else {
      setError(res.error || '操作失败');
    }
    setFormBusy(false);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此配置？')) return;
    const res = await apiClient.delete(`/ai/configs/${id}`);
    if (res.success) {
      await loadConfigs();
    } else {
      setError(res.error || '删除失败');
    }
  };

  const handleActivate = async (id: number) => {
    const res = await apiClient.post(`/ai/configs/${id}/activate`);
    if (res.success) {
      await loadConfigs();
      const active = configs.find(c => c.id === id);
      if (active && onConfigSelect) onConfigSelect(active);
    } else {
      setError(res.error || '激活失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center p-8"><Loader className="w-5 h-5 animate-spin text-violet-500" /></div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-gray-900 dark:text-white">AI 配置</h3>
          <p className="text-xs text-gray-400">共 {configs.length}/{MAX_CONFIGS} 条</p>
        </div>
        {configs.length < MAX_CONFIGS && !showForm && (
          <button onClick={() => { resetForm(); setShowForm(true); }}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors">
            <Plus className="w-3.5 h-3.5" /> 新增
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-xl text-xs text-red-600 dark:text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto p-0.5"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
          <input value={formName} onChange={e => setFormName(e.target.value)} placeholder="配置名称（如：GPT-4o）"
            className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50" />
          <input value={formUrl} onChange={e => setFormUrl(e.target.value)} placeholder="API 地址（如：https://api.openai.com/v1）"
            className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50" />
          <div className="relative">
            <input value={formKey} onChange={e => setFormKey(e.target.value)}
              type={showKeys[-1] ? 'text' : 'password'}
              placeholder={editingId ? '留空则不修改 API Key' : 'API Key（sk-...）'}
              className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50 pr-9" />
            <button onClick={() => setShowKeys(prev => ({...prev, [-1]: !prev[-1]}))}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600">
              {showKeys[-1] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <div className="flex gap-2">
            <input value={formModel} onChange={e => setFormModel(e.target.value)} placeholder="模型（如：gpt-4o）"
              className="flex-1 px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50" />
            <select value={formProvider} onChange={e => setFormProvider(e.target.value)}
              className="px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/50">
              {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={resetForm} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors">取消</button>
            <button onClick={handleSubmit} disabled={formBusy}
              className="flex items-center gap-1 px-4 py-1.5 text-xs font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors">
              {formBusy && <Loader className="w-3 h-3 animate-spin" />}
              {editingId ? '保存' : '创建'}
            </button>
          </div>
        </div>
      )}

      {/* Config list */}
      <div className="space-y-2">
        {configs.map(c => (
          <div key={c.id}
            className={`p-4 rounded-xl border transition-all ${
              c.is_active
                ? 'border-violet-300 dark:border-violet-700 bg-violet-50/50 dark:bg-violet-900/10'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'
            }`}>
            <div className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-gray-900 dark:text-white truncate">{c.name}</span>
                  {c.is_active && <span className="text-[10px] px-1.5 py-0.5 bg-violet-200 dark:bg-violet-800 text-violet-700 dark:text-violet-300 rounded-full font-medium">当前</span>}
                </div>
                <p className="text-xs text-gray-400 truncate mt-0.5">{c.api_url} / {c.model}</p>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {!c.is_active && (
                  <button onClick={() => handleActivate(c.id)} title="激活"
                    className="p-1.5 rounded-lg hover:bg-violet-50 dark:hover:bg-violet-900/20 text-gray-400 hover:text-violet-600 transition-colors">
                    <Check className="w-3.5 h-3.5" />
                  </button>
                )}
                <button onClick={() => startEdit(c)} title="编辑"
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors">
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => handleDelete(c.id)} title="删除"
                  className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
        {configs.length === 0 && !loading && (
          <div className="text-center py-8 text-sm text-gray-400">
            <p>暂无配置</p>
            <p className="text-xs mt-1">点击"新增"添加你的第一个 AI 配置</p>
          </div>
        )}
      </div>
    </div>
  );
}
