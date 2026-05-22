'use client';

import React, {useEffect, useRef, useState, useCallback} from 'react';
import {apiClient} from '@/lib/api';
import {
  Send, MessageCircle, ChevronLeft, Users, Bell, Plus, X,
  Loader, Check, Hash, Trash2,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────────
interface Conv {id:number; username:string; avatar?:string; last_message?:string; unread:number; updated_at:string;}
interface Msg {id:number; sender_id:number; content:string; created_at:string; is_me?:boolean; sender_name?:string;}
interface Group {id:number; name:string; description?:string; member_count:number; unread_count:number; last_message_at?:string; avatar_url?:string;}
interface Notification {id:number; content?:string; message?:string; title?:string; is_read:boolean; created_at:string;}

const TABS = [
  {key:'chat', label:'私信', icon: MessageCircle},
  {key:'groups', label:'群聊', icon: Users},
  {key:'notifications', label:'通知', icon: Bell},
];

// ─── Tab: Private Chat ──────────────────────────────
function ChatTab({onUnread}: {onUnread?: (n: number) => void}) {
  const [convs, setConvs] = useState<Conv[]>([]);
  const [active, setActive] = useState<number|null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient.get('/chats/messages/private/conversations').then(r => {
      if (r.success && r.data) {
        const raw = Array.isArray(r.data) ? r.data : (r.data.conversations || r.data.data || []);
        setConvs(raw);
        const total = raw.reduce((sum: number, c: Conv) => sum + (c.unread || 0), 0);
        onUnread?.(total);
      }
    }).finally(() => setLoading(false));
  }, [onUnread]);

  useEffect(() => {
    if (!active) return;
    apiClient.get(`/chats/messages/private/conversation/${active}`).then(r => {
      if (r.success && r.data) {
        setMsgs(Array.isArray(r.data) ? r.data : r.data.messages || []);
      }
    });
  }, [active]);

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:'smooth'}); }, [msgs]);

  const send = async () => {
    if (!text.trim() || !active) return;
    const r = await apiClient.post('/chats/messages/private/send', {recipient_id: active, content: text});
    if (r.success) {
      setMsgs(p => [...p, {id:Date.now(), sender_id:0, content: text, created_at: new Date().toISOString(), is_me:true}]);
      setText('');
    }
  };

  return (
    <div className="flex flex-1 min-h-0">
      {/* Sidebar */}
      <div className={`w-56 lg:w-64 border-r border-gray-200 dark:border-gray-800 flex flex-col shrink-0 ${active ? 'hidden lg:flex' : 'flex w-full lg:w-64'}`}>
        <div className="p-3 border-b border-gray-200 dark:border-gray-800">
          <h2 className="font-semibold text-sm text-gray-900 dark:text-white">私信</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-3 space-y-2">{[1,2,3].map(i=><div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
          ) : !convs.length ? (
            <div className="p-6 text-center text-gray-400 text-xs"><MessageCircle className="w-6 h-6 mx-auto mb-2 opacity-50"/><p>暂无对话</p></div>
          ) : convs.map(c => (
            <button key={c.id} onClick={()=>setActive(c.id)}
              className={`w-full p-3 text-left border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${active===c.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-xs shrink-0">{c.username?.charAt(0)||'?'}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-xs text-gray-900 dark:text-white">{c.username}</span>
                    {c.updated_at && <span className="text-[10px] text-gray-400">{new Date(c.updated_at).toLocaleDateString('zh-CN')}</span>}
                  </div>
                  <p className="text-[11px] text-gray-500 truncate mt-0.5">{c.last_message||''}</p>
                </div>
                {c.unread > 0 && <span className="px-1.5 py-0.5 bg-blue-600 text-white text-[10px] rounded-full min-w-[16px] text-center leading-none">{c.unread}</span>}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className={`flex-1 flex flex-col min-w-0 ${!active ? 'hidden lg:flex lg:items-center lg:justify-center' : ''}`}>
        {!active ? (
          <div className="text-xs text-gray-400 hidden lg:block">选择一个对话</div>
        ) : (
          <>
            <div className="h-11 flex items-center gap-2.5 px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <button onClick={()=>setActive(null)} className="lg:hidden p-1 -ml-1"><ChevronLeft className="w-4 h-4"/></button>
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-xs">{convs.find(c=>c.id===active)?.username?.charAt(0)||'?'}</div>
              <span className="font-medium text-xs text-gray-900 dark:text-white">{convs.find(c=>c.id===active)?.username||''}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
              {msgs.map(m => (
                <div key={m.id} className={`flex ${(m.is_me || m.sender_id === 0) ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-3.5 py-2 rounded-2xl text-xs ${(m.is_me || m.sender_id === 0) ? 'bg-blue-600 text-white rounded-br-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-sm'}`}>
                    {m.content}
                    <p className={`text-[10px] mt-0.5 ${(m.is_me || m.sender_id === 0) ? 'text-blue-200' : 'text-gray-400'}`}>
                      {m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) : ''}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef}/>
            </div>
            <div className="p-3 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <div className="flex gap-2">
                <input value={text} onChange={e=>setText(e.target.value)} placeholder="输入消息..."
                  className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}/>
                <button onClick={send} disabled={!text.trim()}
                  className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl disabled:opacity-50"><Send className="w-3.5 h-3.5"/></button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Tab: Groups ────────────────────────────────────
function GroupsTab() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [activeGroup, setActiveGroup] = useState<number|null>(null);
  const [groupMsgs, setGroupMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient.get('/chats/groups/').then(r => {
      if (r.success && r.data) {
        const raw = Array.isArray(r.data) ? r.data : (r.data.groups || r.data.data || []);
        setGroups(raw);
      }
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!activeGroup) return;
    apiClient.get(`/chats/groups/${activeGroup}/messages`).then(r => {
      if (r.success && r.data) {
        setGroupMsgs(Array.isArray(r.data) ? r.data : r.data.messages || []);
      }
    });
  }, [activeGroup]);

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:'smooth'}); }, [groupMsgs]);

  const sendGroup = async () => {
    if (!text.trim() || !activeGroup) return;
    const r = await apiClient.post(`/chats/private/${activeGroup}/send`, {content: text, message_type: 'text'});
    if (r.success) {
      setGroupMsgs(p => [...p, {id:Date.now(), sender_id:0, content: text, created_at: new Date().toISOString(), is_me:true}]);
      setText('');
    }
  };

  const createGroup = async () => {
    if (!createName.trim()) return;
    const r = await apiClient.post('/chats/groups/', {name: createName, description: createDesc});
    if (r.success) {
      const g = r.data?.group || r.data;
      if (g?.id) setGroups(p => [...p, {id: g.id, name: g.name, description: g.description, member_count: 1, unread_count: 0}]);
      setShowCreate(false); setCreateName(''); setCreateDesc('');
      // Refresh list
      apiClient.get('/chats/groups/').then(r2 => {
        if (r2.success && r2.data) {
          const raw = Array.isArray(r2.data) ? r2.data : (r2.data.groups || r2.data.data || []);
          setGroups(raw);
        }
      });
    }
  };

  return (
    <div className="flex flex-1 min-h-0">
      {/* Sidebar */}
      <div className={`w-56 lg:w-64 border-r border-gray-200 dark:border-gray-800 flex flex-col shrink-0 ${activeGroup ? 'hidden lg:flex' : 'flex w-full lg:w-64'}`}>
        <div className="p-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold text-sm text-gray-900 dark:text-white">群聊</h2>
          <button onClick={()=>setShowCreate(true)} className="p-1 text-gray-400 hover:text-blue-600"><Plus className="w-4 h-4"/></button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-3 space-y-2">{[1,2,3].map(i=><div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
          ) : !groups.length ? (
            <div className="p-6 text-center text-gray-400 text-xs"><Users className="w-6 h-6 mx-auto mb-2 opacity-50"/><p>暂未加入群聊</p><button onClick={()=>setShowCreate(true)} className="mt-2 text-blue-500 underline">创建群聊</button></div>
          ) : groups.map(g => (
            <button key={g.id} onClick={()=>setActiveGroup(g.id)}
              className={`w-full p-3 text-left border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${activeGroup===g.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-white font-bold text-xs">{g.name?.charAt(0)||'G'}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-xs text-gray-900 dark:text-white truncate">{g.name}</span>
                    <span className="text-[10px] text-gray-400">{g.member_count}人</span>
                  </div>
                  <p className="text-[11px] text-gray-500 truncate mt-0.5">{g.description||''}</p>
                </div>
                {g.unread_count > 0 && <span className="px-1.5 py-0.5 bg-blue-600 text-white text-[10px] rounded-full">{g.unread_count}</span>}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Group chat area */}
      <div className={`flex-1 flex flex-col min-w-0 ${!activeGroup ? 'hidden lg:flex lg:items-center lg:justify-center' : ''}`}>
        {!activeGroup ? (
          <div className="text-xs text-gray-400 hidden lg:block">选择一个群聊</div>
        ) : (
          <>
            <div className="h-11 flex items-center gap-2.5 px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <button onClick={()=>setActiveGroup(null)} className="lg:hidden p-1 -ml-1"><ChevronLeft className="w-4 h-4"/></button>
              <Hash className="w-4 h-4 text-gray-400"/>
              <span className="font-medium text-xs text-gray-900 dark:text-white">{groups.find(g=>g.id===activeGroup)?.name||''}</span>
              <span className="text-[10px] text-gray-400 ml-auto">{groups.find(g=>g.id===activeGroup)?.member_count||0} 人在线</span>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
              {groupMsgs.map(m => (
                <div key={m.id} className={`flex ${(m.is_me || m.sender_id === 0) ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-3.5 py-2 rounded-2xl text-xs ${(m.is_me || m.sender_id === 0) ? 'bg-blue-600 text-white rounded-br-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-sm'}`}>
                    {!m.is_me && m.sender_name && <p className="text-[10px] font-medium text-blue-500 mb-0.5">{m.sender_name}</p>}
                    {m.content}
                    <p className={`text-[10px] mt-0.5 ${(m.is_me || m.sender_id === 0) ? 'text-blue-200' : 'text-gray-400'}`}>
                      {m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) : ''}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef}/>
            </div>
            <div className="p-3 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <div className="flex gap-2">
                <input value={text} onChange={e=>setText(e.target.value)} placeholder="发送群消息..."
                  className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendGroup();}}}/>
                <button onClick={sendGroup} disabled={!text.trim()}
                  className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl disabled:opacity-50"><Send className="w-3.5 h-3.5"/></button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Create group modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={()=>setShowCreate(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-sm m-4" onClick={e=>e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-sm text-gray-900 dark:text-white">创建群聊</h3>
              <button onClick={()=>setShowCreate(false)} className="p-1 text-gray-400"><X className="w-4 h-4"/></button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">群名称</label>
                <input value={createName} onChange={e=>setCreateName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm dark:bg-gray-800 dark:text-white"/>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">描述（可选）</label>
                <input value={createDesc} onChange={e=>setCreateDesc(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm dark:bg-gray-800 dark:text-white"/>
              </div>
              <button onClick={createGroup} disabled={!createName.trim()}
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50">创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tab: Notifications ──────────────────────────────
function NotificationsTab() {
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await apiClient.get<any>('/notifications/messages');
    if (r.success && r.data) {
      setNotifs(Array.isArray(r.data) ? r.data : r.data.notifications || r.data.data || []);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const markRead = async (id: number) => {
    await apiClient.post(`/notifications/${id}/read`);
    setNotifs(prev => prev.map(n => n.id === id ? {...n, is_read: true} : n));
  };

  const markAllRead = async () => {
    await apiClient.post('/notifications/messages/read_all');
    setNotifs(prev => prev.map(n => ({...n, is_read: true})));
  };

  const cleanAll = async () => {
    if (!confirm('清理所有通知？')) return;
    await apiClient.delete('/notifications/messages/clean');
    setNotifs([]);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <h2 className="font-semibold text-sm text-gray-900 dark:text-white">通知</h2>
        <div className="flex gap-2">
          {notifs.some(n => !n.is_read) && (
            <button onClick={markAllRead} className="text-[10px] text-blue-600 hover:underline">全部已读</button>
          )}
          {notifs.length > 0 && (
            <button onClick={cleanAll} className="text-[10px] text-red-500 hover:underline">清理</button>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center"><div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>
        ) : !notifs.length ? (
          <div className="p-8 text-center text-gray-400"><Bell className="w-8 h-8 mx-auto mb-2 opacity-40"/><p className="text-xs">暂无通知</p></div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {notifs.map(n => (
              <div key={n.id} className={`px-4 py-3.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 ${!n.is_read ? 'bg-blue-50/50 dark:bg-blue-900/5' : ''}`}>
                <div className="flex-1 min-w-0 pr-3">
                  <p className={`text-xs ${n.is_read ? 'text-gray-500' : 'text-gray-900 dark:text-white font-medium'}`}>
                    {n.content || n.message || n.title || '-'}
                  </p>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    {n.created_at ? new Date(n.created_at).toLocaleString('zh-CN') : ''}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  {!n.is_read && (
                    <button onClick={() => markRead(n.id)} className="p-1.5 text-gray-400 hover:text-green-600" title="标为已读">
                      <Check className="w-3.5 h-3.5"/>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────
export default function MessagesPage() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="h-screen bg-white dark:bg-gray-950 flex flex-col pt-14">
      {/* Tab bar */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0 px-2">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors
                ${activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              <Icon className="w-4 h-4"/>{t.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 flex min-h-0">
        {activeTab === 'chat' && <ChatTab/>}
        {activeTab === 'groups' && <GroupsTab/>}
        {activeTab === 'notifications' && <NotificationsTab/>}
      </div>
    </div>
  );
}
