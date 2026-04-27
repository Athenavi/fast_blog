/**
 * 主题组件注册表
 *
 * 这是一个颠覆性的主题系统架构，参考WordPress的Template Hierarchy
 * 每个主题可以提供自己的一组组件，系统会根据当前激活的主题动态加载对应的组件
 */

import React from 'react';
import {useTheme} from '@/hooks/useTheme';

// 定义组件映射类型
type ComponentMap = {
    // 布局组件
    Layout?: React.ComponentType<{ children: React.ReactNode }>;
    Header?: React.ComponentType;
    Footer?: React.ComponentType;

    // 首页组件
    HomePage?: React.ComponentType;
    HeroSection?: React.ComponentType<any>;

    // 文章列表组件
    ArticleList?: React.ComponentType<any>;
    ArticleCard?: React.ComponentType<any>;

    // 文章详情组件
    ArticleDetail?: React.ComponentType<any>;

    // 分类页面组件
    CategoryPage?: React.ComponentType<any>;

    // 其他页面组件
    AboutPage?: React.ComponentType;
    ContactPage?: React.ComponentType;
};

// 主题组件缓存
const themeComponentCache = new Map<string, ComponentMap>();

/**
 * 动态加载主题组件
 *
 * @param themeSlug 主题slug
 * @returns 主题组件映射
 */
export async function loadThemeComponents(themeSlug: string): Promise<ComponentMap> {
    // 检查缓存
    if (themeComponentCache.has(themeSlug)) {
        return themeComponentCache.get(themeSlug)!;
    }

    let components: ComponentMap = {};

    try {
        // 动态导入主题组件
        // 主题组件位于 themes/{themeSlug}/components/ 目录
        switch (themeSlug) {
            case 'magazine':
                const magazineComponents = await import('@/themes/magazine/components');
                components = (magazineComponents.default as ComponentMap) || (magazineComponents as unknown as ComponentMap);
                break;

            case 'modern-minimal':
                // 检查是否有自定义组件，否则使用默认
                try {
                    const modernComponents = await import('@/themes/modern-minimal/components');
                    components = (modernComponents.default as ComponentMap) || (modernComponents as unknown as ComponentMap);
                    // 如果导出为空对象，使用默认组件
                    if (Object.keys(components).length === 0) {
                        components = await loadDefaultComponents();
                    }
                } catch (e) {
                    console.warn('[ThemeRegistry] modern-minimal主题组件不存在，使用默认组件');
                    components = await loadDefaultComponents();
                }
                break;

            case 'default':
            default:
                // 使用默认组件（当前的组件）
                components = await loadDefaultComponents();
                break;
        }

        // 缓存结果
        themeComponentCache.set(themeSlug, components);

        console.log(`[ThemeRegistry] 已加载主题组件: ${themeSlug}`, Object.keys(components));

        return components;
    } catch (error) {
        console.error(`[ThemeRegistry] 加载主题组件失败: ${themeSlug}`, error);
        // 回退到默认组件
        const defaultComponents = await loadDefaultComponents();
        themeComponentCache.set(themeSlug, defaultComponents);
        return defaultComponents;
    }
}

/**
 * 加载默认组件（现有的组件）
 */
async function loadDefaultComponents(): Promise<ComponentMap> {
    const [
        {FrontendLayout},
        {default: Header},
        {default: Footer},
        {ModernHomePage},
        {default: ArticleCard}
    ] = await Promise.all([
        import('@/components/FrontendLayout'),
        import('@/components/Header'),
        import('@/components/Footer'),
        import('@/components/home/ModernHomePage'),
        import('@/components/ArticleCard')
    ]);

    return {
        Layout: FrontendLayout,
        Header,
        Footer,
        HomePage: ModernHomePage,
        ArticleCard,
    };
}

/**
 * Hook: 获取当前主题的组件
 *
 * @example
 * const { HomePage, ArticleCard } = useThemeComponents();
 * return <HomePage />;
 */
export function useThemeComponents() {
    const {config, isLoading} = useTheme();
    const [components, setComponents] = React.useState<ComponentMap>({});
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        if (!isLoading && config) {
            const themeSlug = config.metadata?.slug || 'default';
            setLoading(true);
            loadThemeComponents(themeSlug).then(setComponents).finally(() => setLoading(false));
        }
    }, [config, isLoading]);

    return {
        components,
        loading: loading || isLoading,
        // 提供便捷的访问方式
        getComponent: <K extends keyof ComponentMap>(name: K): ComponentMap[K] | undefined => {
            return components[name];
        }
    };
}

/**
 * 高阶组件：用主题组件包装
 *
 * @example
 * const ThemedHomePage = withThemeComponent('HomePage', DefaultHomePage);
 */
export function withThemeComponent<K extends keyof ComponentMap>(
    componentName: K,
    FallbackComponent: React.ComponentType<any>
): React.ComponentType<any> {
    return function ThemedComponent(props: any) {
        const {getComponent, loading} = useThemeComponents();
        const ThemeComponent = getComponent(componentName);

        if (loading) {
            return <div className="animate-pulse">加载中...</div>;
        }

        const ComponentToRender = ThemeComponent || FallbackComponent;
        return <ComponentToRender {...props} />;
    };
}

// 导出组件名称常量，避免硬编码字符串
export const THEME_COMPONENTS = {
    LAYOUT: 'Layout',
    HEADER: 'Header',
    FOOTER: 'Footer',
    HOME_PAGE: 'HomePage',
    HERO_SECTION: 'HeroSection',
    ARTICLE_LIST: 'ArticleList',
    ARTICLE_CARD: 'ArticleCard',
    ARTICLE_DETAIL: 'ArticleDetail',
    CATEGORY_PAGE: 'CategoryPage',
    ABOUT_PAGE: 'AboutPage',
    CONTACT_PAGE: 'ContactPage',
} as const;
