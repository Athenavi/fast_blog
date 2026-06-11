'use client';

import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {apiClient} from '@/lib/api/base-client';
import {Layout, Plus, Trash2, Eye, X} from 'lucide-react';

interface Pattern {
  id: number;
  name: string;
  slug: string;
  description?: string;
  category?: string;
  blocks?: any[];
}

function BlockPatternsManager() {
  const qc = useQueryClient();
  const [showEditor, setShowEditor] = useState(false);
  const [newPattern, setNewPattern] = useState({name: '', description: '', category: '', blocks: '[]'});

  const {data: patterns = [], isLoading} = useQuery({
    queryKey: ['block-patterns'],
    queryFn: async () => {
      const res = await apiClient.get('/cms/block-patterns/list');
      return (res.data as any)?.patterns || res.data || [];
    },
  });

  const createMut = useMutation({
    mutationFn: () => apiClient.post('/cms/pattern', {
      name: newPattern.name,
      description: newPattern.description,
      category: newPattern.category,
      blocks: JSON.parse(newPattern.blocks || '[]'),
    }),
    onSuccess: () => { qc.invalidateQueries({queryKey: ['block-patterns']}); setShowEditor(false); setNewPattern({name: '', description: '', category: '', blocks: '[]'}); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/cms/pattern/${id}`),
    onSuccess: () => qc.invalidateQueries({queryKey: ['block-patterns']}),
  });

  return (
    <AdminShell title="Block Patterns" actions={
      <button onClick={() => setShowEditor(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors">
        <Plus className="w-4 h-4"/> New Pattern
      </button>
    }>
      {isLoading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
      ) : (patterns as any[]).length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Layout className="w-12 h-12 mx-auto mb-4 opacity-50"/>
          <p className="text-lg font-medium text-gray-500 dark:text-gray-400">No patterns yet</p>
          <p className="text-sm mt-1">Create reusable block patterns for your articles</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(patterns as any[]).map((p: any) => (
            <div key={p.id} className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-gray-300 dark:hover:border-gray-700 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-white">{p.name || p.title}</h3>
                {p.category && <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-full">{p.category}</span>}
              </div>
              {p.description && <p className="text-xs text-gray-500 mb-3 line-clamp-2">{p.description}</p>}
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{p.blocks?.length || 0} blocks</span>
                <button onClick={() => deleteMut.mutate(p.id)}
                        className="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors text-gray-400 hover:text-red-500">
                  <Trash2 className="w-3.5 h-3.5"/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowEditor(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-lg m-4 p-6 shadow-2xl border border-gray-200 dark:border-gray-800" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">New Pattern</h2>
              <button onClick={() => setShowEditor(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"><X className="w-5 h-5 text-gray-400"/></button>
            </div>
            <div className="space-y-3">
              <input type="text" placeholder="Pattern name" value={newPattern.name} onChange={e => setNewPattern({...newPattern, name: e.target.value})}
                     className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white"/>
              <input type="text" placeholder="Description" value={newPattern.description} onChange={e => setNewPattern({...newPattern, description: e.target.value})}
                     className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white"/>
              <select value={newPattern.category} onChange={e => setNewPattern({...newPattern, category: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
                <option value="">No category</option>
                <option value="header">Header</option>
                <option value="content">Content</option>
                <option value="media">Media</option>
                <option value="cta">CTA</option>
              </select>
              <textarea rows={4} placeholder='[{"type":"paragraph","content":"Hello"}]' value={newPattern.blocks} onChange={e => setNewPattern({...newPattern, blocks: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white font-mono"/>
              <button onClick={() => createMut.mutate()} disabled={!newPattern.name || createMut.isPending}
                      className="w-full px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-50 transition-colors">
                {createMut.isPending ? 'Creating...' : 'Create Pattern'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  );
}

export default function AdminBlockPatterns() {
  return <AuthGuard><QueryProvider><BlockPatternsManager/></QueryProvider></AuthGuard>;
}
