'use client';

import React, {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';
import {EmptyState, Modal, Pagination} from '@/components/admin/shared-ui';
import {apiClient} from '@/lib/api/api-client';
import {Link2, MessageSquare, Plus, Search, Trash2, Users} from 'lucide-react';

/* ─── Types ─────────────────────────────────────── */
interface ChatGroup {
  id: number;
  name: string;
  description?: string;
  avatar_url?: string;
  owner_id: number;
  owner_name?: string;
  member_count: number;
  max_members?: number;
  is_active: boolean;
  is_public: boolean;
  created_at?: string;
  updated_at?: string;
}

interface ChatGroupMember {
  id: number;
  user_id: number;
  username: string;
  avatar_url?: string;
  role: string;
  joined_at?: string;
  last_active_at?: string;
}

interface ChatGroupInvite {
  id: number;
  group_id: number;
  invite_code: string;
  created_by: number;
  max_uses?: number;
  current_uses: number;
  expires_at?: string;
  is_active: boolean;
  created_at?: string;
}

/* ─── Helper Components ────────────────────────── */
const Input: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  rows?: number;
}> = ({label, value, onChange, type, placeholder, rows}) => (
  <div className="mb-3">
    <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">{label}</label>
    {rows ? (
      <textarea rows={rows} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400 resize-none"/>
    ) : (
      <input type={type || 'text'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white placeholder-gray-400"/>
    )}
  </div>
);

const StatusBadge: React.FC<{ active: boolean }> = ({active}) => (
  <span
    className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${active ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
    {active ? '活跃' : '已停用'}
  </span>
);

/* ─── Groups Tab ────────────────────────────────── */
const GroupsTab: React.FC = () => {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ChatGroup | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [showMembers, setShowMembers] = useState<number | null>(null);
  const [showInvites, setShowInvites] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '', description: '', max_members: '500', is_public: 'true'
  });

  const {data, isLoading} = useQuery({
    queryKey: ['chat-groups', page, search],
    queryFn: () => apiClient.get('/chats/groups', {page, per_page: 15, search: search || undefined}),
  });

  const items: ChatGroup[] = data?.data?.groups || data?.data?.items || [];
  const total: number = data?.data?.total || 0;

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/chats/groups', d),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['chat-groups']});
        setShowForm(false);
      } else alert(r.error);
    },
  });

  const openCreate = () => {
    setEditing(null);
    setForm({name: '', description: '', max_members: '500', is_public: 'true'});
    setShowForm(true);
  };
  const submit = () => {
    if (!form.name.trim()) return alert('请填写群聊名称');
    const payload = {
      ...form,
      max_members: parseInt(form.max_members) || 500,
      is_public: form.is_public === 'true',
    };
    createMut.mutate(payload);
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"/>
            <input value={search} onChange={e => {
              setSearch(e.target.value);
              setPage(1);
            }}
                   placeholder="搜索群聊..."
                   className="pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm dark:text-white w-64"/>
          </div>
        </div>
        <button onClick={openCreate}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4"/> 创建群聊
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(5)].map((_, i) => <div key={i}
                                                                     className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={MessageSquare} title="暂无群聊" description="点击" 创建群聊"开始"/>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(g => (
            <div key={g.id}
                 className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                    {g.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">{g.name}</h3>
                    <p className="text-xs text-gray-500">{g.owner_name || `创建者#${g.owner_id}`}</p>
                  </div>
                </div>
                <StatusBadge active={g.is_active}/>
              </div>
              {g.description && <p className="text-xs text-gray-500 mb-3 line-clamp-2">{g.description}</p>}
              <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                <span className="flex items-center gap-1"><Users
                  className="w-3 h-3"/> {g.member_count}/{g.max_members || '∞'}</span>
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[10px] ${g.is_public ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
                  {g.is_public ? '公开' : '私密'}
                </span>
              </div>
              <div className="flex items-center justify-end gap-1 pt-2 border-t border-gray-100 dark:border-gray-800">
                <button onClick={() => setShowMembers(g.id)}
                        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="成员管理">
                  <Users className="w-3.5 h-3.5 text-gray-500"/>
                </button>
                <button onClick={() => setShowInvites(g.id)}
                        className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="邀请链接">
                  <Link2 className="w-3.5 h-3.5 text-gray-500"/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {total > 15 &&
        <div className="mt-4"><Pagination page={page} total={total} perPage={15} onPageChange={setPage}/></div>}

      {/* Create Group Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="创建群聊">
        <Input label="群聊名称 *" value={form.name} onChange={v => setForm(f => ({...f, name: v}))}
               placeholder="输入群聊名称"/>
        <Input label="描述" value={form.description} onChange={v => setForm(f => ({...f, description: v}))}
               placeholder="群聊描述" rows={3}/>
        <Input label="最大成员数" value={form.max_members} onChange={v => setForm(f => ({...f, max_members: v}))}
               type="number" placeholder="500"/>
        <div className="mb-3">
          <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">群聊类型</label>
          <select value={form.is_public} onChange={e => setForm(f => ({...f, is_public: e.target.value}))}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white">
            <option value="true">公开群聊</option>
            <option value="false">私密群聊</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">取消
          </button>
          <button onClick={submit} disabled={createMut.isPending}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {createMut.isPending ? '创建中...' : '创建'}
          </button>
        </div>
      </Modal>

      {/* Members Modal */}
      <Modal open={showMembers !== null} onClose={() => setShowMembers(null)} title="群聊成员管理">
        <GroupMembersPanel groupId={showMembers}/>
      </Modal>

      {/* Invites Modal */}
      <Modal open={showInvites !== null} onClose={() => setShowInvites(null)} title="邀请链接管理">
        <GroupInvitesPanel groupId={showInvites}/>
      </Modal>
    </>
  );
};

/* ─── Group Members Panel ───────────────────────── */
const GroupMembersPanel: React.FC<{ groupId: number | null }> = ({groupId}) => {
  const qc = useQueryClient();
  const [addUserId, setAddUserId] = useState('');

  const {data, isLoading} = useQuery({
    queryKey: ['group-members', groupId],
    queryFn: () => groupId ? apiClient.get(`/chats/groups/${groupId}/members`) : null,
    enabled: !!groupId,
  });

  const members: ChatGroupMember[] = data?.data?.members || [];

  const addMut = useMutation({
    mutationFn: (userIds: number[]) => apiClient.post(`/chats/groups/${groupId}/members`, {user_ids: userIds}),
    onSuccess: (r: any) => {
      if (r.success) {
        qc.invalidateQueries({queryKey: ['group-members', groupId]});
        setAddUserId('');
      } else alert(r.error);
    },
  });
  const removeMut = useMutation({
    mutationFn: (userId: number) => apiClient.delete(`/chats/groups/${groupId}/members/${userId}`),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['group-members', groupId]});
      else alert(r.error);
    },
  });

  if (!groupId) return null;

  return (
    <div>
      {isLoading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i}
                                                                     className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <>
          <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
            {members.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">暂无成员</p>
            ) : members.map(m => (
              <div key={m.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 flex items-center justify-center text-white text-xs font-bold">
                    {m.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{m.username}</span>
                    <span
                      className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${m.role === 'admin' ? 'bg-red-100 dark:bg-red-900/30 text-red-600' : m.role === 'moderator' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>
                      {m.role === 'admin' ? '群主' : m.role === 'moderator' ? '管理员' : '成员'}
                    </span>
                  </div>
                </div>
                {m.role !== 'admin' && (
                  <button onClick={() => removeMut.mutate(m.user_id)}
                          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="移除">
                    <Trash2 className="w-3.5 h-3.5 text-red-500"/>
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
            <h4 className="text-xs font-semibold text-gray-500 mb-2">添加成员</h4>
            <div className="flex gap-2">
              <input value={addUserId} onChange={e => setAddUserId(e.target.value)} placeholder="用户ID（多个用逗号分隔）"
                     className="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-white"/>
              <button onClick={() => {
                const ids = addUserId.split(',').map(s => parseInt(s.trim())).filter(Boolean);
                if (ids.length > 0) addMut.mutate(ids);
              }} disabled={!addUserId || addMut.isPending}
                      className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                添加
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

/* ─── Group Invites Panel ───────────────────────── */
const GroupInvitesPanel: React.FC<{ groupId: number | null }> = ({groupId}) => {
  const qc = useQueryClient();

  const {data, isLoading} = useQuery({
    queryKey: ['group-invites', groupId],
    queryFn: () => groupId ? apiClient.get(`/chats/groups/${groupId}/invites`) : null,
    enabled: !!groupId,
  });

  const invites: ChatGroupInvite[] = data?.data?.invites || [];

  const createMut = useMutation({
    mutationFn: () => apiClient.post(`/chats/groups/${groupId}/create-invite`, {}),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['group-invites', groupId]});
      else alert(r.error);
    },
  });
  const revokeMut = useMutation({
    mutationFn: (code: string) => apiClient.post(`/chats/groups/${groupId}/revoke-invite`, {invite_code: code}),
    onSuccess: (r: any) => {
      if (r.success) qc.invalidateQueries({queryKey: ['group-invites', groupId]});
      else alert(r.error);
    },
  });

  if (!groupId) return null;

  return (
    <div>
      {isLoading ? (
        <div className="space-y-2">{[...Array(2)].map((_, i) => <div key={i}
                                                                     className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <>
          <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
            {invites.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">暂无邀请链接</p>
            ) : invites.map(inv => (
              <div key={inv.id}
                   className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div>
                  <div className="flex items-center gap-2">
                    <code
                      className="text-sm font-mono bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">{inv.invite_code}</code>
                    <StatusBadge active={inv.is_active}/>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    已使用 {inv.current_uses}{inv.max_uses ? `/${inv.max_uses}` : ''} 次
                    {inv.expires_at && ` · 过期时间: ${inv.expires_at.slice(0, 16)}`}
                  </div>
                </div>
                <button onClick={() => revokeMut.mutate(inv.invite_code)}
                        className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20" title="撤销">
                  <Trash2 className="w-3.5 h-3.5 text-red-500"/>
                </button>
              </div>
            ))}
          </div>
          <button onClick={() => createMut.mutate()} disabled={createMut.isPending}
                  className="w-full px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {createMut.isPending ? '生成中...' : '生成新邀请链接'}
          </button>
        </>
      )}
    </div>
  );
};

/* ─── Main Component ────────────────────────────── */
const AdminChatGroupsManagementInner: React.FC = () => {
  return (
    <AdminShell title="群聊管理">
      <div className="p-6 max-w-7xl mx-auto">
        <GroupsTab/>
      </div>
    </AdminShell>
  );
};

export default function AdminChatGroupsManagement() {
  return (
    <AuthGuard>
      <QueryProvider>
        <AdminChatGroupsManagementInner/>
      </QueryProvider>
    </AuthGuard>
  );
}
