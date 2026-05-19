'use client';

import React, {useEffect, useState} from 'react';
import {MediaService} from '@/lib/api';
import type {MediaFile} from '@/lib/api/base-types';

const AdminMedia: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    MediaService.getMediaFiles({page: 1}).then(res => {
      if (res.success && res.data) setFiles(res.data.media_items || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {files.map(f => (
        <div key={f.id} className="aspect-square rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          {f.mime_type?.startsWith('image/') ? (
            <img src={f.url || ''} alt={f.original_filename} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">{f.original_filename}</div>
          )}
        </div>
      ))}
    </div>
  );
};

export default AdminMedia;
