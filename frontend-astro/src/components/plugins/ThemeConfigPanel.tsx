'use client';

import React, {useState, useEffect} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {Palette, Save, RotateCcw} from 'lucide-react';

interface Props {
    pluginSlug: string;
    themeName: string;
    themeDescription?: string;
}

export default function ThemeConfigPanel({pluginSlug, themeName, themeDescription}: Props) {
    const toast = useToast();
    const qc = useQueryClient();
    const [settings, setSettings] = useState<any>({});

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
    }, [configData]);

    // 保存主题配置
    const saveMut = useMutation({
        mutationFn: (newSettings: any) =>
            apiClient.put(`/themes/${pluginSlug}/config`, {settings: newSettings}),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['theme-config', pluginSlug]});
            qc.invalidateQueries({queryKey: ['themes-installed']});
            toast.success('主题配置已保存！');
        },
    });

    const handleSave = () => saveMut.mutate(settings);
    const handleReset = () => {
        if (configData?.settings) setSettings({...configData.settings});
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
