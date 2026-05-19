'use client';

import React, {useEffect, useState} from 'react';
import {AdminSettingsService} from '@/lib/api';

const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AdminSettingsService.getSettings().then(res => {
      if (res.success) setSettings(res.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <p className="text-gray-500">系统设置面板</p>
    </div>
  );
};

export default AdminSettings;
