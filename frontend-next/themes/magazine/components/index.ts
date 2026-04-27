/**
 * Magazine主题组件导出
 */

import MagazineLayout from './MagazineLayout';
import MagazineHeader from './MagazineHeader';
import MagazineFooter from './MagazineFooter';
import MagazineHomePage from './MagazineHomePage';
import MagazineArticleCard from './MagazineArticleCard';

export {MagazineLayout, MagazineHeader, MagazineFooter, MagazineHomePage, MagazineArticleCard};

// 也导出带别名的版本
export {MagazineLayout as Layout};
export {MagazineHeader as Header};
export {MagazineFooter as Footer};
export {MagazineHomePage as HomePage};
export {MagazineArticleCard as ArticleCard};

// 默认导出所有组件
export default {
    Layout: MagazineLayout,
    Header: MagazineHeader,
    Footer: MagazineFooter,
    HomePage: MagazineHomePage,
    ArticleCard: MagazineArticleCard,
};
