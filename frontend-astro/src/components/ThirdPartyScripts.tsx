/**
 * ThirdPartyScripts - 第三方脚本管理器
 * 统一管理页面中所有第三方脚本的加载策略
 *
 * 功能：
 * 1. 集中管理第三方脚本配置
 * 2. 根据网络状态自动降级
 * 3. 支持按路由条件加载
 * 4. 弱网络/离线时自动跳过非必要脚本
 *
 * 使用示例:
 * ```tsx
 * // 在 Layout 中添加
 * <ThirdPartyScripts
 *   scripts={[
 *     {
 *       name: 'analytics',
 *       src: 'https://www.googletagmanager.com/gtag/js?id=XXX',
 *       strategy: 'lazyOnload',
 *       required: false
 *     },
 *     {
 *       name: 'chat-widget',
 *       src: '/chat-widget.js',
 *       strategy: 'lazyOnload',
 *       required: false
 *     }
 *   ]}
 * />
 * ```
 */

'use client';

import {memo, useMemo} from 'react';
import {type AsyncScriptOptions, useAsyncScript} from '@/lib/hooks/useAsyncScript';
import {useNetworkState} from '@/lib/hooks/useNetworkState';

interface ScriptConfig extends Omit<AsyncScriptOptions, 'onLoad' | 'onError'> {
  /** 脚本名称，用于标识 */
  name: string;
  /** 是否必需（必需脚本即使在弱网络下也会尝试加载）*/
  required?: boolean;
  /** 仅在当前路由匹配时才加载 */
  routes?: string[];
}

const ThirdPartyScripts = memo(({scripts}: { scripts: ScriptConfig[] }) => {
  const network = useNetworkState();
  const currentRoute = typeof window !== 'undefined'
    ? window.location.pathname
    : '/';

  const filteredScripts = useMemo(() => {
    return scripts.filter(script => {
      // 检查路由条件
      if (script.routes?.length) {
        const match = script.routes.some(route =>
          currentRoute.startsWith(route) || currentRoute === route
        );
        if (!match) return false;
      }
      return true;
    });
  }, [scripts, currentRoute]);

  const handlers = useMemo(() => {
    return filteredScripts.map(script => {
      const {name, ...options} = script;
      const opts: AsyncScriptOptions = {
        ...options,
        skipOnSlowNetwork: script.required ? false : (options.skipOnSlowNetwork ?? true),
        id: `script-${name}`
      };

      return useAsyncScript(opts);
    });
  }, [filteredScripts]);

  const total = filteredScripts.length;
  const loaded = handlers.filter(h => h.loaded).length;
  const errors = handlers.filter(h => h.error).length;

  return (
    <>
      {/* 脚本状态调试 - 仅在开发环境显示 */}
      {import.meta.env.DEV && total > 0 && (
        <div className="fixed bottom-2 left-2 z-50 text-xs text-gray-500 dark:text-gray-400">
          Scripts: {loaded}/{total} loaded {errors > 0 && `(${errors} errors)`}
        </div>
      )}

      {/* 网络状态日志 */}
      {import.meta.env.DEV && (network.isSlow || !network.isOnline) && (
        <div
          className="fixed bottom-2 right-2 z-50 text-xs px-1 rounded bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
          {network.isSlow ? 'Slow network' : 'Offline'} - scripts skipped
        </div>
      )}
    </>
  );
});

ThirdPartyScripts.displayName = 'ThirdPartyScripts';

/**
 * 常用的第三方脚本预设配置
 */
export const PRESETS = {
  /** Google Analytics */
  analytics: (trackingId: string): Omit<ScriptConfig, 'src'> => ({
    name: 'analytics',
    src: `https://www.googletagmanager.com/gtag/js?id=${trackingId}`,
    strategy: 'lazyOnload',
    required: false
  }),

  /** Chart.js */
  chartJs: (): ScriptConfig => ({
    name: 'chart-js',
    src: 'https://cdn.jsdelivr.net/npm/chart.js',
    strategy: 'lazyOnload',
    required: false
  }),

  /** Three.js (已内置，通常不需要外部加载) */
  threeJs: (): ScriptConfig => ({
    name: 'three-js',
    src: 'https://cdn.jsdelivr.net/npm/three@0.185/build/three.min.js',
    strategy: 'worker',
    required: false
  }),
};

export default ThirdPartyScripts;
