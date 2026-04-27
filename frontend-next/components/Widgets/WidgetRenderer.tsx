/**
 * Widget渲染引擎 - 根据配置动态渲染Widget
 */

'use client';

import React from 'react';
import SearchWidget from './SearchWidget';
import RecentPostsWidget from './RecentPostsWidget';
import CategoriesWidget from './CategoriesWidget';
import TagsWidget from './TagsWidget';
import ArchivesWidget from './ArchivesWidget';
import RecentCommentsWidget from './RecentCommentsWidget';
import PopularPostsWidget from './PopularPostsWidget';
import TextWidget from './TextWidget';
import HtmlWidget from './HtmlWidget';
import SocialLinksWidget from './SocialLinksWidget';
import NewsletterWidget from './NewsletterWidget';
import AdvertisementWidget from './AdvertisementWidget';
import MenuWidget from './MenuWidget';

interface WidgetInstance {
    id: number;
    widget_type: string;
    area: string;
    title: string;
    config: Record<string, any>;
    order_index: number;
    is_active: boolean;
}

interface WidgetRendererProps {
    area: string;
    widgets?: WidgetInstance[];
}

// Widget组件映射表
const widgetComponents: Record<string, React.FC<any>> = {
    search: SearchWidget,
    recent_posts: RecentPostsWidget,
    categories: CategoriesWidget,
    tags: TagsWidget,
    archives: ArchivesWidget,
    recent_comments: RecentCommentsWidget,
    popular_posts: PopularPostsWidget,
    text: TextWidget,
    html: HtmlWidget,
    social_links: SocialLinksWidget,
    newsletter: NewsletterWidget,
    advertisement: AdvertisementWidget,
    menu: MenuWidget,
};

/**
 * Widget渲染器
 *
 * @param area - Widget区域名称
 * @param widgets - Widget实例列表
 */
const WidgetRenderer: React.FC<WidgetRendererProps> = ({area, widgets = []}) => {
    // 过滤出指定区域的活跃Widget，并按order_index排序
    const areaWidgets = widgets
        .filter(w => w.area === area && w.is_active)
        .sort((a, b) => a.order_index - b.order_index);

    if (areaWidgets.length === 0) {
        return null;
    }

    return (
        <div className="widget-area space-y-6">
            {areaWidgets.map((widget) => {
                const WidgetComponent = widgetComponents[widget.widget_type];

                if (!WidgetComponent) {
                    console.warn(`Unknown widget type: ${widget.widget_type}`);
                    return null;
                }

                return (
                    <div key={widget.id} className="widget-item">
                        <WidgetComponent
                            widgetId={widget.id}
                            title={widget.title}
                            config={widget.config}
                        />
                    </div>
                );
            })}
        </div>
    );
};

export default WidgetRenderer;
export type {WidgetInstance};
