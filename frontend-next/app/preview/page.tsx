/**
 * 主题预览页面
 * 支持多设备预览（桌面、平板、手机）
 */

'use client';

import {Suspense, useEffect, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import apiClient from '@/lib/api-client';
import {Monitor, RotateCcw, Smartphone, Tablet} from 'lucide-react';

type DeviceType = 'desktop' | 'tablet' | 'mobile';

function ThemePreviewContent() {
    const searchParams = useSearchParams();
    const themeSlug = searchParams.get('theme');

    const [device, setDevice] = useState<DeviceType>('desktop');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [previewUrl, setPreviewUrl] = useState('');

    useEffect(() => {
        if (themeSlug) {
            loadPreview();
        }
    }, [themeSlug]);

    const loadPreview = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await apiClient.get<{ preview_url: string }>(`/api/v1/themes/${themeSlug}/preview`);

            if (response.success && response.data) {
                setPreviewUrl(response.data.preview_url);
            } else {
                setError(response.error || '加载预览失败');
            }
        } catch (err: any) {
            console.error('Failed to load preview:', err);
            setError(err.message || '加载预览失败');
        } finally {
            setLoading(false);
        }
    };

    // 获取设备宽度
    const getDeviceWidth = () => {
        switch (device) {
            case 'mobile':
                return '375px';
            case 'tablet':
                return '768px';
            case 'desktop':
            default:
                return '100%';
        }
    };

    // 获取设备名称
    const getDeviceName = () => {
        switch (device) {
            case 'mobile':
                return '手机';
            case 'tablet':
                return '平板';
            case 'desktop':
            default:
                return '桌面';
        }
    };

    if (!themeSlug) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">主题预览</h1>
                    <p className="text-gray-600">未指定要预览的主题</p>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载预览中...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center max-w-md">
                    <div className="text-red-500 text-6xl mb-4">⚠️</div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">预览失败</h1>
                    <p className="text-gray-600 mb-4">{error}</p>
                    <button
                        onClick={loadPreview}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        重试
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* 顶部工具栏 */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <h1 className="text-xl font-bold text-gray-900">
                            主题预览 - {themeSlug}
                        </h1>
                    </div>

                    {/* 设备切换按钮 */}
                    <div className="flex items-center space-x-2 bg-gray-100 rounded-lg p-1">
                        <button
                            onClick={() => setDevice('desktop')}
                            className={`px-3 py-2 rounded-md flex items-center space-x-2 transition-colors ${
                                device === 'desktop'
                                    ? 'bg-white shadow-sm text-blue-600'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                            title="桌面视图"
                        >
                            <Monitor className="w-4 h-4"/>
                            <span className="text-sm">桌面</span>
                        </button>
                        <button
                            onClick={() => setDevice('tablet')}
                            className={`px-3 py-2 rounded-md flex items-center space-x-2 transition-colors ${
                                device === 'tablet'
                                    ? 'bg-white shadow-sm text-blue-600'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                            title="平板视图"
                        >
                            <Tablet className="w-4 h-4"/>
                            <span className="text-sm">平板</span>
                        </button>
                        <button
                            onClick={() => setDevice('mobile')}
                            className={`px-3 py-2 rounded-md flex items-center space-x-2 transition-colors ${
                                device === 'mobile'
                                    ? 'bg-white shadow-sm text-blue-600'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                            title="手机视图"
                        >
                            <Smartphone className="w-4 h-4"/>
                            <span className="text-sm">手机</span>
                        </button>
                    </div>

                    {/* 刷新按钮 */}
                    <button
                        onClick={loadPreview}
                        className="p-2 text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="刷新预览"
                    >
                        <RotateCcw className="w-5 h-5"/>
                    </button>
                </div>
            </div>

            {/* 预览区域 */}
            <div className="p-6 overflow-auto" style={{height: 'calc(100vh - 80px)'}}>
                <div className="mx-auto transition-all duration-300 ease-in-out"
                     style={{
                         width: getDeviceWidth(),
                         height: '100%',
                         backgroundColor: 'white',
                         borderRadius: device !== 'desktop' ? '12px' : '0',
                         boxShadow: device !== 'desktop' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                         overflow: 'hidden'
                     }}>
                    {previewUrl ? (
                        <iframe
                            src={previewUrl}
                            className="w-full h-full border-0"
                            title={`Theme Preview - ${getDeviceName()}`}
                            sandbox="allow-same-origin allow-scripts"
                        />
                    ) : (
                        <div className="flex items-center justify-center h-full">
                            <p className="text-gray-500">暂无预览内容</p>
                        </div>
                    )}
                </div>
            </div>

            {/* 底部提示 */}
            <div className="fixed bottom-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2">
                <p className="text-sm text-gray-600">
                    当前视图: <span className="font-medium text-gray-900">{getDeviceName()}</span>
                </p>
            </div>
        </div>
    );
}

export default function ThemePreviewPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载中...</p>
                </div>
            </div>
        }>
            <ThemePreviewContent/>
        </Suspense>
    );
}
