'use client';

import {useEffect, useState} from 'react';
import {MenuService, MenuTreeItem} from '@/lib/api/menu-service';

interface UseMenuOptions {
    menuLocation?: string;
    defaultMenu?: MenuTreeItem[];
}

export const useMenu = (options: UseMenuOptions = {}) => {
    const {
        menuLocation = 'main',
        defaultMenu = [
            {
                id: 1,
                title: '首页',
                url: '/',
                target: '_self',
                order_index: 1,
                is_active: true,
                menu_id: 1,
                children: []
            },
            {
                id: 2,
                title: '分类',
                url: '/categories',
                target: '_self',
                order_index: 2,
                is_active: true,
                menu_id: 1,
                children: []
            },
            {
                id: 3,
                title: '关于',
                url: '/about',
                target: '_self',
                order_index: 3,
                is_active: true,
                menu_id: 1,
                children: []
            },
        ]
    } = options;

    const [menuItems, setMenuItems] = useState<MenuTreeItem[]>(defaultMenu);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchMenuData = async () => {
            try {
                setIsLoading(true);
                setError(null);

                let response;
                if (menuLocation === 'main') {
                    response = await MenuService.getMainMenu();
                } else {
                    // 可以根据需要扩展其他菜单位置
                    response = await MenuService.getMainMenu();
                }

                if (response.success && response.data && (response.data as any).length > 0) {
                    setMenuItems(response.data as any);
                } else {
                    // 如果没有获取到数据，使用默认菜单
                    setMenuItems(defaultMenu);
                }
            } catch (err: any) {
                console.error('Failed to fetch menu data:', err);
                setError(err.message || '加载菜单失败');
                // 错误情况下使用默认菜单
                setMenuItems(defaultMenu);
            } finally {
                setIsLoading(false);
            }
        };

        fetchMenuData();
    }, [menuLocation]);

    // 刷新菜单数据
    const refreshMenu = async () => {
        setIsLoading(true);
        try {
            const response = await MenuService.getMainMenu();
            if (response.success && response.data) {
                setMenuItems(response.data as any);
                setError(null);
            }
        } catch (err: any) {
            setError(err.message || '刷新菜单失败');
        } finally {
            setIsLoading(false);
        }
    };

    return {
        menuItems,
        isLoading,
        error,
        refreshMenu,
    };
};
