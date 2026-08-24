'use client';

import React, {useState, useEffect} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {Palette, Save, RotateCcw, CheckCircle, AlertCircle, Layers} from 'lucide-react';

interface Props {
    pluginSlug: string;
    themeName: string;
    themeDescription?: string;
}

// 组件槽位定义：可供主题覆盖的组件与其可用变体
const SLOT_DEFS: { key: string; label: string; options: { value: string; label: string }[] }[] = [
    {
        key: 'header',
        label: '顶部导航',
        options: [
            {value: 'floating', label: '浮动胶囊（默认）'},
            {value: 'classic', label: '经典顶栏'},
        ],
    },
    {
        key: 'articleCard',
        label: '文章卡片',
        options: [
            {value: 'default', label: '标准卡片（默认）'},
            {value: 'compact', label: '紧凑卡片'},
        ],
    },
    {
        key: 'footer',
        label: '页脚',
        options: [
            {value: 'default', label: '标准（默认）'},
            {value: 'minimal', label: '极简'},
        ],
    },
];

export default function ThemeConfigPanel({pluginSlug, themeName, themeDescription}: Props) {
    const qc = useQueryClient();
    const [settings, setSettings] = useState<any>({});
    const [componentSlots, setComponentSlots] = useState<Record<string, string>>({});
    const [notification, setNotification] = useState<{type: 'success' | 'error'; message: string} | null>(null);

    // 自动清除通知
    useEffect(() => {
        if (notification) {
            const timer = setTimeout(() => setNotification(null), 3000);
            return () => clearTimeout(timer);
        }
    }, [notification]);

    const showSuccess = (msg: string) => setNotification({type: 'success', message: msg});
    const showError = (msg: string) => setNotification({type: 'error', message: msg});

    // 读取主题配置
    const {data: configData, isLoading} = useQuery({
        queryKey: ['theme-config', pluginSlug],
        queryFn: async () => {
            const res = await apiClient.get(`/themes/${pluginSlug}/config`);
            return res.data;
        },
    });

    useEffect(() => {
        if (configData?.settings) {
            setSettings(configData.settings);
        }
        if (configData?.contract?.componentSlots) {
            setComponentSlots({...configData.contract.componentSlots});
        }
    }, [configData]);

    // 保存主题配置
    const saveMut = useMutation({
        mutationFn: (payload: {settings: any; component_slots: Record<string, string>}) =>
            apiClient.put(`/themes/${pluginSlug}/config`, payload),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['theme-config', pluginSlug]});
            qc.invalidateQueries({queryKey: ['themes-installed']});
            showSuccess('主题配置已保存！');
        },
        onError: (err: any) => {
            showError(err?.message || '保存失败');
        },
    });

    const handleSave = () => saveMut.mutate({settings, component_slots: componentSlots});
    const handleReset = () => {
        if (configData?.settings) setSettings({...configData.settings});
        if (configData?.contract?.componentSlots) setComponentSlots({...configData.contract.componentSlots});
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"/>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* 通知 */}
            {notification && (
                <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
                    notification.type === 'success'
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300'
                        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
                }`}>
                    {notification.type === 'success' ? <CheckCircle className="w-5 h-5"/> : <AlertCircle className="w-5 h-5"/>}
                    <span className="text-sm font-medium">{notification.message}</span>
                </div>
            )}

            {/* 主题信息 */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border p-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                        <Palette className="w-8 h-8 text-blue-600"/>
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{themeName}</h2>
                        {themeDescription && <p className="text-sm text-gray-500">{themeDescription}</p>}
                    </div>
                </div>
            </div>

            {/* 配置表单 */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border p-6 space-y-6">
                {configData?.settings_schema && Object.entries(configData.settings_schema).map(([groupKey, group]: [string, any]) => (
                    <div key={groupKey}>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                            {group.label || groupKey}
                        </h3>
                        <div className="space-y-4 pl-2">
                            {group.fields && Object.entries(group.fields).map(([fieldKey, field]: [string, any]) => (
                                <div key={fieldKey}>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        {field.label || fieldKey}
                                    </label>
                                    {renderField(fieldKey, field, settings, setSettings)}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* 组件槽位 */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border p-6 space-y-6">
                <div className="flex items-center gap-3">
                    <Layers className="w-5 h-5 text-blue-600"/>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">组件</h3>
                    <span className="text-xs text-gray-400">选择该主题下各组件使用的变体</span>
                </div>
                <div className="space-y-4 pl-2">
                    {SLOT_DEFS.map((slot) => (
                        <div key={slot.key}>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                {slot.label}
                            </label>
                            <select
                                value={componentSlots[slot.key] || slot.options[0]?.value || ''}
                                onChange={(e) => setComponentSlots((prev) => ({...prev, [slot.key]: e.target.value}))}
                                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                {slot.options.map((opt) => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                        </div>
                    ))}
                </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3 justify-end">
                <button
                    onClick={handleReset}
                    className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-2"
                >
                    <RotateCcw className="w-4 h-4"/>重置
                </button>
                <button
                    onClick={handleSave}
                    disabled={saveMut.isPending}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition flex items-center gap-2"
                >
                    <Save className="w-4 h-4"/>
                    {saveMut.isPending ? '保存中...' : '保存配置'}
                </button>
            </div>
        </div>
    );
}

// 渲染单个配置字段
function renderField(
    fieldKey: string,
    field: any,
    settings: any,
    setSettings: (s: any) => void,
) {
    const value = settings[fieldKey] ?? field.default;

    const update = (newVal: any) => {
        setSettings((prev: any) => ({...prev, [fieldKey]: newVal}));
    };

    switch (field.type) {
        case 'color':
            return (
                <div className="flex items-center gap-3">
                    <input type="color" value={value || '#000000'}
                           onChange={(e) => update(e.target.value)}
                           className="w-10 h-10 rounded border cursor-pointer"/>
                    <input type="text" value={value || ''}
                           onChange={(e) => update(e.target.value)}
                           className="flex-1 px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                </div>
            );
        case 'select':
            return (
                <select value={value || ''}
                        onChange={(e) => update(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {(field.options || []).map((opt: any) => (
                        <option key={opt.value} value={opt.value}>{opt.label || opt.value}</option>
                    ))}
                </select>
            );
        case 'boolean':
            return (
                <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" checked={!!value}
                           onChange={(e) => update(e.target.checked)}
                           className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"/>
                    <span className="text-sm text-gray-600 dark:text-gray-400">{field.label || fieldKey}</span>
                </label>
            );
        case 'number':
            return (
                <input type="number" value={value ?? ''}
                       onChange={(e) => update(Number(e.target.value))}
                       className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            );
        case 'textarea':
            return (
                <textarea value={value || ''}
                          onChange={(e) => update(e.target.value)} rows={3}
                          className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            );
        default:
            return (
                <input type="text" value={value || ''}
                       onChange={(e) => update(e.target.value)}
                       className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            );
    }
}
