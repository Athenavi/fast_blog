'use client';

import React from 'react';
import {Globe, Monitor, RefreshCw, Smartphone, Trash2} from 'lucide-react';

interface Props {
  sessions: any[];
  onRevokeSession: (sessionId: string) => void;
  onRevokeAllOther: () => void;
  onRefresh: () => void;
  formatDevice: (s: any) => string;
  getDeviceIcon: (s: any) => React.ReactNode;
}

const SessionsTab: React.FC<Props> = ({
  sessions, onRevokeSession, onRevokeAllOther, onRefresh, formatDevice, getDeviceIcon,
}) => {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
              <Monitor className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">已登录设备</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">共 {sessions.length} 个活跃会话</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onRefresh}
              className="p-2 text-gray-400 hover:text-blue-500 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
              title="刷新"
            >
              <RefreshCw className="w-4 h-4"/>
            </button>
            {sessions.length > 1 && (
              <button
                onClick={onRevokeAllOther}
                className="px-3 py-2 text-xs font-medium text-red-500 bg-red-50 dark:bg-red-900/20 rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              >
                注销其他设备
              </button>
            )}
          </div>
        </div>

        {sessions.length === 0 ? (
          <div className="py-12 text-center">
            <Monitor className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600"/>
            <p className="text-sm text-gray-400">暂无活跃会话</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((s: any, i: number) => {
              const isCurrent = s.is_current || s.current || false;
              const sessionId = s.session_id || s.id;
              return (
                <div
                  key={sessionId || i}
                  className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                    isCurrent
                      ? 'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10'
                      : 'border-gray-100 dark:border-gray-700 hover:border-gray-200 dark:hover:border-gray-600'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    isCurrent ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  }`}>
                    {getDeviceIcon(s)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
                      <span className="truncate">{formatDevice(s)}</span>
                      {isCurrent && (
                        <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[10px] rounded-full font-medium shrink-0">当前设备</span>
                      )}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-gray-400">
                      <span className="flex items-center gap-1"><Globe className="w-3 h-3"/> {s.ip_address || s.ip || '—'}</span>
                      <span>{s.last_active ? new Date(s.last_active).toLocaleString('zh-CN') : s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : ''}</span>
                    </div>
                  </div>
                  {!isCurrent && (
                    <button
                      onClick={() => onRevokeSession(sessionId)}
                      className="p-2 text-gray-400 hover:text-red-500 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="注销"
                    >
                      <Trash2 className="w-4 h-4"/>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionsTab;
