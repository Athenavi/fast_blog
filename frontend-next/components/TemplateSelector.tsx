'use client';

import React, {useEffect, useState} from 'react';
import apiClient from '@/lib/api-client';
import {Card, CardContent} from '@/components/ui/card';
import {Check, Image as ImageIcon} from 'lucide-react';

interface Template {
    slug: string;
    name: string;
    description: string;
    thumbnail?: string;
    is_default?: boolean;
    is_theme_template?: boolean;
    theme?: string;
}

interface TemplateSelectorProps {
    value: string;
    onChange: (template: string) => void;
    themeSlug?: string;
}

/**
 * 页面模板选择器组件
 * 
 * @param value - 当前选中的模板slug
 * @param onChange - 模板变更回调
 * @param themeSlug - 主题slug,用于加载主题特定模板
 */
const TemplateSelector: React.FC<TemplateSelectorProps> = ({
                                                               value,
                                                               onChange,
                                                               themeSlug
                                                           }) => {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadTemplates();
    }, [themeSlug]);

    const loadTemplates = async () => {
        try {
            setLoading(true);
            const url = themeSlug
                ? `/api/v1/page-templates?theme_slug=${themeSlug}`
                : '/api/v1/page-templates';

            const response = await apiClient.get(url);

            if (response.success && (response.data as any)?.templates) {
                setTemplates((response.data as any).templates);
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                    <Card key={i} className="animate-pulse">
                        <CardContent className="p-4">
                            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded mb-3"/>
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"/>
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"/>
                        </CardContent>
                    </Card>
                ))}
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map((template) => {
                const isSelected = value === template.slug;

                return (
                    <Card
                        key={template.slug}
                        className={`cursor-pointer transition-all duration-200 hover:shadow-lg ${
                            isSelected
                                ? 'ring-2 ring-blue-500 border-blue-500'
                                : 'border-gray-200 dark:border-gray-700'
                        }`}
                        onClick={() => onChange(template.slug)}
                    >
                        <CardContent className="p-4">
                            {/* 缩略图 */}
                            <div className="relative h-32 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                                {template.thumbnail ? (
                                    <img
                                        src={template.thumbnail}
                                        alt={template.name}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <ImageIcon className="w-12 h-12 text-gray-400"/>
                                )}

                                {/* 选中指示器 */}
                                {isSelected && (
                                    <div className="absolute top-2 right-2 bg-blue-500 text-white rounded-full p-1">
                                        <Check className="w-4 h-4"/>
                                    </div>
                                )}

                                {/* 默认标记 */}
                                {template.is_default && (
                                    <div
                                        className="absolute top-2 left-2 bg-green-500 text-white text-xs px-2 py-1 rounded">
                                        默认
                                    </div>
                                )}
                            </div>

                            {/* 模板信息 */}
                            <div>
                                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                                    {template.name}
                                </h3>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {template.description}
                                </p>

                                {/* 主题标记 */}
                                {template.is_theme_template && template.theme && (
                                    <div className="mt-2 text-xs text-blue-600 dark:text-blue-400">
                                        来自主题: {template.theme}
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
};

export default TemplateSelector;
