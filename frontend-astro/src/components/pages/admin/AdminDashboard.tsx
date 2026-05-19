'use client';

import React, {useEffect, useState} from 'react';
import {DashboardService} from '@/lib/api';
import type {DashboardStats, Activity} from '@/lib/api';

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      DashboardService.getStats(),
      DashboardService.getRecentActivity(10)
    ]).then(([statsRes, activityRes]) => {
      if (statsRes.success && statsRes.data) setStats(statsRes.data);
      if (activityRes.success && activityRes.data) setActivities(activityRes.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="文章" value={stats?.articles || 0} color="blue" />
        <StatCard label="用户" value={stats?.users || 0} color="green" />
        <StatCard label="评论" value={stats?.comments || 0} color="purple" />
        <StatCard label="访问" value={stats?.visitors || 0} color="orange" />
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">最近活动</h2>
        <div className="space-y-3">
          {activities.map(a => (
            <div key={a.id} className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span>{a.user_name}</span>
              <span>{a.activity_type}</span>
              <span className="text-gray-400 ml-auto">{new Date(a.created_at).toLocaleString('zh-CN')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: number; color: string }> = ({label, value, color}) => {
  const colors: Record<string, string> = {blue: 'from-blue-500 to-blue-600', green: 'from-green-500 to-green-600', purple: 'from-purple-500 to-purple-600', orange: 'from-orange-500 to-orange-600'};
  return (
    <div className={`p-6 bg-gradient-to-br ${colors[color]} rounded-xl text-white`}>
      <p className="text-sm opacity-80">{label}</p>
      <p className="text-3xl font-bold mt-1">{value.toLocaleString()}</p>
    </div>
  );
};

export default AdminDashboard;
