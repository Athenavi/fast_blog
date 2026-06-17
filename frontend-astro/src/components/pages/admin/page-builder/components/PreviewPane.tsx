/**
 * PreviewPane — 实时预览面板（右侧）
 *
 * 使用 BlockPreview 组件将 block data 实时渲染为可视化效果，
 * 支持响应式设备切换（桌面/平板/手机）。
 */
import React from 'react';
import {Monitor, Tablet, Smartphone} from 'lucide-react';
import BlockPreview from './BlockPreview';
import type {PreviewDevice} from '../types';

interface Props {
    blocks: any[];
    previewDevice: PreviewDevice;
    onChangeDevice: (device: PreviewDevice) => void;
}

const deviceWidths: Record<PreviewDevice, string> = {
    desktop: 'max-w-4xl',
    tablet: 'max-w-[768px]',
    mobile: 'max-w-[375px]',
};

export default function PreviewPane({blocks, previewDevice, onChangeDevice}: Props) {
    return (
        <div className="w-[420px] bg-gray-50 dark:bg-gray-950 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col shrink-0">
            {/* 头部 */}
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center justify-between">
                <h3 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    实时预览
                </h3>
                <div className="flex items-center gap-0.5 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
                    {([
                        {key: 'desktop' as const, icon: Monitor, label: '桌面端'},
                        {key: 'tablet' as const, icon: Tablet, label: '平板端'},
                        {key: 'mobile' as const, icon: Smartphone, label: '移动端'},
                    ]).map(({key, icon: Icon, label}) => (
                        <button key={key} onClick={() => onChangeDevice(key)}
                                className={`p-1.5 rounded-md transition ${
                                    previewDevice === key
                                        ? 'bg-white dark:bg-gray-700 text-blue-600 shadow-sm'
                                        : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                                }`}
                                title={label}>
                            <Icon className="w-3.5 h-3.5"/>
                        </button>
                    ))}
                </div>
            </div>

            {/* 预览内容 */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className={`${deviceWidths[previewDevice]} mx-auto bg-white dark:bg-gray-900 shadow-lg rounded-lg min-h-[500px] transition-all duration-200`}>
                    {blocks.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-[500px] text-gray-400 dark:text-gray-500">
                            <div className="text-5xl mb-3">👁️</div>
                            <p className="text-sm">暂无内容预览</p>
                            <p className="text-xs mt-1">添加组件后即时预览效果</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100 dark:divide-gray-800">
                            {blocks.map((block, idx) => (
                                <div key={idx} className="p-6">
                                    <BlockPreview
                                        type={block.type}
                                        data={block.data || {}}
                                        styles={block.styles || {}}
                                    />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
