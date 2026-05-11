/**
 * 社交媒体链接 Widget
 * 显示社交平台的图标链接
 */

'use client';

import React from 'react';
import Link from 'next/link';
import {Card, CardContent} from '@/components/ui/card';
import {Facebook, Github, Globe, Instagram, Linkedin, Mail, Rss, Twitter, Youtube} from 'lucide-react';

interface SocialLink {
    platform: string;
    url: string;
    icon?: string;
}

interface SocialLinksWidgetProps {
    widgetId: number;
    title?: string;
    config: {
        links?: SocialLink[];
        style?: 'icons' | 'buttons' | 'text';
        size?: 'sm' | 'md' | 'lg';
    };
}

// 平台图标映射
const platformIcons: Record<string, React.ElementType> = {
    github: Github,
    twitter: Twitter,
    facebook: Facebook,
    instagram: Instagram,
    linkedin: Linkedin,
    youtube: Youtube,
    email: Mail,
    rss: Rss,
    website: Globe,
};

// 平台颜色映射
const platformColors: Record<string, string> = {
    github: 'hover:text-gray-900 dark:hover:text-white',
    twitter: 'hover:text-blue-400',
    facebook: 'hover:text-blue-600',
    instagram: 'hover:text-pink-600',
    linkedin: 'hover:text-blue-700',
    youtube: 'hover:text-red-600',
    email: 'hover:text-green-600',
    rss: 'hover:text-orange-600',
    website: 'hover:text-blue-500',
};

const SocialLinksWidget: React.FC<SocialLinksWidgetProps> = ({title, config}) => {
    const links = config.links || [];
    const style = config.style || 'icons';
    const size = config.size || 'md';

    if (!links.length) {
        return null;
    }

    // 尺寸映射
    const sizeClasses = {
        sm: 'w-4 h-4',
        md: 'w-5 h-5',
        lg: 'w-6 h-6',
    };

    const iconSize = sizeClasses[size];

    return (
        <Card>
            {title && (
                <div className="px-6 py-4 border-b">
                    <h3 className="text-lg font-semibold">{title}</h3>
                </div>
            )}
            <CardContent className="p-4">
                {style === 'icons' && (
                    <div className="flex flex-wrap gap-3 justify-center">
                        {links.map((link, index) => {
                            const IconComponent = platformIcons[link.platform.toLowerCase()] || Globe;
                            const colorClass = platformColors[link.platform.toLowerCase()] || 'hover:text-blue-500';
                            
                            return (
                                <Link
                                    key={index}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className={`text-gray-600 dark:text-gray-400 ${colorClass} transition-colors`}
                                    aria-label={link.platform}
                                >
                                    <IconComponent className={iconSize} />
                                </Link>
                            );
                        })}
                    </div>
                )}

                {style === 'buttons' && (
                    <div className="flex flex-col gap-2">
                        {links.map((link, index) => {
                            const IconComponent = platformIcons[link.platform.toLowerCase()] || Globe;
                            
                            return (
                                <Link
                                    key={index}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-3 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <IconComponent className={iconSize} />
                                    <span className="text-sm font-medium capitalize">{link.platform}</span>
                                </Link>
                            );
                        })}
                    </div>
                )}

                {style === 'text' && (
                    <div className="flex flex-col gap-2">
                        {links.map((link, index) => (
                            <Link
                                key={index}
                                href={link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors capitalize"
                            >
                                {link.platform}
                            </Link>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default SocialLinksWidget;
