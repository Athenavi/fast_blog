/**
 * Table of Contents Component
 * 文章目录组件
 */
'use client';

import React, {useState, useEffect} from 'react';
import {useTheme} from '@/hooks/useTheme';

interface Heading {
    id: string;
    text: string;
    level: number;
}

interface TableOfContentsProps {
    headings?: Heading[];
}

const TableOfContents: React.FC<TableOfContentsProps> = ({headings = []}) => {
    const {config} = useTheme();
    const themeConfig = config?.config || {};
    const colors = themeConfig?.colors || {};
    const features = themeConfig?.features || {};

    const [isVisible, setIsVisible] = useState(false);

    // 检查是否启用了目录功能
    useEffect(() => {
        setIsVisible(features.showTableOfContents ?? false);
    }, [features]);

    if (!isVisible || headings.length === 0) {
        return null;
    }

    return (
        <div
            className="toc-container p-4 rounded-lg mb-6 transition-colors duration-300 sticky top-4"
            style={{
                backgroundColor: colors.muted || '#f3f4f6',
                borderColor: colors.border || '#e5e7eb',
                color: colors.foreground || '#1f2937',
            }}
        >
            <h3
                className="font-bold text-lg mb-3"
                style={{color: colors.primary || '#3b82f6'}}
            >
                目录
            </h3>
            <ul className="space-y-2">
                {headings.map((heading, index) => (
                    <li
                        key={index}
                        className={`
              ${heading.level === 2 ? 'ml-0' : ''}
              ${heading.level === 3 ? 'ml-4' : ''}
              ${heading.level === 4 ? 'ml-8' : ''}
            `}
                    >
                        <a
                            href={`#${heading.id}`}
                            className="block py-1 hover:opacity-80 transition-opacity"
                            style={{color: colors.secondary || '#64748b'}}
                        >
                            {heading.text}
                        </a>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default TableOfContents;
