'use client';

import React, {useCallback, useEffect, useState} from 'react';

interface HeadingItem {
  id: string;
  text: string;
  level: number;
  element: HTMLElement;
}

interface TableOfContentsProps {
  contentSelector?: string;
  headingSelector?: string;
  offset?: number;
}

const TableOfContents: React.FC<TableOfContentsProps> = ({
                                                           contentSelector = '.article-content',
                                                           headingSelector = 'h1, h2, h3, h4, h5, h6',
                                                           offset = 100,
                                                         }) => {
  const [headings, setHeadings] = useState<HeadingItem[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  // 生成唯一ID
  const generateId = useCallback((text: string, index: number): string => {
    return `heading-${text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]/g, '-')}-${index}`;
  }, []);

  // 提取标题
  const extractHeadings = useCallback(() => {
    const contentElement = document.querySelector(contentSelector);
    if (!contentElement) {
      console.warn('[TOC] Content element not found');
      return [];
    }

    const headingElements = Array.from(
        contentElement.querySelectorAll(headingSelector)
    ) as HTMLElement[];

    if (headingElements.length === 0) {
      console.warn('[TOC] No headings found');
      return [];
    }

    // 为没有ID的标题添加ID
    const headingItems: HeadingItem[] = headingElements.map((element, index) => {
      let id = element.id;
      if (!id) {
        id = generateId(element.textContent || '', index);
        element.id = id;
      }

      const level = parseInt(element.tagName.substring(1), 10);

      return {
        id,
        text: element.textContent || '',
        level,
        element,
      };
    });

    console.log(`[TOC] ✅ Extracted ${headingItems.length} headings`);
    return headingItems;
  }, [contentSelector, headingSelector, generateId]);

  // 滚动处理
  const handleScroll = useCallback(() => {
    const scrollPosition = window.scrollY + offset;

    // 找到当前可见的标题
    for (let i = headings.length - 1; i >= 0; i--) {
      const heading = headings[i];
      const elementTop = heading.element.offsetTop;

      if (scrollPosition >= elementTop) {
        setActiveId(heading.id);
        return;
      }
    }

    // 如果没有找到，设置为第一个
    if (headings.length > 0) {
      setActiveId(headings[0].id);
    }
  }, [headings, offset]);

  // 点击标题滚动
  const handleHeadingClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      const elementPosition = element.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth',
      });

      setActiveId(id);
    }
  };

  // 初始化
  useEffect(() => {
    setIsLoading(true);

    // 延迟执行以确保内容已加载
    const timer = setTimeout(() => {
      const extractedHeadings = extractHeadings();
      setHeadings(extractedHeadings);
      setIsLoading(false);

      if (extractedHeadings.length > 0) {
        setActiveId(extractedHeadings[0].id);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [extractHeadings]);

  // 监听滚动
  useEffect(() => {
    if (headings.length === 0) return;

    window.addEventListener('scroll', handleScroll, {passive: true});
    handleScroll(); // 初始检查

    return () => window.removeEventListener('scroll', handleScroll);
  }, [headings, handleScroll]);

  // 渲染目录项
  const renderHeading = (heading: HeadingItem, index: number) => {
    const isActive = activeId === heading.id;
    const indentLevel = (heading.level - 1) * 12; // 每级缩进12px

    return (
        <li key={heading.id} style={{marginLeft: `${indentLevel}px`}} className="mb-1">
          <a
              href={`#${heading.id}`}
              onClick={(e) => handleHeadingClick(e, heading.id)}
              className={`block py-1.5 px-2 text-sm rounded transition-all duration-200 ${
                  isActive
                      ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium border-l-2 border-blue-500'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
          >
            {heading.text}
          </a>
        </li>
    );
  };

  if (isLoading) {
    return (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-sm text-gray-500">加载中...</span>
        </div>
    );
  }

  if (headings.length === 0) {
    return (
        <div className="text-center py-8 text-gray-400 text-sm">
          暂无目录
        </div>
    );
  }

  return (
      <nav aria-label="文章目录" className="toc-nav">
        <ul className="space-y-0.5 list-none p-0 m-0">
          {headings.map(renderHeading)}
        </ul>
      </nav>
  );
};

export default TableOfContents;
