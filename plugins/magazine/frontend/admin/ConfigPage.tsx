'use client';
import React from 'react';
import {AdminShell} from '@/components/admin/AdminShell';
import ThemeConfigPanel from '@/components/plugins/ThemeConfigPanel';

export default function MagazineThemeConfig() {
    return (
        <AdminShell title="杂志主题配置">
            <ThemeConfigPanel
                pluginSlug="magazine"
                themeName="Magazine"
                themeDescription="杂志风格主题 - 网格布局、特色图片展示、多栏目支持"
            />
        </AdminShell>
    );
}
