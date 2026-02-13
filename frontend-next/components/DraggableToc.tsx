'use client';

import React, {useEffect, useRef, useState} from 'react';
import tocbot from 'tocbot';
import {springPresets, useSpringAnimation2D} from '@/hooks/useSpringAnimation';

// Tocbot类型定义
interface TocbotOptions {
  tocSelector?: string;
  contentSelector?: string;
  headingSelector?: string;
  positionFixedSelector?: string;
  positionFixedClass?: string;
  fixedSidebarOffset?: number;
  includeHtml?: boolean;
  headingsOffset?: number;
  ignoreSelector?: string;
  linkClass?: string;
  activeLinkClass?: string;
  listClass?: string;
  listItemClass?: string;
  collapseDepth?: number;
  orderedList?: boolean;
  onClick?(e: Event): void;
}

interface TocbotInstance {
  init(options: TocbotOptions): void;
  destroy(): void;
}

interface DraggableTocProps {
    contentSelector?: string;
    headingSelector?: string;
    className?: string;
}

interface Position {
    x: number;
    y: number;
    side: 'left' | 'right';
}

const DraggableToc: React.FC<DraggableTocProps> = ({
    contentSelector = '.article-content',
    headingSelector = 'h1, h2, h3, h4, h5, h6',
    className = ''
}) => {
    DraggableToc.displayName = 'DraggableToc';
    DraggableToc.displayName = 'DraggableToc';
    const [isVisible, setIsVisible] = useState(true);
    const [isMinimized, setIsMinimized] = useState(false);
    const [position, setPosition] = useState<Position>({ x: 0, y: 100, side: 'right' });
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [clickPosition, setClickPosition] = useState<{x: number, y: number} | null>(null); // 记录点击位置
    const [dynamicHeight, setDynamicHeight] = useState<number>(300); // 动态高度状态
    const [isClient, setIsClient] = useState(false); // hydration保护状态
    const [tocInitError, setTocInitError] = useState<string | null>(null); // Tocbot初始化错误状态
    const [isTocInitialized, setIsTocInitialized] = useState(false); // 目录是否已初始化
    const tocRef = useRef<HTMLDivElement>(null);
    const dragHandleRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const tocbotRef = useRef<TocbotInstance | null>(null);

    // hydration完成后标记为客户端
    useEffect(() => {
        setIsClient(true);
    }, []);

    // 使用物理弹簧动画
    const springAnimation = useSpringAnimation2D(
        position.x, 
        position.y, 
        springPresets.blackholeLong // 使用长时间黑洞吸附效果
    );

    // 存储键名
    const STORAGE_KEY = 'draggable_toc_position';
    const MINIMIZED_KEY = 'draggable_toc_minimized';

    // 从localStorage加载位置和最小化状态
    useEffect(() => {
        const loadData = async () => {
            const savedPosition = localStorage.getItem(STORAGE_KEY);
            const savedMinimized = localStorage.getItem(MINIMIZED_KEY);
            
            if (savedPosition) {
                try {
                    const parsed = JSON.parse(savedPosition);
                    setPosition(parsed);
                } catch (error) {
                    console.warn('Failed to parse saved position:', error);
                }
            }
            
            if (savedMinimized) {
                try {
                    setIsMinimized(JSON.parse(savedMinimized));
                } catch (error) {
                    console.warn('Failed to parse minimized state:', error);
                }
            }
        };
        
        loadData();
    }, []);

    // 保存位置和最小化状态到localStorage
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(position));
    }, [position]);
    
    useEffect(() => {
        localStorage.setItem(MINIMIZED_KEY, JSON.stringify(isMinimized));
    }, [isMinimized]);

    // 客户端-only的高度计算 - 避免SSR hydration问题
    useEffect(() => {
        // 仅在客户端执行
        if (typeof window === 'undefined' || isMinimized) return;

        const calculateAndApplyHeight = () => {
            if (!tocRef.current) return;
            
            // 获取实际的视窗高度
            const windowHeight = window.innerHeight;
            const maxAllowedHeight = windowHeight - 100;
            const minHeight = 250;
            
            // 计算理想高度
            const idealHeight = Math.max(
                Math.min(windowHeight * 0.7, maxAllowedHeight),
                minHeight
            );
            
            // 直接修改DOM样式而不是通过React state
            // 这样可以避免hydration mismatch
            tocRef.current.style.height = `${idealHeight}px`;
            
            // 同时更新内部状态用于其他计算
            setDynamicHeight(idealHeight);
        };

        // 延迟执行确保hydration完成
        const timer = setTimeout(() => {
            calculateAndApplyHeight();
            
            // 监听窗口大小变化
            window.addEventListener('resize', calculateAndApplyHeight);
        }, 100);

        return () => {
            clearTimeout(timer);
            if (typeof window !== 'undefined') {
                window.removeEventListener('resize', calculateAndApplyHeight);
            }
        };
    }, [isMinimized]);

    // 安全的Tocbot初始化 - 遵循前端组件安全初始化规范
    // 支持重新初始化以解决最小化后内容消失问题
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const initToc = () => {
            // 如果已经初始化且不是因为最小化状态变化，则跳过
            if (isTocInitialized && !isMinimized) return true;

            try {
                // 安全检查：确保必要的DOM元素存在
                const tocContainer = document.querySelector('.js-draggable-toc-content');
                const contentContainer = document.querySelector(contentSelector);
                
                // 严格验证元素存在性
                if (!tocContainer) {
                    console.warn('TOC container not found, retrying...');
                    return false;
                }
                
                if (!contentContainer) {
                    console.warn('Content container not found, retrying...');
                    return false;
                }

                // 销毁之前的实例
                if (tocbotRef.current) {
                    try {
                        tocbotRef.current.destroy();
                    } catch (destroyError) {
                        if (destroyError instanceof Error) {
                            console.warn('Failed to destroy previous tocbot instance:', destroyError.message);
                        }
                    }
                }

                // 初始化新的tocbot实例
                tocbot.init({
                    tocSelector: '.js-draggable-toc-content',
                    contentSelector: contentSelector,
                    headingSelector: headingSelector,
                    positionFixedSelector: '.js-draggable-toc-content',
                    positionFixedClass: 'is-position-fixed',
                    fixedSidebarOffset: 20,
                    includeHtml: true,
                    headingsOffset: 10,
                    ignoreSelector: '.js-toc-ignore',
                    linkClass: 'toc-link',
                    activeLinkClass: 'is-active-link',
                    listClass: 'toc-list',
                    listItemClass: 'toc-list-item',
                    collapseDepth: 6,
                    orderedList: false,
                    onClick: function (e) {
                        e.preventDefault();
                        const target = e.target as HTMLAnchorElement;
                        const targetId = target.getAttribute('href')?.substring(1);
                        if (targetId) {
                            const targetElement = document.getElementById(targetId);
                            if (targetElement) {
                                targetElement.scrollIntoView({ 
                                    behavior: 'smooth', 
                                    block: 'center' 
                                });
                                // 添加高亮效果
                                targetElement.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                                setTimeout(() => {
                                    targetElement.style.backgroundColor = '';
                                }, 1000);
                            }
                        }
                    }
                });

                tocbotRef.current = tocbot;
                console.log('Tocbot initialized successfully');
                setTocInitError(null); // 清除之前的错误
                setIsTocInitialized(true); // 标记已初始化
                return true;
            } catch (error) {
                if (error instanceof Error) {
                    console.error('Tocbot initialization failed:', error.message);
                    setTocInitError(error.message);
                } else {
                    console.error('Tocbot initialization failed with unknown error');
                    setTocInitError('Unknown initialization error');
                }
                return false;
            }
        };

        // 渐进式初始化策略 - 遵循Tocbot目录功能优化方案
        let attemptCount = 0;
        const maxAttempts = 5;
        
        const progressiveInit = () => {
            attemptCount++;
            const success = initToc();
            
            if (!success && attemptCount < maxAttempts) {
                // 递增延迟重试
                const delay = Math.pow(1.5, attemptCount) * 500;
                console.log(`Tocbot init attempt ${attemptCount}, retrying in ${delay}ms`);
                setTimeout(progressiveInit, delay);
            } else if (!success) {
                console.error('Tocbot failed to initialize after maximum attempts');
                setTocInitError('目录初始化失败，请刷新页面重试');
            }
        };

        // 使用requestAnimationFrame确保DOM完全渲染后初始化
        requestAnimationFrame(() => {
            setTimeout(progressiveInit, 300);
        });

        // 当从最小化状态恢复时，重新初始化目录
        if (isMinimized) {
            // 组件最小化时重置初始化状态
            setIsTocInitialized(false);
        }

        return () => {
            if (tocbotRef.current) {
                try {
                    tocbotRef.current.destroy();
                } catch (error) {
                    if (error instanceof Error) {
                        console.warn('Failed to destroy tocbot on cleanup:', error.message);
                    }
                }
            }
        };
    }, [isMinimized, contentSelector, headingSelector]); // 依赖数组包含最小化状态，支持重新初始化

    // 拖动相关事件处理
    const handleMouseDown = (e: React.MouseEvent) => {
        if (!tocRef.current) return;
        
        const rect = tocRef.current.getBoundingClientRect();
        setDragOffset({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        });
        setIsDragging(true);
        e.preventDefault();
    };

    const handleMouseMove = (e: MouseEvent) => {
        if (!isDragging || !tocRef.current) return;

        const newX = e.clientX - dragOffset.x;
        const newY = e.clientY - dragOffset.y;
        
        // SSR兼容性检查
        if (typeof window === 'undefined') return;
        
        // 获取视窗尺寸
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const tocWidth = tocRef.current.offsetWidth;
        const tocHeight = tocRef.current.offsetHeight;

        // 计算边界限制 - 确保组件不会超出视窗
        const minX = 20;  // 左边距
        const maxX = windowWidth - tocWidth - 20;  // 右边距
        const minY = 20;  // 上边距
        const maxY = windowHeight - tocHeight - 20; // 下边距

        // 限制在视窗内
        const boundedX = Math.max(minX, Math.min(maxX, newX));
        const boundedY = Math.max(minY, Math.min(maxY, newY));

        // 判断应该吸附到左边还是右边
        const side: 'left' | 'right' = boundedX < windowWidth / 2 ? 'left' : 'right';
        const finalX = side === 'left' ? 20 : windowWidth - tocWidth - 20;

        setPosition({
            x: finalX,
            y: boundedY,
            side
        });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
        // 鼠标释放时启动弹簧动画
        springAnimation.setTarget(position.x, position.y);
    };

    // 添加全局事件监听器
    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'grabbing';
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
        };
    }, [isDragging, dragOffset, position.x, position.y]); // 添加依赖确保动画同步

    // 根据位置和最小化状态计算样式 - SSR安全版本
    const getTocStyle = () => {
        // SSR兼容性检查 - 使用静态默认值避免hydration不匹配
        const windowWidth = typeof window !== 'undefined' ? window.innerWidth : 1200;
        
        if (isMinimized) {
            // 最小化状态 - 固定在导航栏右侧
            return {
                position: 'fixed' as const,
                top: '16px',
                right: '120px',
                zIndex: 1000,
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                border: '2px solid #3b82f6'
            };
        } else {
            // 正常状态 - 可拖动的完整目录
            // 使用固定值避免hydration期间的计算差异
            const baseStyle: React.CSSProperties = {
                position: 'fixed',
                top: '100px', // 固定值而不是动态position.y
                zIndex: 1000,
                width: '280px',
                height: '300px', // 固定值而不是动态dynamicHeight
                minHeight: '200px',
                maxHeight: 'calc(100vh - 80px)',
                transition: 'all 0.3s ease', // 简化transition避免复杂计算
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
                borderRadius: '8px',
                overflow: 'hidden',
                userSelect: 'none',
                display: 'flex',
                flexDirection: 'column'
            };

            // 使用固定的左右位置计算
            if (position.side === 'left') {
                return {
                    ...baseStyle,
                    left: '20px', // 固定值
                    borderLeft: '3px solid #3b82f6'
                };
            } else {
                return {
                    ...baseStyle,
                    right: '20px', // 固定值
                    borderRight: '3px solid #3b82f6'
                };
            }
        }
    };

    // 切换可见性
    const toggleVisibility = () => {
        setIsVisible(!isVisible);
    };

    // 切换最小化状态
    const toggleMinimize = (e?: React.MouseEvent) => {
        const newState = !isMinimized;
        setIsMinimized(newState);
        
        if (newState) {
            // 最小化时：记录点击位置并启动从点击点开始的动画
            if (e) {
                const rect = tocRef.current?.getBoundingClientRect();
                if (rect) {
                    // 计算相对于组件的点击位置
                    const clickX = e.clientX - rect.left;
                    const clickY = e.clientY - rect.top;
                    setClickPosition({ x: clickX, y: clickY });
                    
                    // 使用特殊的点击吸附动画
                    // 暂时使用当前位置作为目标，实际的视觉效果通过CSS实现
                    springAnimation.setTarget(position.x, position.y);
                }
            }
        } else {
            // 展开时：清除点击位置记录，并触发目录重新初始化
            setClickPosition(null);
            springAnimation.setTarget(position.x, position.y);
            // 重置初始化状态以便重新生成目录
            setIsTocInitialized(false);
        }
    };

    // 重置位置
    const resetPosition = () => {
        // SSR兼容性检查
        const windowWidth = typeof window !== 'undefined' ? window.innerWidth : 1200;
        const newPosition: Position = { x: windowWidth - 300, y: 100, side: 'right' };
        setPosition(newPosition);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newPosition));
        setIsMinimized(false); // 重置时取消最小化
        // 重置弹簧动画
        springAnimation.reset();
        springAnimation.setTarget(newPosition.x, newPosition.y);
    };

    // hydration期间返回简单结构避免样式不匹配
    if (!isClient) {
        return (
            <div 
                className="draggable-toc-container"
                style={{
                    position: 'fixed',
                    top: '100px',
                    right: '20px',
                    width: '280px',
                    height: '300px'
                }}
            />
        );
    }

    return (
        <div 
            ref={tocRef}
            className={`bg-white dark:bg-gray-800 shadow-lg ${isMinimized ? 'minimized-toc-button' : 'draggable-toc-container'} ${className} ${isVisible ? '' : 'hidden'} ${isDragging ? 'dragging' : ''}`}
            style={getTocStyle()}
            onClick={isMinimized ? (e) => toggleMinimize(e) : undefined}
            role={isMinimized ? "button" : "region"}
            aria-label={isMinimized ? "展开文章目录" : "可拖动文章目录"}
        >
            {isMinimized ? (
                // 最小化状态 - 只显示图标按钮
                <div className="flex items-center justify-center w-full h-full" aria-hidden="true">
                    <i className="fas fa-list text-blue-600 dark:text-blue-400 text-lg"></i>
                </div>
            ) : (
                // 正常状态 - 完整的目录界面
                <>
                    {/* 拖动手柄 */}
                    <div
                        ref={dragHandleRef}
                        onMouseDown={handleMouseDown}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600 cursor-grab active:cursor-grabbing drag-handle"

                    >
                        <div className="flex items-center">
                            <i className="fas fa-list mr-2 text-blue-600 dark:text-blue-400"></i>
                            <span className="font-medium text-gray-800 dark:text-gray-200">文章目录</span>
                        </div>
                        <div className="flex items-center space-x-1">
                            {/* 最小化按钮 - 记录点击位置 */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    toggleMinimize(e);
                                }}
                                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors min-w-[28px] flex items-center justify-center control-button"
                                title="最小化目录"
        
                            >
                                <i className="fas fa-compress text-xs"></i>
                            </button>
                            {/* 重置按钮 */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    resetPosition();
                                }}
                                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors min-w-[28px] flex items-center justify-center control-button"
                                title="重置位置"
        
                            >
                                <i className="fas fa-sync-alt text-xs"></i>
                            </button>
                        </div>
                    </div>

                    {/* 目录内容 */}
                    <div 
                        ref={contentRef}
                        className="toc-content-area p-4 overflow-y-auto"
                        style={{
                            maxHeight: `calc(${dynamicHeight}px - 96px)`
                        }}
                    >
                        <div 
                            className="js-draggable-toc-content toc"
                            style={{ minHeight: '100px' }}
                        >
                            {tocInitError ? (
                                // 错误状态
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                    <div className="text-red-500 mb-2">
                                        <i className="fas fa-exclamation-triangle text-xl"></i>
                                    </div>
                                    <p className="text-red-600 font-medium mb-2">目录初始化失败</p>
                                    <p className="text-gray-500 text-sm mb-4">{tocInitError}</p>
                                    <button 
                                        onClick={() => {
                                            setTocInitError(null);
                                            setIsTocInitialized(false); // 允许重新初始化
                                            // 触发重新初始化
                                            if (typeof window !== 'undefined') {
                                                window.location.reload();
                                            }
                                        }}
                                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 transition-colors"
                                    >
                                        重新加载
                                    </button>
                                </div>
                            ) : !isTocInitialized ? (
                                // 加载状态
                                <div className="flex items-center justify-center py-8">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mr-2"></div>
                                    <span className="text-gray-500 text-sm">正在生成目录...</span>
                                </div>
                            ) : (
                                // 目录已生成，显示空内容（由tocbot填充）
                                <div className="py-4 text-center text-gray-500 text-sm">
                                    目录内容将在此处显示
                                </div>
                            )}
                        </div>
                    </div>

                    {/* 底部提示 */}
                    <div 
                        className="px-4 py-2 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400"
                    >
                        <div className="flex items-center justify-between">
                            <span>可拖动调整位置</span>
                            <span>吸附：{position.side === 'left' ? '左侧' : '右侧'}</span>
                        </div>
                    </div>
                </>
            )}

        </div>
    );
};

export default DraggableToc;