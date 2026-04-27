/**
 * 菜单 Widget
 * 显示网站导航菜单
 */

'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import apiClient from '@/lib/api-client';
import {ChevronDown} from 'lucide-react';

interface MenuItem {
    id: number;
    title: string;
    url: string;
    target?: string;
    children?: MenuItem[];
}

interface MenuWidgetProps {
    widgetId: number;
    title: string;
    config: {
        menu_slug?: string;
        show_submenus?: boolean;
    };
}

const MenuWidget: React.FC<MenuWidgetProps> = ({title, config}) => {
    const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadMenu();
    }, []);

    const loadMenu = async () => {
        try {
            const response = await apiClient.get(
                `/api/v1/widgets/data/menu?slug=${config.menu_slug || 'main-menu'}`
            );

            if (response.success && response.data) {
                setMenuItems((response.data as any).items || []);
            }
        } catch (error) {
            console.error('Failed to load menu:', error);
        } finally {
            setLoading(false);
        }
    };

    const renderMenuItem = (item: MenuItem, depth: number = 0) => {
        const hasChildren = item.children && item.children.length > 0;
        const paddingLeft = depth * 12;

        return (
            <li key={item.id} className="relative">
                <Link
                    href={item.url}
                    target={item.target}
                    className={`block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
                        depth > 0 ? 'text-sm text-gray-600 dark:text-gray-400' : 'font-medium'
                    }`}
                    style={{paddingLeft: `${paddingLeft + 12}px`}}
                >
                    <div className="flex items-center justify-between">
                        <span>{item.title}</span>
                        {hasChildren && config.show_submenus !== false && (
                            <ChevronDown className="w-4 h-4" />
                        )}
                    </div>
                </Link>

                {/* 子菜单 */}
                {hasChildren && config.show_submenus !== false && (
                    <ul className="ml-4 mt-1 space-y-1">
                        {item.children!.map(child => renderMenuItem(child, depth + 1))}
                    </ul>
                )}
            </li>
        );
    };

    if (loading) {
        return (
            <Card>
                <CardContent className="py-4">
                    <div className="text-center text-gray-500">加载中...</div>
                </CardContent>
            </Card>
        );
    }

    if (menuItems.length === 0) {
        return null;
    }

    return (
        <Card>
            {title && (
                <CardHeader>
                    <CardTitle className="text-lg">{title}</CardTitle>
                </CardHeader>
            )}
            <CardContent>
                <nav className="menu-nav">
                    <ul className="space-y-1">
                        {menuItems.map(item => renderMenuItem(item))}
                    </ul>
                </nav>
            </CardContent>
        </Card>
    );
};

export default MenuWidget;
