'use client';

import React, {memo} from 'react';
import {MediaFile} from '@/lib/api';

interface MediaGridProps {
  mediaFiles: MediaFile[];
  loading: boolean;
  onPreview: (media: MediaFile) => void;
  onDelete: (media: MediaFile) => void;
  totalItems: number;
}

const MediaGrid: React.FC<MediaGridProps> = memo(({
  mediaFiles,
  loading,
  onPreview,
  onDelete,
  totalItems
}) => {
  const formatFileSize = (size?: number) => {
    if (!size) return '0 KB';
    const units = ['B', 'KB', 'MB', 'GB'];
    let unitIndex = 0;
    let fileSize = size;
    while (fileSize >= 1024 && unitIndex < units.length - 1) {
      fileSize /= 1024;
      unitIndex++;
    }
    return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
  };

  const getFileIconClass = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return 'fas fa-file-image text-blue-500';
    if (mimeType.startsWith('video/')) return 'fas fa-file-video text-purple-500';
    if (mimeType.startsWith('audio/')) return 'fas fa-file-audio text-green-500';
    if (mimeType === 'application/pdf') return 'fas fa-file-pdf text-red-500';
    if (mimeType.includes('word')) return 'fas fa-file-word text-blue-600';
    if (mimeType.includes('excel')) return 'fas fa-file-excel text-green-600';
    if (mimeType.includes('powerpoint')) return 'fas fa-file-powerpoint text-orange-500';
    if (mimeType.startsWith('text/')) return 'fas fa-file-alt text-gray-500';
    if (mimeType.includes('zip') || mimeType.includes('rar')) return 'fas fa-file-archive text-yellow-500';
    return 'fas fa-file text-gray-400';
  };

  const downloadFile = (hash: string) => {
    window.open(`/api/v1/media/${hash}`, '_blank');
  };

  if (loading) {
    return (
      <div className="p-12 text-center">
        <i className="fas fa-spinner fa-spin text-3xl text-blue-500 mb-4"></i>
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  if (mediaFiles.length === 0) {
    return (
      <div className="p-12 text-center">
        <div className="text-gray-400 mb-4">
          <i className="fas fa-file-archive text-5xl"></i>
        </div>
        <p className="text-gray-500">暂无媒体文件</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {mediaFiles.map((media) => (
          <div
            key={media.id}
            className="border border-gray-200 rounded-lg overflow-hidden group hover:shadow-md transition-shadow"
          >
            <div
              className="h-32 flex items-center justify-center bg-gray-100 cursor-pointer hover:bg-gray-200 transition-colors"
              onClick={() => onPreview(media)}
            >
              {media.mime_type.startsWith('image/') || media.mime_type.startsWith('video/') ? (
                <img
                  src={`/api/v1/thumbnail/?data=${media.hash}`}
                  alt={media.original_filename}
                  className="w-16 h-16 object-cover rounded"
                  loading="lazy"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.onerror = null;
                    target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+';
                  }}
                />
              ) : (
                <div className="text-center">
                  <i
                    className={getFileIconClass(media.mime_type)}
                    style={{ fontSize: '1.5rem' }}
                  ></i>
                </div>
              )}
            </div>

            <div className="p-3">
              <div className="flex justify-between items-start mb-2">
                <h3
                  title={media.original_filename}
                  className="text-xs font-medium text-gray-900 truncate max-w-[100px]"
                >
                  {media.original_filename}
                </h3>
                <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className="text-blue-500 hover:text-blue-700"
                    title="下载"
                    onClick={(e) => {
                      e.stopPropagation();
                      downloadFile(media.hash);
                    }}
                  >
                    <i className="fas fa-download text-xs"></i>
                  </button>
                  <button
                    className="text-red-500 hover:text-red-700"
                    title="删除"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(media);
                    }}
                  >
                    <i className="fas fa-trash text-xs"></i>
                  </button>
                </div>
              </div>

              <div className="text-xs text-gray-500 mb-1">
                <span>{formatFileSize(media.file_size)}</span>
              </div>

              <div className="text-xs text-gray-500">
                <span>{new Date(media.created_at || '').toLocaleDateString('zh-CN')}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

MediaGrid.displayName = 'MediaGrid';

export default MediaGrid;