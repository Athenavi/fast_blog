'use client';

import React, {memo, useEffect, useState} from 'react';
import {MediaFile} from '@/lib/api';

interface PreviewModalProps {
    media: MediaFile | null;
    onClose: () => void;
}

const PreviewModal: React.FC<PreviewModalProps> = memo(({media, onClose}) => {
    const [previewContent, setPreviewContent] = useState('');

    useEffect(() => {
        if (media && isTextType(media.mime_type)) {
            setTimeout(() => {
                setPreviewContent('这是预览内容的示例...\n您可以在此处显示文本文件的内容。');
            }, 300);
        }
    }, [media]);

    const isTextType = (mimeType?: string) => {
        if (!mimeType) return false;
        return mimeType.startsWith('text/') ||
            mimeType === 'application/json' ||
            mimeType === 'application/javascript';
    };

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

    if (!media) return null;

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-75 overflow-y-auto h-full w-full z-50"
            onClick={onClose}
        >
            <div className="relative top-4 mx-auto p-4 w-full max-w-4xl"
                 onClick={(e) => e.stopPropagation()}>
                <div className="bg-white rounded-lg shadow-lg">
                    <div className="flex justify-between items-center px-6 py-4 border-b">
                        <h3 className="text-lg font-medium text-gray-900">{media.original_filename}</h3>
                        <button className="text-gray-400 hover:text-gray-500" onClick={onClose}>
                            <i className="fas fa-times text-xl"></i>
                        </button>
                    </div>

                    <div className="p-6">
                        <div className="flex items-center justify-center min-h-64">
                            {media.mime_type.startsWith('video/') ? (
                                <video
                                    src={`/api/v1/media/${media.id}`}
                                    controls
                                    className="max-w-full max-h-96"
                                    onError={(e) => {
                                        const target = e.target as HTMLVideoElement;
                                        target.onerror = null;
                                        // 视频加载失败时的处理
                                        console.error('视频加载失败:', media.original_filename);
                                    }}
                                >
                                    您的浏览器不支持视频播放。
                                </video>
                            ) : media.mime_type.startsWith('image/') ? (
                                <img
                                    src={`/api/v1/media/${media.id}`}
                                    alt={media.original_filename}
                                    className="max-w-full max-h-96 object-contain"
                                    onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        target.onerror = null;
                                        target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZTVlN2ViIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjNmI3MjgwIj5JbWFnZSBQbGFjZWhvbGRlcjwvdGV4dD48L3N2Zz4=';
                                    }}
                                />
                            ) : isTextType(media.mime_type) ? (
                                <div className="w-full bg-gray-50 p-4 rounded border text-left max-h-96 overflow-auto">
                                    <pre className="whitespace-pre-wrap font-mono text-sm">{previewContent}</pre>
                                </div>
                            ) : (
                                <div className="text-center">
                                    <i className="fas fa-file text-6xl text-gray-400 mb-4"></i>
                                    <p className="text-gray-500">不支持在线预览此文件类型</p>
                                    <p className="text-sm text-gray-400 mt-2">{media.mime_type}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="px-6 py-4 border-t bg-gray-50 flex justify-between items-center">
                        <div className="text-sm text-gray-500">
                            文件大小: {formatFileSize(media.file_size)} |
                            类型: {media.mime_type}
                        </div>
                        <div className="flex space-x-2">
                            <button
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                onClick={onClose}
                            >
                                关闭
                            </button>
                            <button
                                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
                                onClick={() => {
                                    window.open(`/api/v1/media/${media.id}`, '_blank');
                                    onClose();
                                }}
                            >
                                下载
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
});

PreviewModal.displayName = 'PreviewModal';

export default PreviewModal;