/**
 * 性能监控模块 - Performance Monitor
 * 支持 Chrome DevTools, Lighthouse, React Profiler 等工具
 */

import {useEffect, useState} from 'react';

// ─── Types ───

interface LayoutShiftEntry extends PerformanceEntry {
  hadRecentInput: boolean;
  value: number;
}

export interface WebVitalEntry {
  id: string;
  name: 'LCP' | 'INP' | 'CLS' | 'FCP' | 'TTFB';
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  entries: PerformanceEntry[];
}

// ─── Performance Mark/Measure ───

export function perfMark(name: string): void {
  if (typeof performance !== 'undefined' && performance.mark) {
    performance.mark(name);
  }
}

export function perfMeasure(name: string, startMark: string, endMark: string): DOMHighResTimeStamp {
  if (typeof performance !== 'undefined' && performance.measure) {
    performance.measure(name, startMark, endMark);
    const entry = performance.getEntriesByName(name)[0];
    return entry?.duration ?? 0;
  }
  return 0;
}

export function perfClear(name?: string): void {
  if (typeof performance === 'undefined') return;
  if (name) {
    performance.clearMarks(name);
    performance.clearMeasures(name);
  } else {
    performance.clearMarks();
    performance.clearMeasures();
  }
}

// ─── Rating Helper ───

function getRating(value: number, good: number, poor: number): 'good' | 'needs-improvement' | 'poor' {
  if (value <= good) return 'good';
  if (value <= poor) return 'needs-improvement';
  return 'poor';
}

// ─── LCP Observer ───

export function observeLCP(onReport: (vital: WebVitalEntry) => void): (() => void) {
  if (typeof performance === 'undefined') return () => {
  };

  let lastEntry: PerformanceEntry | null = null;
  let reported = false;

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'largest-contentful-paint') {
        lastEntry = entry;
      }
    }
    if (lastEntry && !reported) {
      reported = true;
      onReport({
        id: 'LCP', name: 'LCP',
        value: lastEntry.startTime,
        rating: getRating(lastEntry.startTime, 2500, 4000),
        delta: lastEntry.startTime,
        entries: [lastEntry],
      });
    }
  });

  observer.observe({type: 'largest-contentful-paint', buffered: true});
  return () => observer.disconnect();
}

// ─── INP Observer ──

export function observeINP(onReport: (vital: WebVitalEntry) => void): (() => void) {
  if (typeof performance === 'undefined') return () => {
  };

  let maxValue = 0;
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      const interactionId = (entry as any).interactionId;
      if (interactionId) {
        const latency = entry.duration;
        if (latency > maxValue) maxValue = latency;
      }
    }
  });

  try {
    observer.observe({type: 'event', buffered: true, durationThreshold: [0, 16, 100, 250, 500, 1000, 2500]});
  } catch {
    observer.observe({type: 'first-input', buffered: true});
  }

  const handlePageHide = () => {
    if (maxValue > 0) {
      onReport({
        id: 'INP', name: 'INP',
        value: maxValue,
        rating: getRating(maxValue, 200, 500),
        delta: maxValue,
        entries: [],
      });
    }
  };

  window.addEventListener('pagehide', handlePageHide);
  return () => {
    observer.disconnect();
    window.removeEventListener('pagehide', handlePageHide);
  };
}

// ─── CLS Observer ───

export function observeCLS(onReport: (vital: WebVitalEntry) => void): (() => void) {
  if (typeof performance === 'undefined') return () => {
  };

  let clsValue = 0;
  const entries: PerformanceEntry[] = [];

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      const shift = entry as LayoutShiftEntry;
      if (!shift.hadRecentInput) {
        clsValue += shift.value;
        entries.push(entry);
        onReport({
          id: 'CLS', name: 'CLS',
          value: clsValue,
          rating: getRating(clsValue, 0.1, 0.25),
          delta: shift.value,
          entries: [...entries],
        });
      }
    }
  });

  observer.observe({type: 'layout-shift', buffered: true});
  return () => observer.disconnect();
}

// ─── FCP Observer ───

export function observeFCP(onReport: (vital: WebVitalEntry) => void): (() => void) {
  if (typeof performance === 'undefined') return () => {
  };

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'paint' && entry.name === 'first-contentful-paint') {
        onReport({
          id: 'FCP', name: 'FCP',
          value: entry.startTime,
          rating: getRating(entry.startTime, 1800, 3000),
          delta: entry.startTime,
          entries: [entry],
        });
      }
    }
  });

  observer.observe({type: 'paint', buffered: true});
  return () => observer.disconnect();
}

// ─── TTFB Observer ───

export function observeTTFB(onReport: (vital: WebVitalEntry) => void): (() => void) {
  if (typeof performance === 'undefined') return () => {
  };

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'navigation') {
        const nav = entry as PerformanceNavigationTiming;
        onReport({
          id: 'TTFB', name: 'TTFB',
          value: nav.responseStart,
          rating: getRating(nav.responseStart, 800, 1800),
          delta: nav.responseStart,
          entries: [entry],
        });
      }
    }
  });

  observer.observe({type: 'navigation', buffered: true});
  return () => observer.disconnect();
}

// ─── React Profiler Integration ──

export const profilerOnRender = (
  id: string,
  phase: 'mount' | 'update' | 'nested-update',
  actualDuration: number,
  baseDuration: number,
) => {
  if (import.meta.env.DEV) {
    const selfTime = actualDuration - baseDuration;
    console.log(
      `%c[Profiler] %c${id} %c${phase}%c | Self: ${selfTime.toFixed(2)}ms | Base: ${baseDuration.toFixed(2)}ms`,
      'color: #7c3aed; font-weight: bold',
      'color: #0f172a; font-weight: bold',
      'color: #64748b',
      'color: #64748b',
    );
    if (typeof performance !== 'undefined') {
      performance.mark(`${id}:${phase}`);
    }
  }
};

// ─── Performance Report ───

export function getPerformanceReport(): {
  navigation: PerformanceNavigationTiming | null;
  resources: PerformanceResourceTiming[];
  entries: PerformanceEntry[];
  memory: { usedJSHeapSize: number; totalJSHeapSize: number } | null;
} {
  const report: any = {navigation: null, resources: [], entries: [], memory: null};

  if (typeof performance === 'undefined') return report;

  const navEntries = performance.getEntriesByType('navigation');
  if (navEntries.length > 0) report.navigation = navEntries[0] as PerformanceNavigationTiming;

  report.resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
  report.entries = performance.getEntries();

  const mem = (performance as any).memory;
  if (mem) {
    report.memory = {usedJSHeapSize: mem.usedJSHeapSize, totalJSHeapSize: mem.totalJSHeapSize};
  }

  return report;
}

// ─── Web Vitals Hook ───

export interface WebVitalsState {
  lcp: number;
  inp: number;
  cls: number;
  fcp: number;
  ttfb: number;
}

export function useWebVitals(): WebVitalsState {
  const [vitals, setVitals] = useState<WebVitalsState>({
    lcp: 0, inp: 0, cls: 0, fcp: 0, ttfb: 0,
  });

  useEffect(() => {
    const disconnects: (() => void)[] = [];

    const update = (key: keyof WebVitalsState, value: number) => {
      setVitals(prev => ({...prev, [key]: value}));
    };

    disconnects.push(observeLCP(v => update('lcp', v.value)));
    disconnects.push(observeINP(v => update('inp', v.value)));
    disconnects.push(observeFCP(v => update('fcp', v.value)));
    disconnects.push(observeTTFB(v => update('ttfb', v.value)));

    if (typeof performance !== 'undefined') {
      let clsVal = 0;
      const clsObs = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const shift = entry as LayoutShiftEntry;
          if (!shift.hadRecentInput) {
            clsVal += shift.value;
            update('cls', clsVal);
          }
        }
      });
      clsObs.observe({type: 'layout-shift', buffered: true});
      disconnects.push(() => clsObs.disconnect());
    }

    return () => disconnects.forEach(d => d());
  }, []);

  return vitals;
}

// ─── Route Timer Hook ───

export function useRouteTimer(routeName: string): () => void {
  useEffect(() => {
    perfMark(`route:${routeName}:start`);
  }, [routeName]);

  return () => {
    perfMark(`route:${routeName}:end`);
    const duration = perfMeasure(`route:${routeName}`, `route:${routeName}:start`, `route:${routeName}:end`);
    if (import.meta.env.DEV && duration > 100) {
      console.warn(`[RouteTimer] ${routeName} took ${duration.toFixed(2)}ms`);
    }
  };
}

// ─── API Timing Wrapper ───

export function withPerfTiming<T extends any[]>(
  name: string,
  fn: (...args: T) => Promise<any>
): (...args: T) => Promise<any> {
  return async (...args: T) => {
    perfMark(`${name}:start`);
    try {
      const result = await fn(...args);
      perfMark(`${name}:end`);
      const duration = perfMeasure(`${name}`, `${name}:start`, `${name}:end`);
      if (import.meta.env.DEV && duration > 500) {
        console.warn(`[API] ${name} took ${duration.toFixed(2)}ms`);
      }
      return result;
    } catch (error) {
      perfMark(`${name}:error`);
      perfMeasure(`${name}:error`, `${name}:start`, `${name}:error`);
      throw error;
    }
  };
}
