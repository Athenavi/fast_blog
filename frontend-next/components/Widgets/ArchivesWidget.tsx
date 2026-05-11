/**
 * 文章归档 Widget
 * 按月或按年显示文章归档
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {Calendar} from 'lucide-react';

interface ArchiveItem {
    label: string;
    slug: string;
    count?: number;
}

interface ArchivesWidgetProps {
    widgetId: number;
    title: string;
    config: {
        archive_type?: 'monthly' | 'yearly';
        show_count?: boolean;
    };
}

const ArchivesWidget: React.FC<ArchivesWidgetProps> = ({title, config}) => {
    const [archives, setArchives] = useState<ArchiveItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadArchives();
    }, []);

    const loadArchives = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/archives?archive_type=${config.archive_type || 'monthly'}&show_count=${config.show_count !== false}`
            );

            if (response.success && response.data) {
                setArchives((response.data as any).archives || []);
            }
        } catch (error) {
            console.error('Failed to load archives:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="p-4">
                    <div className="animate-pulse space-y-2">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-5 bg-gray-200 dark:bg-gray-700 rounded"/>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!archives.length) {
        return null;
    }

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Calendar className="w-5 h-5 text-green-500"/>
                        {title}
                    </CardTitle>
                </CardHeader>
            )}
            <CardContent>
                <div className="space-y-1">
                    {archives.map((archive) => (
                        <Link
                            key={archive.slug}
                            href={`/articles?archive=${archive.slug}`}
                            className="flex items-center justify-between px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                        >
                            <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-600">
                                {archive.label}
                            </span>
                            {config.show_count !== false && archive.count !== undefined && (
                                <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                                    {archive.count}
                                </span>
                            )}
                        </Link>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default ArchivesWidget;
