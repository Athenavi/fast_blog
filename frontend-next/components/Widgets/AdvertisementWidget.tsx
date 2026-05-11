/**
 * 广告位 Widget
 * 支持自定义广告代码嵌入
 */

'use client';

import React from 'react';
import {Card, CardContent} from '@/components/ui/card';

interface AdvertisementWidgetProps {
    widgetId: number;
    title?: string;
    config: {
        ad_code?: string;
        position?: 'sidebar' | 'content' | 'header' | 'footer';
        label?: string;
    };
}

const AdvertisementWidget: React.FC<AdvertisementWidgetProps> = ({title, config}) => {
    const adCode = config.ad_code || '';
    const label = config.label || '广告';

    if (!adCode) {
        return null;
    }

    return (
        <Card>
            {title && (
                <div className="px-6 py-4 border-b">
                    <h3 className="text-lg font-semibold">{title}</h3>
                </div>
            )}
            <CardContent className="p-4">
                {/* 广告标识 */}
                <div className="mb-2 text-xs text-gray-500 text-center">{label}</div>
                
                {/* 
                  广告代码容器
                  注意：这里使用 dangerouslySetInnerHTML，广告代码应该来自可信来源
                */}
                <div 
                    className="advertisement-container min-h-[100px] flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded"
                    dangerouslySetInnerHTML={{__html: adCode}}
                />
                
                {/* 广告尺寸提示（开发环境） */}
                {process.env.NODE_ENV === 'development' && !adCode.includes('<script') && (
                    <div className="mt-2 text-xs text-gray-400 text-center">
                        💡 提示：请配置有效的广告代码
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default AdvertisementWidget;
