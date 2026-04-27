/**
 * 分类目录 Widget
 * 显示文章分类列表
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {FolderOpen} from 'lucide-react';

interface CategoryItem {
    id: number;
    name: string;
    slug: string;
    count?: number;
}

interface CategoriesWidgetProps {
    widgetId: number;
    title: string;
    config: {
        show_count?: boolean;
        display_type?: 'list' | 'hierarchy';
    };
}

const CategoriesWidget: React.FC<CategoriesWidgetProps> = ({title, config}) => {
    const [categories, setCategories] = useState<CategoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadCategories();
    }, []);

    const loadCategories = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/categories?show_count=${config.show_count !== false}&display_type=${config.display_type || 'list'}`
            );

            if (response.success && response.data) {
                setCategories((response.data as any).categories || []);
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="p-4">
                    <div className="animate-pulse space-y-2">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="h-5 bg-gray-200 dark:bg-gray-700 rounded"/>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!categories.length) {
        return null;
    }

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <FolderOpen className="w-5 h-5 text-blue-500"/>
                        {title}
                    </CardTitle>
                </CardHeader>
            )}
            <CardContent>
                <div className="space-y-1">
                    {categories.map((category) => (
                        <Link
                            key={category.id}
                            href={`/articles?category=${category.slug}`}
                            className="flex items-center justify-between px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                        >
                            <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-600">
                                {category.name}
                            </span>
                            {config.show_count !== false && category.count !== undefined && (
                                <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                                    {category.count}
                                </span>
                            )}
                        </Link>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

export default CategoriesWidget;
