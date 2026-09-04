/**
 * useEventListener - 统一事件监听 Hook
 * 支持事件委托，自动清理，减少事件监听器数量
 *
 * 使用示例:
 * ```tsx
 * // 基本用法
 * useEventListener('click', handleClick);
 *
 * // 指定目标元素
 * useEventListener('scroll', handleScroll, window);
 *
 * // 事件委托（推荐）
 * useEventListener('click', handleItemClick, document, {
 *   selector: '.item',
 *   handler: (e) => handleItemClick(e.target)
 * });
 * ```
 */

import {useCallback, useLayoutEffect} from 'react';

export interface UseEventListenerOptions {
  /** 事件委托选择器 */
  selector?: string;
  /** 是否使用捕获阶段 */
  capture?: boolean;
  /** 是否使用被动监听 */
  passive?: boolean;
  /** 是否只监听一次 */
  once?: boolean;
}

function useEventListener(
  eventName: string,
  handler: ((event: any) => void) | null,
  target: EventTarget | null = null,
  options: UseEventListenerOptions = {}
) {
  const {selector, capture = false, passive = false, once = false} = options;

  const savedHandler = useCallback(handler, [handler]);

  useLayoutEffect(() => {
    // 如果没有 handler 或 target，不添加监听器
    if (!savedHandler) return;

    const domTarget = target || window;
    if (!(domTarget instanceof EventTarget)) return;

    const eventOptions = {capture, passive, once};

    // 如果使用事件委托，需要包装处理函数
    const eventHandler = selector
      ? ((event: Event) => {
        const targetElement = event.target as Element;
        const matchedElement = targetElement.closest(selector);
        if (matchedElement) {
          // 修改 event 的 currentTarget 为匹配的元素
          const modifiedEvent = {
            ...event,
            currentTarget: matchedElement,
            delegator: domTarget
          };
          savedHandler(modifiedEvent);
        }
      })
      : savedHandler;

    domTarget.addEventListener(eventName, eventHandler, eventOptions);

    return () => {
      domTarget.removeEventListener(eventName, eventHandler, eventOptions);
    };
  }, [eventName, savedHandler, target, selector, capture, passive, once]);
}

export default useEventListener;
