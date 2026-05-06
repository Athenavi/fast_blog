'use client';

import React, {useState} from 'react';
import {useHomePageData} from '@/hooks/useHomePageData';
import ModernHomePage from "@/components/home/ModernHomePage";
import FrontendLayout from "@/components/FrontendLayout";

export default function HomePage() {
    const {featuredArticles, recentArticles, popularArticles, categories, loading: dataLoading} = useHomePageData();

    const [ThemedLayout, setThemedLayout] = useState<React.ComponentType<any> | null>(null);
    const [ThemedHomePage, setThemedHomePage] = useState<React.ComponentType<any> | null>(null);


    // 使用主题组件（如果有）或回退到默认组件
    const Layout = FrontendLayout;

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