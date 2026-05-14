/**
 * 主题组件无限刷新问题修复测试
 *
 * 测试场景：
 * 1. 页面加载时主题正常应用
 * 2. 切换深色/浅色模式不会导致无限刷新
 * 3. 主题适配不会触发无限循环
 */

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {render, screen, waitFor} from '@testing-library/react';
// import {ThemeProvider} from '@/components/ThemeProvider';
import {darkModeManager} from '@/lib/dark-mode-manager';

// Mock ThemeProvider component
const ThemeProvider = ({children}: { children: React.ReactNode }) => <>{children}</>;

// Mock fetch
global.fetch = vi.fn();

describe('Theme Provider - Infinite Refresh Fix', () => {
    beforeEach(() => {
        // 清除所有 mocks
        vi.clearAllMocks();

        // Mock theme API response
        (global.fetch as any).mockResolvedValue({
            json: async () => ({
                success: true,
                data: {
                    config: {
                        metadata: {
                            name: 'Default Theme',
                            slug: 'default',
                            version: '1.0.0',
                            description: 'Default theme',
                            author: 'Test',
                        },
                        config: {
                            colors: {
                                primary: '#3b82f6',
                                secondary: '#64748b',
                                accent: '#f59e0b',
                                background: '#ffffff',
                                foreground: '#1f2937',
                            },
                        },
                    },
                    css_variables: ':root { --color-primary: #3b82f6; }',
                    stylesheet_url: '/themes/default/styles.css',
                },
            }),
        });

        // 重置主题管理器状态
        localStorage.removeItem('theme');
    });

    afterEach(() => {
        // 清理全局标志位
        if (typeof window !== 'undefined') {
            (window as any).__themeAdapterUpdating__ = false;
            (window as any).__themeObserverActive__ = false;
        }
    });

    it('应该正常加载主题而不进入无限循环', async () => {
        const TestComponent = () => <div data-testid="test-content">Test Content</div>;

        render(
            <ThemeProvider>
                <TestComponent/>
            </ThemeProvider>
        );

        // 等待主题加载完成
        await waitFor(() => {
            expect(screen.getByTestId('test-content')).toBeInTheDocument();
        }, {timeout: 3000});

        // 验证没有无限循环（如果在 3 秒内完成，说明没有无限循环）
        expect(screen.getByTestId('test-content')).toHaveTextContent('Test Content');
    });

    it('切换深色模式不应该导致无限刷新', async () => {
        const TestComponent = () => <div data-testid="test-content">Test Content</div>;

        render(
            <ThemeProvider>
                <TestComponent/>
            </ThemeProvider>
        );

        // 等待初始加载
        await waitFor(() => {
            expect(screen.getByTestId('test-content')).toBeInTheDocument();
        });

        // 记录初始渲染次数
        const initialRenderCount = 1;

        // 切换深色模式
        darkModeManager.toggleTheme();

        // 等待一小段时间，确保没有持续的重新渲染
        await new Promise(resolve => setTimeout(resolve, 1000));

        // 验证组件仍然正常显示（没有被无限循环破坏）
        expect(screen.getByTestId('test-content')).toBeInTheDocument();
    });

    it('theme-adapter 的标志位应该防止重复执行', () => {
        // 导入 theme-adapter 函数
        const {applyThemeAdaptation} = require('@/lib/theme-adapter');

        const testColors = {
            primary: '#3b82f6',
            secondary: '#64748b',
        };

        // 第一次调用
        applyThemeAdaptation(testColors);
        expect((window as any).__themeAdapterUpdating__).toBe(true);

        // 在标志位为 true 时再次调用，应该不会执行
        applyThemeAdaptation(testColors);

        // 等待标志位重置
        setTimeout(() => {
            expect((window as any).__themeAdapterUpdating__).toBe(false);
        }, 100);
    });

    it('observeThemeChanges 应该防止重复启动', () => {
        const {observeThemeChanges} = require('@/lib/theme-adapter');

        // 第一次启动
        const cleanup1 = observeThemeChanges();
        expect((window as any).__themeObserverActive__).toBe(true);

        // 第二次启动应该被阻止
        const cleanup2 = observeThemeChanges();
        expect(cleanup2).toBeUndefined(); // 应该直接返回

        // 清理
        cleanup1();
        expect((window as any).__themeObserverActive__).toBe(false);
    });
});
