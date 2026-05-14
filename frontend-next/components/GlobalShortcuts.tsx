'use client';

import {useRouter} from 'next/navigation';
import {useHotkeys} from '@/hooks/useHotkeys';

interface GlobalShortcutsProps {
    enabled?: boolean;
}

/**
 * 全局快捷键组件
 * 提供全站通用的键盘快捷键支持
 */
export function GlobalShortcuts({enabled = true}: GlobalShortcutsProps) {
    const router = useRouter();

    // 定义全局快捷键
    useHotkeys({
        // Ctrl+K: 快速搜索
        'ctrl+k': (e) => {
            e.preventDefault();
            // 触发搜索框聚焦或打开搜索模态框
            const searchInput = document.querySelector('input[placeholder*="搜索"], input[placeholder*="Search"]') as HTMLInputElement;
            if (searchInput) {
                searchInput.focus();
            } else {
                // 如果没有找到搜索框，导航到搜索页面
                router.push('/search');
            }
        },

        // Ctrl+N: 新建文章（仅登录用户）
        'ctrl+n': (e) => {
            e.preventDefault();
            // 检查用户是否已登录
            const token = localStorage.getItem('token') || sessionStorage.getItem('token');
            if (token) {
                router.push('/admin/blog');
            } else {
                router.push('/login');
            }
        },

        // ESC: 关闭弹窗/模态框
        'escape': (e) => {
            e.preventDefault();
            // 查找并关闭所有打开的模态框/对话框
            const modals = document.querySelectorAll('[role="dialog"], .modal, [data-state="open"]');
            if (modals.length > 0) {
                // 触发最近打开的模态框的关闭按钮
                const lastModal = modals[modals.length - 1] as unknown as HTMLElement;
                const closeButton = lastModal.querySelector('button[aria-label="Close"], button[data-state="close"]') as HTMLButtonElement;
                if (closeButton) {
                    closeButton.click();
                }
            }
        },

        // Ctrl+/: 显示快捷键帮助
        'ctrl+/': (e) => {
            e.preventDefault();
            // 触发快捷键帮助对话框
            const helpButton = document.querySelector('[data-shortcut-help]') as HTMLButtonElement;
            if (helpButton) {
                helpButton.click();
            }
        },

        // Alt+H: 返回首页
        'alt+h': (e) => {
            e.preventDefault();
            router.push('/');
        },

        // G+H: Go to Home (Vim风格)
        'g+h': (e) => {
            e.preventDefault();
            router.push('/');
        },
    }, enabled);

    return null; // 这个组件不渲染任何内容
}

export default GlobalShortcuts;
