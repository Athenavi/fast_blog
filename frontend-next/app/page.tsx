// 静态导出模式下的首页
// 使用主题组件系统，根据激活的主题动态加载不同的组件
'use client';

import React, {useEffect, useState} from 'react';
import {useThemeComponents} from '@/lib/theme-registry';
import {useHomePageData} from '@/hooks/useHomePageData';
import {ModernHomePage} from "@/components/home/ModernHomePage";
import FrontendLayout from "@/components/FrontendLayout";

export default function HomePage() {
    const {getComponent, loading: themeLoading} = useThemeComponents();
    const {featuredArticles, recentArticles, popularArticles, categories, loading: dataLoading} = useHomePageData();
    
    const [ThemedLayout, setThemedLayout] = useState<React.ComponentType<any> | null>(null);
    const [ThemedHomePage, setThemedHomePage] = useState<React.ComponentType<any> | null>(null);

    useEffect(() => {
        if (!themeLoading) {
            const layout = getComponent('Layout');
            const homePage = getComponent('HomePage');

            console.log('[HomePage] 主题组件检测结果:');
            console.log('  - Layout:', layout ? layout.name : 'null');
            console.log('  - HomePage:', homePage ? homePage.name : 'null');
            
            // 只有当组件存在时才设置
            if (layout) setThemedLayout(() => layout);
            if (homePage) setThemedHomePage(() => homePage);
        }
    }, [themeLoading, getComponent]);
    
    // 加载中状态
    if (themeLoading || dataLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse text-lg">加载中...</div>
            </div>
        );
    }

    // 使用主题组件（如果有）或回退到默认组件
    const Layout = ThemedLayout || FrontendLayout;

    // 为Magazine主题准备数据
    const MagazineHomePage = ThemedHomePage as React.ComponentType<any> | undefined;
    const DefaultHomePage = ModernHomePage;

    // 如果使用的是Magazine主题，传递数据
    const HomePageToRender = MagazineHomePage ? (
        <MagazineHomePage
            featuredArticles={featuredArticles}
            recentArticles={recentArticles}
            popularArticles={popularArticles}
            categories={categories}
        />
    ) : (
        <DefaultHomePage/>
    );
    
    return (
        <Layout>
            {HomePageToRender}
        </Layout>
    );
}