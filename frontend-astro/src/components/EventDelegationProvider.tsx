/**
 * EventDelegationProvider - 事件委托提供者组件
 * 使用单一事件监听器处理多个子元素事件，大幅减少监听器数量
 *
 * 使用示例:
 * ```tsx
 * <EventDelegationProvider
 *   on点击={{
 *     selector: '.btn',
 *     handler: (e) => handleButtonClick(e.target)
 *   }}
 *   onScroll={{
 *     selector: '.scrollable',
 *     handler: (e) => handleScroll(e.target)
 *   }}
 * >
 *   <button className="btn">点击我</button>
 *   <div className="scrollable">...</div>
 * </EventDelegationProvider>
 * ```
 */

'use client';

import React, {memo, useCallback, useEffect, useRef} from 'react';

export interface EventDelegationConfig {
  /** CSS 选择器 */
  selector: string;
  /** 事件处理函数 */
  handler: (element: Element, event: Event) => void;
  /** 是否使用捕获阶段 */
  capture?: boolean;
  /** 是否使用被动监听 */
  passive?: boolean;
}

interface EventDelegationProviderProps {
  /** 子元素 */
  children: React.ReactNode;
  /** 点击事件配置 */
  onClick?: EventDelegationConfig;
  /** 滚动事件配置 */
  onScroll?: EventDelegationConfig;
  /** 键盘事件配置 */
  onKeyDown?: EventDelegationConfig;
  /** 鼠标移动事件配置 */
  onMouseMove?: EventDelegationConfig;
  /** 自定义事件配置映射 */
  events?: Record<string, EventDelegationConfig>;
  /** 根元素引用 */
  rootRef?: React.Ref<HTMLElement>;
}

const EventDelegationProvider = memo(({
                                        children,
                                        onClick,
                                        onScroll,
                                        onKeyDown,
                                        onMouseMove,
                                        events,
                                        rootRef,
                                      }: EventDelegationProviderProps) => {
  const internalRef = useRef<HTMLDivElement>(null);
  const root = (rootRef as any)?.current || internalRef.current;

  const setupDelegation = useCallback((
    eventName: string,
    config: EventDelegationConfig | undefined
  ) => {
    if (!config || !root) return;

    const handler = (event: Event) => {
      const target = event.target as Element;
      const matched = target.closest(config.selector);

      if (matched) {
        config.handler(matched, event);
      }
    };

    root.addEventListener(eventName, handler, {
      capture: config.capture || false,
      passive: config.passive || false
    });

    return () => {
      root.removeEventListener(eventName, handler, {
        capture: config.capture || false,
        passive: config.passive || false
      });
    };
  }, [root]);

  useEffect(() => {
    if (!root) return;

    const cleanupFunctions: Array<() => void> = [];

    // 设置预定义事件
    if (onClick) cleanupFunctions.push(setupDelegation('click', onClick));
    if (onScroll) cleanupFunctions.push(setupDelegation('scroll', onScroll));
    if (onKeyDown) cleanupFunctions.push(setupDelegation('keydown', onKeyDown));
    if (onMouseMove) cleanupFunctions.push(setupDelegation('mousemove', onMouseMove));

    // 设置自定义事件
    if (events) {
      Object.entries(events).forEach(([eventName, config]) => {
        cleanupFunctions.push(setupDelegation(eventName, config));
      });
    }

    return () => {
      cleanupFunctions.forEach(clean => clean?.());
    };
  }, [root, onClick, onScroll, onKeyDown, onMouseMove, events, setupDelegation]);

  // 如果提供了外部 rootRef，不需要渲染包装元素
  if (rootRef) {
    return <>{children}</>;
  }

  return (
    <div ref={internalRef} className="event-delegation-root">
      {children}
    </div>
  );
});

EventDelegationProvider.displayName = 'EventDelegationProvider';

export default EventDelegationProvider;
