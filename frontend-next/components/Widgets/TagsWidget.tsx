/**
 * 标签云 Widget
 * 显示文章标签，支持云模式和列表模式
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {Tag} from 'lucide-react';

interface TagItem {
    name: string;
    count: number;
    font_size?: number;
    slug: string;
}

interface TagsWidgetProps {
    widgetId: number;
    title: string;
    config: {
        count?: number;
        display_type?: 'cloud' | 'list';
        show_count?: boolean;
    };
}

const TagsWidget: React.FC<TagsWidgetProps> = ({title, config}) => {
    const [tags, setTags] = useState<TagItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadTags();
    }, []);

    const loadTags = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/tags-cloud?count=${config.count || 20}&display_type=${config.display_type || 'cloud'}`
            );

            if (response.success && response.data) {
                setTags((response.data as any).tags || []);
            }
        } catch (error) {
            console.error('Failed to load tags:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="p-4">
                    <div className="animate-pulse flex flex-wrap gap-2">
                        {[...Array(8)].map((_, i) => (
                            <div key={i} className="h-6 bg-gray-200 dark:bg-gray-700 rounded" style={{width: `${Math.random() * 60 + 40}px`}}/>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!tags.length) {
        return null;
    }

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Tag className="w-5 h-5 text-purple-500"/>
                        {title}
                    </CardTitle>
                </CardHeader>
            )}
            <CardContent>
                {config.display_type === 'list' ? (
                    // 列表模式
                    <div className="space-y-2">
                        {tags.map((tag) => (
                            <Link
                                key={tag.slug}
                                href={`/articles?tag=${encodeURIComponent(tag.name)}`}
                                className="flex items-center justify-between px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                            >
                                <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-600">
                                    {tag.name}
                                </span>
                                {config.show_count !== false && (
                                    <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                                        {tag.count}
                                    </span>
                                )}
                            </Link>
                        ))}
                    </div>
                ) : (
                    // 云模式
                    <div className="flex flex-wrap gap-2">
                        {tags.map((tag) => (
                            <Link
                                key={tag.slug}
                                href={`/articles?tag=${encodeURIComponent(tag.name)}`}
                                className="inline-flex items-center px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors group"
                                style={{
                                    fontSize: `${tag.font_size || 1}em`,
                                }}
                            >
                                <span className="text-gray-700 dark:text-gray-300 group-hover:text-blue-600">
                                    {tag.name}
                                </span>
                                {config.show_count && (
                                    <span className="ml-1 text-xs text-gray-500">
                                        ({tag.count})
                                    </span>
                                )}
                            </Link>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default TagsWidget;
