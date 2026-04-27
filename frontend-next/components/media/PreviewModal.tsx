'use client';

import React, {memo, useEffect, useState, useRef} from 'react';
import {MediaFile} from '@/lib/api';

interface PreviewModalProps {
    media: MediaFile | null;
    onClose: () => void;
    onEdit?: (media: MediaFile) => void;
}

const PreviewModal: React.FC<PreviewModalProps> = memo(({media, onClose, onEdit}) => {
    const [previewContent, setPreviewContent] = useState('');
    const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:8000');
    const [apiPrefix, setApiPrefix] = useState('/api/v1');
    const mediaRef = useRef(media);

    // 更新 ref
    useEffect(() => {
        mediaRef.current = media;
    }, [media]);

    // 加载 API 配置
    useEffect(() => {
        const loadConfig = async () => {
            const config = await import('@/lib/config');
            const apiConfig = config.getConfig();
            setApiBaseUrl(apiConfig.API_BASE_URL);
            setApiPrefix(apiConfig.API_PREFIX);
        };
        loadConfig();
    }, []);

    useEffect(() => {
        if (media) {
            console.log('媒体预览信息:', {
                id: media.id,
                filename: media.original_filename,
                mime_type: media.mime_type,
                file_size: media.file_size,
                url: `${apiBaseUrl}${apiPrefix}/media/${media.id}`
            });
            
            if (isTextType(media.mime_type)) {
                setTimeout(() => {
                    setPreviewContent('这是预览内容的示例...\n您可以在此处显示文本文件的内容。');
                }, 300);
            }
        }
    }, [media, apiBaseUrl, apiPrefix]);

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
                                    src={`${apiBaseUrl}${apiPrefix}/media/${media.id}`}
                                    controls
                                    className="max-w-full max-h-96"
                                    onLoadedMetadata={() => {
                                        console.log('✅ 视频元数据加载成功:', media.original_filename);
                                    }}
                                    onError={(e) => {
                                        const target = e.target as HTMLVideoElement;
                                        target.onerror = null;
                                        // 直接使用闭包中的 media 变量（在组件渲染时捕获）
                                        console.error('❌ 视频加载失败:');
                                        console.error('  文件名:', media.original_filename);
                                        console.error('  URL:', `${apiBaseUrl}${apiPrefix}/media/${media.id}`);
                                        console.error('  MIME类型:', media.mime_type);
                                        console.error('  错误类型:', e.type);
                                        console.error('  networkState:', target.networkState, '(0=EMPTY,1=IDLE,2=LOADING,3=NO_SOURCE)');
                                        console.error('  readyState:', target.readyState, '(0=HAVE_NOTHING,1=HAVE_METADATA,2=HAVE_CURRENT_DATA,3=HAVE_FUTURE_DATA,4=HAVE_ENOUGH_DATA)');
                                        console.error('  建议: 请在浏览器新标签页中打开上述 URL 测试');
                                    }}
                                >
                                    您的浏览器不支持视频播放。
                                </video>
                            ) : media.mime_type.startsWith('audio/') ? (
                                <div className="w-full max-w-md">
                                    <div className="text-center mb-4">
                                        <i className="fas fa-music text-6xl text-blue-500 mb-2"></i>
                                        <p className="text-gray-700 font-medium">{media.original_filename}</p>
                                        <p className="text-sm text-gray-500">{formatFileSize(media.file_size)}</p>
                                    </div>
                                    <audio
                                        src={`${apiBaseUrl}${apiPrefix}/media/${media.id}`}
                                        controls
                                        preload="metadata"
                                        className="w-full"
                                        onError={(e) => {
                                            const target = e.target as HTMLAudioElement;
                                            target.onerror = null;
                                            const currentMedia = mediaRef.current;
                                            console.error('音频加载失败:', {
                                                filename: currentMedia?.original_filename || '未知',
                                                url: `${apiBaseUrl}${apiPrefix}/media/${currentMedia?.id}`,
                                                mime_type: currentMedia?.mime_type || '未知',
                                                error: e.type,
                                                status: target.networkState,
                                                readyState: target.readyState
                                            });
                                        }}
                                    >
                                        您的浏览器不支持音频播放。
                                    </audio>
                                </div>
                            ) : media.mime_type === 'application/pdf' ? (
                                <div className="w-full">
                                    <iframe
                                        src={`${apiBaseUrl}${apiPrefix}/media/${media.id}#toolbar=0&view=FitH`}
                                        className="w-full h-[600px] border rounded"
                                        title={media.original_filename}
                                        style={{ minHeight: '600px' }}
                                        onLoad={() => {
                                            const currentMedia = mediaRef.current;
                                            console.log('PDF 加载成功:', currentMedia?.original_filename);
                                        }}
                                        onError={(e) => {
                                            const currentMedia = mediaRef.current;
                                            console.error('PDF 加载失败:', {
                                                filename: currentMedia?.original_filename || '未知',
                                                url: `${apiBaseUrl}${apiPrefix}/media/${currentMedia?.id}`,
                                                mime_type: currentMedia?.mime_type || '未知',
                                                error: e.type
                                            });
                                        }}
                                    />
                                </div>
                            ) : media.mime_type.startsWith('image/') ? (
                                <img
                                    src={`${apiBaseUrl}${apiPrefix}/media/${media.id}`}
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
                            {onEdit && (media.mime_type?.startsWith('image/') || media.file_type === 'image') && (
                                <button
                                    className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors flex items-center"
                                    onClick={() => {
                                        console.log('点击编辑按钮', media);
                                        onEdit(media);
                                    }}
                                >
                                    <i className="fas fa-edit mr-2"></i>
                                    编辑
                                </button>
                            )}
                            <button
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                onClick={onClose}
                            >
                                关闭
                            </button>
                            <button
                                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
                                onClick={() => {
                                    window.open(`${apiBaseUrl}${apiPrefix}/media/${media.id}`, '_blank');
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