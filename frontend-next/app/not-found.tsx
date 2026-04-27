'use client';

import {useEffect, useState} from 'react';
import {getConfig} from '@/lib/config';

export default function NotFound() {
    const [htmlContent, setHtmlContent] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>('');

    useEffect(() => {
        // 从后端API获取自定义404页面内容
        const fetchCustom404 = async () => {
            try {
                const config = getConfig();
                const apiUrl = `${config.API_BASE_URL}${config.API_PREFIX}/plugin/404-redirect/page`;

                console.log('[404 Page] Fetching custom 404 from:', apiUrl);

                const response = await fetch(apiUrl, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                console.log('[404 Page] Response status:', response.status);

                if (response.ok) {
                    const data = await response.json();
                    console.log('[404 Page] Response data:', data);

                    if (data.success && data.html) {
                        console.log('[404 Page] Setting HTML content, length:', data.html.length);
                        setHtmlContent(data.html);
                    } else {
                        console.warn('[404 Page] No HTML in response or success=false');
                        setError('No custom 404 page available');
                    }
                } else {
                    console.error('[404 Page] API request failed:', response.status);
                    setError(`API error: ${response.status}`);
                }
            } catch (error) {
                console.error('[404 Page] Failed to fetch custom 404 page:', error);
                setError('Failed to load custom 404 page');
            } finally {
                setLoading(false);
            }
        };

        fetchCustom404();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="text-6xl font-bold text-gray-400 mb-4">404</div>
                    <p className="text-gray-600">加载中...</p>
                </div>
            </div>
        );
    }

    // 如果有自定义HTML,直接渲染
    if (htmlContent) {
        console.log('[404 Page] Rendering custom HTML');
        return (
            <div
                dangerouslySetInnerHTML={{__html: htmlContent}}
            />
        );
    }

    // 显示错误信息或默认404页面
    return (
        <div
            className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
            <div className="max-w-2xl w-full text-center text-white">
                <div className="text-[120px] md:text-[180px] font-bold leading-none mb-4 animate-bounce">
                    404
                </div>
                <h1 className="text-3xl md:text-4xl font-bold mb-4">页面未找到</h1>
                <p className="text-lg md:text-xl mb-8 opacity-90">
                    抱歉,您访问的页面不存在或已被移除。
                </p>
                {error && (
                    <p className="text-sm mb-4 text-yellow-300">
                        {error}
                    </p>
                )}
                <div className="flex gap-4 justify-center">
                    <a href="/"
                       className="px-8 py-3 bg-white text-indigo-600 rounded-full font-semibold hover:bg-gray-100 transition">
                        返回首页
                    </a>
                </div>
            </div>
        </div>
    );
}
