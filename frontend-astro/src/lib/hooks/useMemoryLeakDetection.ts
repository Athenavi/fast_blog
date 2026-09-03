/**
 * useMemoryLeakDetection - 内存泄漏检测 Hook
 *
 * 功能：
 * 1. useEffect cleanup 审计 — 检测未正确清理的副作用
 * 2. 内存占用监控 — 通过 performance.memory API 跟踪堆内存变化
 * 3. 全局事件监听器泄漏检测 — 检测未清除的 window 事件监听器
 * 4. setInterval/setTimeout 泄漏检测
 * 5. DOM 节点泄漏初步检测
 *
 * 使用方式:
 * ```tsx
 * // 全局挂载（推荐在 App 根组件）
 * const report = useMemoryLeakDetection({ interval: 30000, threshold: 50 });
 *
 * // 审计单个组件
 * useMemoryLeakDetection({ trackComponents: true });
 * ```
 */

import {useCallback, useEffect, useMemo, useRef, useState} from 'react';

// ─── Types ───

interface MemorySnapshot {
  timestamp: number;
  usedHeap: number;
  totalHeap: number;
  jsHeapLimit: number | null;
  domNodes: number;
}

interface LeakReport {
  memoryGrowing: boolean;
  currentUsedHeap: number;
  peakUsedHeap: number;
  snapshots: MemorySnapshot[];
  leakedTimers: Array<{ id: number; type: string; createdAt: number }>;
  leakedListeners: Array<{ type: string; target: string; createdAt: number }>;
  uncleanedEffects: Array<{ component: string; effect: string; mountedAt: number }>;
}

export interface UseMemoryLeakDetectionOptions {
  /** 检查间隔 (ms) */
  interval?: number;
  /** 内存增长阈值 (MB) */
  threshold?: number;
  /** 是否追踪组件级 useEffect */
  trackComponents?: boolean;
  /** 是否追踪定时器泄漏 */
  trackTimers?: boolean;
  /** 是否追踪事件监听器泄漏 */
  trackListeners?: boolean;
  /** 内存快照保留数量 */
  maxSnapshots?: number;
  /** 报告回调 */
  onLeakDetected?: (report: LeakReport) => void;
}

// ─── Global tracking stores (singleton pattern) ───

const trackedTimers = new Set<number>();
const trackedListeners = new Map<string, { type: string; target: string; createdAt: number }>();
const componentEffects = new Map<string, { component: string; effects: string[]; mountedAt: number }>();

/** 包装 setInterval 以追踪潜在泄漏 */
function trackSetInterval(handler: any, ms: number, ...args: any[]): number {
  const id = setInterval(handler, ms, ...args);
  trackedTimers.add(id);
  return id;
}

/** 包装 clearInterval 以移除追踪 */
function trackClearInterval(id: number): void {
  clearInterval(id);
  trackedTimers.delete(id);
}

/** 包装 setTimeout 以追踪潜在泄漏 */
function trackSetTimeout(handler: any, ms: number, ...args: any[]): number {
  const id = setTimeout(handler, ms, ...args);
  trackedTimers.add(id);
  return id;
}

/** 包装 clearTimeout 以移除追踪 */
function trackClearTimeout(id: number): void {
  clearTimeout(id);
  trackedTimers.delete(id);
}

/** 包装 addEventListener 以追踪潜在泄漏 */
function trackAddEventListener(
  target: Window | Document | HTMLElement,
  type: string,
  listener: EventListener,
  options?: boolean | AddEventListenerOptions
): void {
  const targetKey = getTargetKey(target);
  const key = `${targetKey}:${type}:${String(listener).slice(0, 50)}`;
  trackedListeners.set(key, {type, target: targetKey, createdAt: Date.now()});
  target.addEventListener(type, listener, options);
}

/** 包装 removeEventListener 以移除追踪 */
function trackRemoveEventListener(
  target: Window | Document | HTMLElement,
  type: string,
  listener: EventListener,
  options?: boolean | EventListenerOptions
): void {
  const targetKey = getTargetKey(target);
  const key = `${targetKey}:${type}:${String(listener).slice(0, 50)}`;
  trackedListeners.delete(key);
  target.removeEventListener(type, listener, options);
}

function getTargetKey(target: any): string {
  if (target === window) return 'window';
  if (target === document) return 'document';
  return (target as HTMLElement)?.id || `element:${(target as HTMLElement)?.tagName}`;
}

// ─── Hook ───

export function useMemoryLeakDetection(options: UseMemoryLeakDetectionOptions = {}): LeakReport {
  const {
    interval = 30000,
    threshold = 50,
    trackComponents = import.meta.env.DEV,
    trackTimers = true,
    trackListeners = true,
    maxSnapshots = 20,
    onLeakDetected,
  } = options;

  const [report, setReport] = useState<LeakReport>({
    memoryGrowing: false,
    currentUsedHeap: 0,
    peakUsedHeap: 0,
    snapshots: [],
    leakedTimers: [],
    leakedListeners: [],
    uncleanedEffects: [],
  });

  const snapshotsRef = useRef<MemorySnapshot[]>([]);
  const peakRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 注入全局追踪方法
  useEffect(() => {
    if (trackTimers && typeof window !== 'undefined') {
      (window as any).__trackSetInterval = trackSetInterval;
      (window as any).__trackClearInterval = trackClearInterval;
      (window as any).__trackSetTimeout = trackSetTimeout;
      (window as any).__trackClearTimeout = trackClearTimeout;
    }
    if (trackListeners && typeof window !== 'undefined') {
      (window as any).__trackAddEventListener = trackAddEventListener;
      (window as any).__trackRemoveEventListener = trackRemoveEventListener;
    }

    return () => {
      if (typeof window !== 'undefined') {
        delete (window as any).__trackSetInterval;
        delete (window as any).__trackClearInterval;
        delete (window as any).__trackSetTimeout;
        delete (window as any).__trackClearTimeout;
        delete (window as any).__trackAddEventListener;
        delete (window as any).__trackRemoveEventListener;
      }
    };
  }, [trackTimers, trackListeners]);

  // 组件级 useEffect 追踪
  if (trackComponents && typeof window !== 'undefined') {
    const componentName = (window as any).__currentComponentName || 'unknown';

    useEffect(() => {
      componentEffects.set(componentName, {
        component: componentName,
        effects: [],
        mountedAt: Date.now(),
      });

      return () => {
        componentEffects.delete(componentName);
      };
    }, [componentName]);
  }

  // 定时内存采样
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const takeSnapshot = (): MemorySnapshot => {
      const mem = (performance as any)?.memory;
      const domNodes = document ? document.querySelectorAll('*').length : 0;

      if (mem) {
        return {
          timestamp: Date.now(),
          usedHeap: mem.usedJSHeapSize,
          totalHeap: mem.totalJSHeapSize,
          jsHeapLimit: mem.jsHeapSizeLimit || null,
          domNodes,
        };
      }

      return {
        timestamp: Date.now(),
        usedHeap: 0,
        totalHeap: 0,
        jsHeapLimit: null,
        domNodes,
      };
    };

    const checkLeaks = () => {
      const snapshot = takeSnapshot();

      // 更新峰值
      if (snapshot.usedHeap > peakRef.current) {
        peakRef.current = snapshot.usedHeap;
      }

      // 保存快照
      const snaps = [...snapshotsRef.current, snapshot];
      if (snaps.length > maxSnapshots) {
        snaps.splice(0, snaps.length - maxSnapshots);
      }
      snapshotsRef.current = snaps;

      // 检测内存持续增长趋势
      let memoryGrowing = false;
      if (snaps.length >= 3) {
        const recent = snaps.slice(-3);
        memoryGrowing =
          recent[1].usedHeap > recent[0].usedHeap &&
          recent[2].usedHeap > recent[1].usedHeap &&
          (recent[2].usedHeap - recent[0].usedHeap) > threshold * 1024 * 1024;
      }

      // 收集泄漏的定时器
      const now = Date.now();
      const leakedTimersList: Array<{ id: number; type: string; createdAt: number }> = [];
      trackedTimers.forEach((id) => {
        leakedTimersList.push({id, type: 'timer', createdAt: now});
      });

      // 收集可能泄漏的事件监听器
      const leakedListenersList = Array.from(trackedListeners.values());

      // 收集未清理的组件 effects
      const uncleaned = Array.from(componentEffects.values())
        .filter((e) => now - e.mountedAt > interval * 10)
        .flatMap((e) =>
          e.effects.map((fx) => ({
            component: e.component,
            effect: fx,
            mountedAt: e.mountedAt,
          }))
        );

      const newReport: LeakReport = {
        memoryGrowing,
        currentUsedHeap: snapshot.usedHeap,
        peakUsedHeap: peakRef.current,
        snapshots: snaps,
        leakedTimers: leakedTimersList,
        leakedListeners: leakedListenersList,
        uncleanedEffects: uncleaned,
      };

      setReport(newReport);

      if (memoryGrowing && onLeakDetected) {
        onLeakDetected(newReport);
        if (import.meta.env.DEV) {
          console.warn(
            '%c[MemoryLeak] 内存持续增长检测到!',
            'color: #ef4444; font-weight: bold',
            newReport
          );
        }
      }
    };

    checkLeaks();
    intervalRef.current = setInterval(checkLeaks, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [interval, threshold, maxSnapshots, onLeakDetected]);

  return report;
}

// ─── 组件级 useEffect 审计 Hook ───

export function useEffectAuditor(componentName: string) {
  const effectsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    (window as any).__currentComponentName = componentName;
    return () => {
      delete (window as any).__currentComponentName;
    };
  }, [componentName]);

  return useMemo(
    () => ({
      track: useCallback((name: string) => {
        effectsRef.current.add(name);
        const comp = componentEffects.get(componentName);
        if (comp) {
          comp.effects.push(name);
        }
      }, [componentName]),

      cleanup: useCallback((name: string) => {
        effectsRef.current.delete(name);
      }, []),

      getActiveEffects: useCallback(() => {
        return Array.from(effectsRef.current);
      }, []),
    }),
    [componentName]
  );
}

// ─── 安全的 Effects 包装器 ───

export function useSafeEffect(
  componentName: string,
  effect: () => void | (() => void),
  deps: React.DependencyList
) {
  const audit = useEffectAuditor(componentName);

  useEffect(() => {
    const effectName = `${componentName}_${String(effect).slice(0, 30)}`;
    audit.track(effectName);

    const cleanup = effect();

    return () => {
      audit.cleanup(effectName);
      if (typeof cleanup === 'function') {
        cleanup();
      }
    };
  }, deps);
}

export default useMemoryLeakDetection;
