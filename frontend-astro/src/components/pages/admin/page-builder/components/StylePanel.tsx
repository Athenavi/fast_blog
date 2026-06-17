/**
 * StylePanel — 扩展样式编辑面板
 */
import React from 'react';

interface Props {
    styles: Record<string, any>;
    onChange: (styles: Record<string, any>) => void;
    onClose: () => void;
}

const presetGroups = [
    {label: '深色', styles: {backgroundColor: '#1e293b', color: '#ffffff'}},
    {label: '蓝色', styles: {backgroundColor: '#eff6ff', color: '#1e40af'}},
    {label: '绿色', styles: {backgroundColor: '#f0fdf4', color: '#166534'}},
    {label: '暖色', styles: {backgroundColor: '#fff7ed', color: '#9a3412'}},
    {label: '卡片', styles: {backgroundColor: '#ffffff', color: '#374151', padding: 24, borderRadius: 12,
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'}},
    {label: '无', styles: {backgroundColor: 'transparent', color: '#111827', padding: 0, margin: 0, borderRadius: 0,
            boxShadow: 'none'}},
];

const fields: { key: string; label: string; type: string; min?: number; max?: number }[] = [
    {key: 'padding', label: '内边距', type: 'number', min: 0, max: 200},
    {key: 'margin', label: '外边距', type: 'number', min: 0, max: 200},
    {key: 'borderRadius', label: '圆角', type: 'number', min: 0, max: 50},
];

export default function StylePanel({styles = {}, onChange, onClose}: Props) {
    const set = (key: string, value: any) => onChange({...styles, [key]: value});

    return (
        <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">样式</span>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">&times;</button>
            </div>

            {/* 预设 */}
            <div>
                <div className="text-[10px] text-gray-400 mb-1.5">预设样式</div>
                <div className="flex flex-wrap gap-1.5">
                    {presetGroups.map(p => (
                        <button key={p.label} onClick={() => onChange(p.styles)}
                                className="px-2 py-1 text-[10px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-400 transition">
                            {p.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* 颜色 */}
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <div className="text-[10px] text-gray-400 mb-0.5">背景色</div>
                    <input type="color" value={styles.backgroundColor || '#ffffff'}
                           onChange={e => set('backgroundColor', e.target.value)}
                           className="w-full h-7 rounded cursor-pointer"/>
                </div>
                <div>
                    <div className="text-[10px] text-gray-400 mb-0.5">文字色</div>
                    <input type="color" value={styles.color || '#000000'}
                           onChange={e => set('color', e.target.value)}
                           className="w-full h-7 rounded cursor-pointer"/>
                </div>
            </div>

            {/* 数值字段 */}
            <div className="grid grid-cols-3 gap-2">
                {fields.map(f => (
                    <div key={f.key}>
                        <div className="text-[10px] text-gray-400 mb-0.5">{f.label}</div>
                        <input type="number" value={styles[f.key] ?? (f.key === 'borderRadius' ? 8 : 0)}
                               onChange={e => set(f.key, Number(e.target.value))}
                               min={f.min} max={f.max}
                               className="w-full px-2 py-1 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-xs"/>
                    </div>
                ))}
            </div>
        </div>
    );
}
