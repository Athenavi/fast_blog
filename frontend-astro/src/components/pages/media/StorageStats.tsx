import React from 'react';

import {ImageIcon, Video, Upload} from 'lucide-react';

export const StorageStats: React.FC<{ stats: any; loading: boolean }> = ({stats, loading}) => {
  const items = [
    {label: '图片', count: stats.image_count || 0, color: 'from-blue-500 to-cyan-500', icon: ImageIcon},
    {label: '视频', count: stats.video_count || 0, color: 'from-purple-500 to-pink-500', icon: Video},
    {label: '已用空间', count: stats.storage_used || '0 MB', color: 'from-green-500 to-emerald-500', icon: Upload},
  ];
  return (<div className="space-y-3">
    <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">存储</h3>
    {items.map(item => {const Icon = item.icon; return (
      <div key={item.label} className={`p-4 rounded-xl bg-gradient-to-br ${item.color} text-white`}>
        <div className="flex items-center gap-2 text-sm opacity-80"><Icon className="w-4 h-4"/>{item.label}</div>
        <p className="text-xl font-bold mt-1">{loading ? '...' : item.count}</p>
      </div>
    );})}
    {!loading && stats.storage_percentage !== undefined && (<div>
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
        <span>存储</span><span>{stats.storage_percentage}%</span></div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2"><div className="bg-blue-600 h-2 rounded-full" style={{width: `${stats.storage_percentage}%`}}/></div></div>)}
  </div>);
};
