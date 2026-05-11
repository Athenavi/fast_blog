/**
 * 自定义 HTML Widget
 * 允许用户插入自定义 HTML 内容
 */

'use client';

import React from 'react';
import {Card, CardContent} from '@/components/ui/card';

interface HtmlWidgetProps {
    widgetId: number;
    title?: string;
    config: {
        html_content?: string;
    };
}

const HtmlWidget: React.FC<HtmlWidgetProps> = ({title, config}) => {
    const htmlContent = config.html_content || '';

    if (!htmlContent) {
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
                {/* 
                  注意：这里使用 dangerouslySetInnerHTML，需要确保后端已经做了 XSS 过滤
                  在生产环境中，应该使用 DOMPurify 等库进行前端二次过滤
                */}
                <div 
                    className="prose prose-sm dark:prose-invert max-w-none"
                    dangerouslySetInnerHTML={{__html: htmlContent}}
                />
            </CardContent>
        </Card>
    );
};

export default HtmlWidget;
