// Menu service for Next.js frontend
import type {ApiResponse} from '@/lib/api/base-types';
import {MenuItem} from './admin-settings-service';
import {cachedFetch} from '@/lib/api-cache';

export interface MenuTreeItem extends MenuItem {
    children?: MenuTreeItem[];
}

export interface MenuData {
    id: number;
    name: string;
    slug: string;
    description?: string;
    items: MenuTreeItem[];
}

// 获取菜单数据的服务
export class MenuService {
    // 从首页 API 获取动态菜单数据
    static async getMenuBySlug(slug: string = 'main'): Promise<ApiResponse<MenuData>> {
        try {
            // 使用新的专用 API 端点获取指定菜单，添加缓存
            const response = await cachedFetch<any>(`/home/menu/${slug}`, undefined, 10 * 60 * 1000); // 10分钟缓存

            if (response.success && response.data) {
                const menuData = response.data as any;
                return {
                    requires_auth: false,
                    success: true,
                    data: {
                        id: 1, // 使用返回数据中的实际ID
                        name: menuData.name || slug,
                        slug: menuData.slug || slug,
                        description: menuData.description,
                        items: menuData.items || []
                    }
                };
            }

            return {
                requires_auth: false,
                success: false,
                error: 'Menu not found',
                data: undefined
            };
        } catch (error) {
            return {
                requires_auth: false,
                success: false,
                error: error instanceof Error ? error.message : 'Failed to fetch menu data',
                data: undefined
            };
        }
    }

    // 获取所有菜单数据
    static async getAllMenus(): Promise<ApiResponse<any>> {
        try {
            const response = await cachedFetch<ApiResponse<any>>('/home/menus', undefined, 10 * 60 * 1000); // 10分钟缓存
            return response;
        } catch (error) {
            return {
                requires_auth: false,
                success: false,
                error: error instanceof Error ? error.message : 'Failed to fetch menu data',
                data: undefined
            };
        }
    }

    // 专门获取菜单结构的方法
    static async getMainMenu(): Promise<ApiResponse<MenuTreeItem[]>> {
        try {
            // 优先获取名为'main'的菜单，如果没有则获取第一个菜单
            let response = await cachedFetch<ApiResponse<any>>('/home/menus', undefined, 10 * 60 * 1000); // 10分钟缓存

            if (response.success && response.data && (response.data as any).menus) {
                const menus = (response.data as any).menus;
                if (Array.isArray(menus) && menus.length > 0) {
                    // 尝试查找名为'main'或'主菜单'的菜单
                    const mainMenu = menus.find((menu: any) =>
                        menu.slug === 'main' ||
                        menu.name === '主菜单' ||
                        menu.name === 'Main Menu' ||
                        menu.name === 'main'
                    );

                    if (mainMenu) {
                        return {
                            requires_auth: false,
                            success: true,
                            data: mainMenu.items || []
                        };
                    } else {
                        // 如果没有找到主菜单，返回第一个菜单
                        return {
                            requires_auth: false,
                            success: true,
                            data: menus[0].items || []
                        };
                    }
                }
            }

            // 如果没有找到菜单，返回默认菜单
            return {
                requires_auth: false,
                success: true,
                data: [
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
            };
        } catch (error) {
            return {
                requires_auth: false,
                success: false,
                error: error instanceof Error ? error.message : 'Failed to fetch menu data',
                data: undefined
            };
        }
    }

    // 获取扁平化的菜单项（用于简单展示）
    static async getFlatMenuItems(): Promise<ApiResponse<MenuTreeItem[]>> {
        try {
            const response = await this.getMainMenu();
            return response;
        } catch (error) {
            return {
                requires_auth: false,
                success: false,
                error: error instanceof Error ? error.message : 'Failed to fetch menu data',
                data: undefined
            };
        }
    }
}