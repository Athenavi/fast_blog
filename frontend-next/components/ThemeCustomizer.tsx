/**
 * 主题自定义器组件
 * 提供可视化的主题配置界面
 */

'use client';

import {useEffect, useState} from 'react';
import useTheme from '@/hooks/useTheme';

interface ThemeCustomizerProps {
    themeId?: number;
    onSave?: (settings: any) => void;
}

export default function ThemeCustomizer({themeId, onSave}: ThemeCustomizerProps) {
    const {config, isLoading, error} = useTheme();

    const [settings, setSettings] = useState({
        colors: {
            primary: '#3b82f6',
            secondary: '#64748b',
            accent: '#f59e0b',
            background: '#ffffff',
            foreground: '#1f2937',
        },
        layout: {
            sidebarPosition: 'right',
            contentWidth: 'max-w-4xl',
            showSidebar: true,
        },
        typography: {
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '16px',
            lineHeight: 1.6,
        },
        components: {
            borderRadius: '0.5rem',
            shadowStyle: 'medium',
        },
    });

    const [activeTab, setActiveTab] = useState<'colors' | 'layout' | 'typography' | 'components'>('colors');
    const [isSaving, setIsSaving] = useState(false);

    // 加载主题设置
    useEffect(() => {
        if (config?.config) {
            setSettings(prev => ({
                colors: {
                    ...prev.colors,
                    ...(config.config.colors || {}),
                },
                layout: {
                    ...prev.layout,
                    ...(config.config.layout || {}),
                },
                typography: {
                    ...prev.typography,
                    ...(config.config.typography || {}),
                },
                components: {
                    ...prev.components,
                    ...(config.config.components || {}),
                },
            }));
        }
    }, [config]);

    // 更新颜色
    const updateColor = (key: string, value: string) => {
        setSettings(prev => ({
            ...prev,
            colors: {
                ...prev.colors,
                [key]: value,
            },
        }));
    };

    // 更新布局
    const updateLayout = (key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            layout: {
                ...prev.layout,
                [key]: value,
            },
        }));
    };

    // 更新排版
    const updateTypography = (key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            typography: {
                ...prev.typography,
                [key]: value,
            },
        }));
    };

    // 更新组件
    const updateComponent = (key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            components: {
                ...prev.components,
                [key]: value,
            },
        }));
    };

    // 保存设置
    const handleSave = async () => {
        if (!themeId) return;

        setIsSaving(true);
        try {
            const response = await fetch(`/api/v1/themes/${themeId}/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({settings}),
            });

            const result = await response.json();

            if (result.success) {
                alert('主题设置已保存');
                onSave?.(settings);
            } else {
                alert(`保存失败: ${result.error}`);
            }
        } catch (error) {
            console.error('保存失败:', error);
            alert('保存失败');
        } finally {
            setIsSaving(false);
        }
    };

    // 重置为默认值
    const handleReset = () => {
        if (confirm('确定要重置为默认设置吗?')) {
            setSettings({
                colors: {
                    primary: '#3b82f6',
                    secondary: '#64748b',
                    accent: '#f59e0b',
                    background: '#ffffff',
                    foreground: '#1f2937',
                },
                layout: {
                    sidebarPosition: 'right',
                    contentWidth: 'max-w-4xl',
                    showSidebar: true,
                },
                typography: {
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: '16px',
                    lineHeight: 1.6,
                },
                components: {
                    borderRadius: '0.5rem',
                    shadowStyle: 'medium',
                },
            });
        }
    };

    if (isLoading) {
        return <div className="p-8 text-center">加载中...</div>;
    }

    if (error) {
        return <div className="p-8 text-center text-red-500">错误: {error}</div>;
    }

    return (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            {/* 头部 */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 px-6 py-4">
                <h2 className="text-2xl font-bold text-white">主题自定义器</h2>
                <p className="text-blue-100 mt-1">个性化您的网站外观</p>
            </div>

            {/* 标签页 */}
            <div className="border-b">
                <nav className="flex space-x-4 px-6" aria-label="Tabs">
                    {[
                        {id: 'colors', label: '颜色'},
                        {id: 'layout', label: '布局'},
                        {id: 'typography', label: '排版'},
                        {id: 'components', label: '组件'},
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                                activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* 内容区 */}
            <div className="p-6">
                {/* 颜色设置 */}
                {activeTab === 'colors' && (
                    <div className="space-y-6">
                        <h3 className="text-lg font-semibold mb-4">配色方案</h3>

                        <div className="grid grid-cols-2 gap-4">
                            {Object.entries(settings.colors).map(([key, value]) => (
                                <div key={key}>
                                    <label className="block text-sm font-medium text-gray-700 mb-2 capitalize">
                                        {key}
                                    </label>
                                    <div className="flex items-center space-x-2">
                                        <input
                                            type="color"
                                            value={value}
                                            onChange={(e) => updateColor(key, e.target.value)}
                                            className="w-12 h-12 rounded cursor-pointer border border-gray-300"
                                        />
                                        <input
                                            type="text"
                                            value={value}
                                            onChange={(e) => updateColor(key, e.target.value)}
                                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 布局设置 */}
                {activeTab === 'layout' && (
                    <div className="space-y-6">
                        <h3 className="text-lg font-semibold mb-4">页面布局</h3>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                侧边栏位置
                            </label>
                            <select
                                value={settings.layout.sidebarPosition}
                                onChange={(e) => updateLayout('sidebarPosition', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="left">左侧</option>
                                <option value="right">右侧</option>
                                <option value="none">隐藏</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                内容宽度
                            </label>
                            <select
                                value={settings.layout.contentWidth}
                                onChange={(e) => updateLayout('contentWidth', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="max-w-3xl">窄 (768px)</option>
                                <option value="max-w-4xl">中 (896px)</option>
                                <option value="max-w-5xl">宽 (1024px)</option>
                                <option value="max-w-7xl">超宽 (1280px)</option>
                            </select>
                        </div>

                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                checked={settings.layout.showSidebar}
                                onChange={(e) => updateLayout('showSidebar', e.target.checked)}
                                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <label className="ml-2 text-sm text-gray-700">
                                显示侧边栏
                            </label>
                        </div>
                    </div>
                )}

                {/* 排版设置 */}
                {activeTab === 'typography' && (
                    <div className="space-y-6">
                        <h3 className="text-lg font-semibold mb-4">字体设置</h3>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                字体系列
                            </label>
                            <input
                                type="text"
                                value={settings.typography.fontFamily}
                                onChange={(e) => updateTypography('fontFamily', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                                placeholder="例如: Inter, system-ui, sans-serif"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                基础字号
                            </label>
                            <select
                                value={settings.typography.fontSize}
                                onChange={(e) => updateTypography('fontSize', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="14px">小 (14px)</option>
                                <option value="16px">中 (16px)</option>
                                <option value="18px">大 (18px)</option>
                                <option value="20px">超大 (20px)</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                行高: {settings.typography.lineHeight}
                            </label>
                            <input
                                type="range"
                                min="1.2"
                                max="2.0"
                                step="0.1"
                                value={settings.typography.lineHeight}
                                onChange={(e) => updateTypography('lineHeight', parseFloat(e.target.value))}
                                className="w-full"
                            />
                        </div>
                    </div>
                )}

                {/* 组件设置 */}
                {activeTab === 'components' && (
                    <div className="space-y-6">
                        <h3 className="text-lg font-semibold mb-4">组件样式</h3>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                圆角大小
                            </label>
                            <select
                                value={settings.components.borderRadius}
                                onChange={(e) => updateComponent('borderRadius', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="0">无圆角</option>
                                <option value="0.25rem">小 (4px)</option>
                                <option value="0.5rem">中 (8px)</option>
                                <option value="1rem">大 (16px)</option>
                                <option value="9999px">完全圆角</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                阴影样式
                            </label>
                            <select
                                value={settings.components.shadowStyle}
                                onChange={(e) => updateComponent('shadowStyle', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="none">无阴影</option>
                                <option value="small">小阴影</option>
                                <option value="medium">中阴影</option>
                                <option value="large">大阴影</option>
                            </select>
                        </div>
                    </div>
                )}
            </div>

            {/* 底部操作栏 */}
            <div className="border-t px-6 py-4 bg-gray-50 flex justify-between items-center">
                <button
                    onClick={handleReset}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    重置默认
                </button>

                <div className="space-x-3">
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        预览
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSaving ? '保存中...' : '保存设置'}
                    </button>
                </div>
            </div>
        </div>
    );
}
