import { useEffect, useCallback } from 'react';

interface HotkeyMap {
  [key: string]: (e: KeyboardEvent) => void;
}

/**
 * 键盘快捷键 Hook
 * @param hotkeys - 快捷键映射表 { 'ctrl+k': handler }
 * @param enabled - 是否启用快捷键
 */
export function useHotkeys(hotkeys: HotkeyMap, enabled: boolean = true) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // 忽略输入框中的按键
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // 允许 Esc 键在输入框中工作
        if (e.key !== 'Escape') return;
      }

      // 构建按键字符串
      const keys: string[] = [];
      if (e.ctrlKey || e.metaKey) keys.push('ctrl');
      if (e.altKey) keys.push('alt');
      if (e.shiftKey) keys.push('shift');
      
      // 处理特殊键名
      let key = e.key.toLowerCase();
      if (key === ' ') key = 'space';
      if (key.length === 1) keys.push(key);
      else if (['escape', 'enter', 'backspace', 'delete', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        keys.push(key);
      } else {
        return; // 忽略其他非标准键
      }

      const keyString = keys.join('+');

      // 查找匹配的处理器
      const handler = hotkeys[keyString];
      if (handler) {
        e.preventDefault();
        handler(e);
      }
    },
    [hotkeys, enabled]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);
}
