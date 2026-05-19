'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import type {UserProfile} from '@/lib/api/base-types';

const UserProfile: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get<UserProfile>('/users/me').then(res => {
      if (res.success && res.data) setProfile(res.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;
  if (!profile) return <p className="text-center text-gray-500 py-12">请先登录</p>;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-6 mb-8">
        <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-3xl font-bold">
          {profile.username.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{profile.display_name || profile.username}</h1>
          <p className="text-gray-500">{profile.email}</p>
          {profile.bio && <p className="text-gray-600 dark:text-gray-400 mt-1">{profile.bio}</p>}
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
