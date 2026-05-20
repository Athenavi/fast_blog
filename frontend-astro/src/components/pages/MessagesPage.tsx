'use client';

import React, {useEffect, useRef, useState} from 'react';
import {apiClient} from '@/lib/api';
import {AuthGuard} from '@/components/AuthGuard';
import {Send, MessageCircle, Search, ChevronLeft} from 'lucide-react';

interface Conv {id:number;username:string;avatar?:string;last_message?:string;unread:number;updated_at:string;}
interface Msg {id:number;sender_id:number;content:string;created_at:string;}

export default function MessagesPage() {
  const [convs, setConvs] = useState<Conv[]>([]);
  const [active, setActive] = useState<number|null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient.get('/messages/private/conversations').then(r => {
      if (r.success && r.data) setConvs(Array.isArray(r.data) ? r.data : []);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!active) return;
    apiClient.get(`/messages/private/conversation/${active}`).then(r => {
      if (r.success && r.data) setMsgs(Array.isArray(r.data) ? r.data : (r.data as any).messages||[]);
    });
  }, [active]);

  useEffect(() => { bottomRef.current?.scrollIntoView(); }, [msgs]);

  const send = async () => {
    if (!text.trim() || !active) return;
    const r = await apiClient.post('/messages/private/send', {receiver_id: active, content: text});
    if (r.success) { setMsgs(p => [...p, {id:Date.now(), sender_id:0, content: text, created_at: new Date().toISOString()}]); setText(''); }
  };

  return (
    <div className="h-screen bg-white dark:bg-gray-950 flex pt-14">
      {/* Sidebar */}
      <aside className={`w-72 lg:w-80 border-r border-gray-200 dark:border-gray-800 flex flex-col ${active ? 'hidden lg:flex' : 'flex-1 lg:flex-initial'}`}>
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <h1 className="font-bold text-gray-900 dark:text-white">消息</h1>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 space-y-3">{[1,2,3].map(i=><div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>)}</div>
          ) : !convs.length ? (
            <div className="p-8 text-center text-gray-400 text-sm"><MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50"/><p>暂无对话</p></div>
          ) : convs.map(c => (
            <button key={c.id} onClick={()=>setActive(c.id)} className={`w-full p-4 text-left border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${active===c.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm shrink-0">{c.username?.charAt(0)||'?'}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between"><span className="font-medium text-sm text-gray-900 dark:text-white">{c.username}</span><span className="text-xs text-gray-400">{c.updated_at ? new Date(c.updated_at).toLocaleDateString('zh-CN') : ''}</span></div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{c.last_message||''}</p>
                </div>
                {c.unread > 0 && <span className="px-1.5 py-0.5 bg-blue-600 text-white text-xs rounded-full min-w-[18px] text-center">{c.unread}</span>}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <main className={`flex-1 flex flex-col ${!active ? 'hidden lg:flex items-center justify-center text-gray-400' : ''}`}>
        {!active ? (
          <p className="text-sm">选择一个对话开始聊天</p>
        ) : (
          <>
            <div className="h-14 flex items-center gap-3 px-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <button onClick={()=>setActive(null)} className="lg:hidden p-1 -ml-1"><ChevronLeft className="w-5 h-5"/></button>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">{convs.find(c=>c.id===active)?.username?.charAt(0)||'?'}</div>
              <span className="font-medium text-sm text-gray-900 dark:text-white">{convs.find(c=>c.id===active)?.username||''}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {msgs.map(m => (
                <div key={m.id} className={`flex ${m.sender_id === 0 ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${m.sender_id === 0 ? 'bg-blue-600 text-white rounded-br-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-sm'}`}>
                    {m.content}
                    <p className={`text-xs mt-0.5 ${m.sender_id === 0 ? 'text-blue-200' : 'text-gray-400'}`}>{m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) : ''}</p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef}/>
            </div>
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shrink-0">
              <div className="flex gap-3">
                <input type="text" value={text} onChange={e=>setText(e.target.value)} placeholder="输入消息..." className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}/>
                <button onClick={send} disabled={!text.trim()} className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl disabled:opacity-50 transition-colors"><Send className="w-4 h-4"/></button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
