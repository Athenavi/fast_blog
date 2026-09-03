/**
 * PerfDashboard - 性能监控仪表盘
 * 集成 LCP/CLS/INP/FCP/TTFB 等 Web Vitals 指标
 * 仅在开发环境下显示，生产环境不渲染
 *
 * 使用方式:
 * ```tsx
 * // 在根布局或 App 中挂载
 * <PerfDashboard />
 * ```
 */

'use client';

import {useCallback, useEffect, useMemo, useState} from 'react';
import {
  type EventTimingEntry,
  getPerformanceReport,
  type LongTaskEntry,
  observeEventTiming,
  observeLongTasks,
  observeSlowResources,
  type SlowResource,
  useWebVitals,
} from '@/lib/perf-monitor';
import {type LeakReport, useMemoryLeakDetection} from '@/lib/hooks/useMemoryLeakDetection';

interface DashboardState {
  longTasks: LongTaskEntry[];
  eventTimings: EventTimingEntry[];
  slowResources: SlowResource[];
  memory: LeakReport;
  visible: boolean;
}

export const PerfDashboard: React.FC<{
  /** 是否始终显示（默认仅在 DEV） */
  forceVisible?: boolean;
}> = ({forceVisible = false}) => {
  const isDev = import.meta.env.DEV || forceVisible;
  if (!isDev) return null;

  const [state, setState] = useState<DashboardState>({
    longTasks: [],
    eventTimings: [],
    slowResources: [],
    memory: {
      memoryGrowing: false,
      currentUsedHeap: 0,
      peakUsedHeap: 0,
      snapshots: [],
      leakedTimers: [],
      leakedListeners: [],
      uncleanedEffects: [],
    },
    visible: false,
  });

  const webVitals = useWebVitals();

  // 内存泄漏检测（每10秒采样）
  const memoryReport = useMemoryLeakDetection({
    interval: 10000,
    threshold: 30,
    trackComponents: true,
    trackTimers: true,
    trackListeners: false,
    maxSnapshots: 10,
  });

  // 长任务检测
  useEffect(() => {
    const disconnect = observeLongTasks(
      (task) => {
        setState((prev) => ({
          ...prev,
          longTasks: [...prev.longTasks.slice(-20), task],
        }));
      },
      50
    );
    const disconnectTiming = observeEventTiming(
      (event) => {
        setState((prev) => ({
          ...prev,
          eventTimings: [...prev.eventTimings.slice(-20), event],
        }));
      },
      100
    );
    const disconnectSlow = observeSlowResources(
      (resource) => {
        setState((prev) => ({
          ...prev,
          slowResources: [...prev.slowResources.slice(-10), resource],
        }));
      },
      2000
    );

    return () => {
      disconnect();
      disconnectTiming();
      disconnectSlow();
    };
  }, []);

  // 同步内存报告
  useEffect(() => {
    setState((prev) => ({...prev, memory: memoryReport}));
  }, [memoryReport]);

  // 快捷键切换可见性（Ctrl+Shift+P）
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        setState((prev) => ({...prev, visible: !prev.visible}));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const ratingColor = useCallback((rating: string) => {
    switch (rating) {
      case 'good':
        return '#22c55e';
      case 'needs-improvement':
        return '#f59e0b';
      case 'poor':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  }, []);

  const formatBytes = useCallback((bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  }, []);

  const perfReport = useMemo(() => getPerformanceReport(), []);

  if (!state.visible) {
    return (
      <div
        title="按 Ctrl+Shift+P 打开性能面板"
        className="fixed bottom-4 right-4 z-50 w-8 h-8 bg-slate-800/60 hover:bg-slate-700 rounded-full cursor-pointer flex items-center justify-center text-xs text-slate-400 transition-colors"
        onClick={() => setState((prev) => ({...prev, visible: true}))}
      >
        ⚡
      </div>
    );
  }

  return (
    <div
      className="fixed bottom-4 right-4 z-50 w-[480px] max-h-[80vh] bg-slate-900/95 backdrop-blur-sm border border-slate-700 rounded-xl shadow-2xl text-sm text-slate-300 overflow-hidden font-mono">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <span className="font-bold text-slate-100">⚡ 性能监控面板</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Ctrl+Shift+P</span>
          <button
            onClick={() => setState((prev) => ({...prev, visible: false}))}
            className="text-slate-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="overflow-y-auto max-h-[calc(80vh-40px)] p-4 space-y-4">
        {/* Web Vitals */}
        <section>
          <h3 className="font-bold text-slate-100 mb-2">Web Vitals</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <VitalRow label="LCP" value={webVitals.lcp} color={ratingColor(getRating(webVitals.lcp, 2500, 4000))}/>
            <VitalRow label="INP" value={webVitals.inp} color={ratingColor(getRating(webVitals.inp, 200, 500))}/>
            <VitalRow label="CLS" value={`${webVitals.cls.toFixed(3)}`}
                      color={ratingColor(getRating(webVitals.cls, 0.1, 0.25))}/>
            <VitalRow label="FCP" value={webVitals.fcp} color={ratingColor(getRating(webVitals.fcp, 1800, 3000))}/>
            <VitalRow label="TTFB" value={webVitals.ttfb} color={ratingColor(getRating(webVitals.ttfb, 800, 1800))}/>
          </div>
        </section>

        {/* 内存 */}
        <section>
          <h3 className="font-bold text-slate-100 mb-2">
            内存
            {state.memory.memoryGrowing && (
              <span className="ml-2 text-red-400 animate-pulse">⚠ 增长中</span>
            )}
          </h3>
          <div className="text-xs space-y-1">
            <div>当前: {formatBytes(state.memory.currentUsedHeap)}</div>
            <div>峰值: {formatBytes(state.memory.peakUsedHeap)}</div>
            <div>
              泄漏: 定时器 {state.memory.leakedTimers.length} |
              监听器 {state.memory.leakedListeners.length} |
              Effects {state.memory.uncleanedEffects.length}
            </div>
          </div>
        </section>

        {/* 长任务 */}
        {state.longTasks.length > 0 && (
          <section>
            <h3 className="font-bold text-amber-400 mb-2">长任务 ({state.longTasks.length})</h3>
            <div className="text-xs space-y-1 max-h-24 overflow-y-auto">
              {state.longTasks.slice(-5).map((task, i) => (
                <div key={i} className="text-amber-300/70">
                  #{task.count} | {task.value.toFixed(0)}ms
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 慢资源 */}
        {state.slowResources.length > 0 && (
          <section>
            <h3 className="font-bold text-red-400 mb-2">慢资源 ({state.slowResources.length})</h3>
            <div className="text-xs space-y-1 max-h-24 overflow-y-auto">
              {state.slowResources.slice(-5).map((res, i) => (
                <div key={i} className="text-red-300/70 truncate" title={res.url}>
                  {res.duration.toFixed(0)}ms | {formatBytes(res.transferSize)}
                  <br/>
                  <span className="text-red-500/50">{res.name.split('/').pop()}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 导航信息 */}
        {perfReport.navigation && (
          <section>
            <h3 className="font-bold text-slate-100 mb-2">导航信息</h3>
            <div className="text-xs grid grid-cols-2 gap-1 text-slate-400">
              <span>DT: {perfReport.navigation.domInteractive.toFixed(0)}ms</span>
              <span>DL: {perfReport.navigation.domContentLoadedEventEnd.toFixed(0)}ms</span>
              <span>Load: {perfReport.navigation.loadEventEnd.toFixed(0)}ms</span>
              <span>资源: {perfReport.resources.length}</span>
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

function VitalRow({label, value, color}: { label: string; value: number | string; color: string }) {
  return (
    <div className="flex items-center justify-between px-2 py-1 rounded bg-slate-800/50">
      <span className="text-slate-400">{label}</span>
      <span style={{color}}>
        {typeof value === 'number' ? `${value.toFixed(0)}ms` : value}
      </span>
    </div>
  );
}

function getRating(value: number, good: number, poor: number): 'good' | 'needs-improvement' | 'poor' {
  if (value <= good) return 'good';
  if (value <= poor) return 'needs-improvement';
  return 'poor';
}

export default PerfDashboard;
