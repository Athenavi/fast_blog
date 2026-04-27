/**
 * Modern Minimal Theme Components
 * 现代简约主题组件 - 支持代码高亮、目录、深色模式
 */

import ModernMinimalLayout from './ModernMinimalLayout';
import ModernMinimalHeader from './ModernMinimalHeader';
import ModernMinimalFooter from './ModernMinimalFooter';
import ModernMinimalHomePage from './ModernMinimalHomePage';
import ModernMinimalArticleCard from './ModernMinimalArticleCard';
import TableOfContents from './TableOfContents';
import CodeBlock from './CodeBlock';

export {
    ModernMinimalLayout,
    ModernMinimalHeader,
    ModernMinimalFooter,
    ModernMinimalHomePage,
    ModernMinimalArticleCard,
    TableOfContents,
    CodeBlock
};

// 默认导出所有组件
export default {
    Layout: ModernMinimalLayout,
    Header: ModernMinimalHeader,
    Footer: ModernMinimalFooter,
    HomePage: ModernMinimalHomePage,
    ArticleCard: ModernMinimalArticleCard,
};
