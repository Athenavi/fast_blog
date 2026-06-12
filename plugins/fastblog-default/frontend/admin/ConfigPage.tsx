'use client';
import React from 'react';
import {AdminShell} from '@/components/admin/AdminShell';
import {QueryProvider} from '@/components/QueryProvider';
import ThemeConfigPanel from '@/components/plugins/ThemeConfigPanel';

export default function DefaultThemeConfig() {
    return (
        <AdminShell title="默认主题配置">
            <QueryProvider>
                <ThemeConfigPanel
                    pluginSlug="fastblog-default"
                    themeName="FastBlog Default"
                    themeDescription="简洁、现代、响应式设计"
                />
            </QueryProvider>
        </AdminShell>
    );
}
