'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {useHomePageData} from '@/hooks/useHomePageData';
import OptimizedHomePage from "@/components/home/OptimizedHomePage";
import FrontendLayout from "@/components/FrontendLayout";

export default function HomePage() {
    const router = useRouter();
    const {featuredArticles, recentArticles, popularArticles, categories, loading: dataLoading} = useHomePageData();

    const [ThemedLayout, setThemedLayout] = useState<React.ComponentType<any> | null>(null);
    const [ThemedHomePage, setThemedHomePage] = useState<React.ComponentType<any> | null>(null);

    // 检测是否在 Capacitor 环境中，如果是则跳转到移动端首页
    useEffect(() => {
        const isCapacitor = typeof window !== 'undefined' &&
            (!!(window as any).Capacitor ||
                !!(window as any).CapacitorPlugins ||
                window.location.protocol === 'capacitor:');

        if (isCapacitor) {
            // 在 Capacitor 环境中，跳转到移动端首页
            router.replace('/mobile');
        }
    }, [router]);

    // 使用主题组件（如果有）或回退到默认组件
    const Layout = FrontendLayout;

    // 为Magazine主题准备数据
    const MagazineHomePage = ThemedHomePage as React.ComponentType<any> | undefined;
    // 使用优化后的首页组件（移除 framer-motion 依赖）
    const DefaultHomePage = OptimizedHomePage;

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