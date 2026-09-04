/**
 * Performance Testing Utilities
 * 用于测试性能监控功能
 */

import {vi} from 'vitest';

// Mock PerformanceObserver
class MockPerformanceObserver {
  callbacks: Array<(list: any) => void> = [];

  observe(options: any) {
    this.callbacks.push(() => {
    });
  }

  disconnect() {
    this.callbacks = [];
  }

  takeRecords() {
    return [];
  }
}

// Mock performance API
const mockPerformance = {
  mark: vi.fn(),
  measure: vi.fn(),
  clearMarks: vi.fn(),
  clearMeasures: vi.fn(),
  getEntriesByName: vi.fn().mockReturnValue([]),
  getEntriesByType: vi.fn().mockReturnValue([]),
  now: vi.fn().mockReturnValue(Date.now()),
  timing: {},
  memory: {
    usedJSHeapSize: 50 * 1024 * 1024,
    totalJSHeapSize: 100 * 1024 * 1024,
    jsHeapSizeLimit: 200 * 1024 * 1024,
  },
};

/**
 * Setup performance mocks for testing
 */
export function setupPerformanceMocks() {
  // @ts-ignore
  global.PerformanceObserver = MockPerformanceObserver;
  // @ts-ignore
  global.performance = mockPerformance;
}

/**
 * Clear performance mock data
 */
export function clearPerformanceMocks() {
  mockPerformance.mark.mockClear();
  mockPerformance.measure.mockClear();
  mockPerformance.clearMarks.mockClear();
  mockPerformance.clearMeasures.mockClear();
  mockPerformance.getEntriesByName.mockClear();
  mockPerformance.getEntriesByType.mockClear();
}

/**
 * Mock Web Vitals data
 */
export function mockWebVitals(lcp = 2000, inp = 100, cls = 0.05, fcp = 1000, ttfb = 500) {
  mockPerformance.getEntriesByType.mockImplementation((type) => {
    if (type === 'largest-contentful-paint') {
      return [{startTime: lcp, entryType: 'largest-contentful-paint'}];
    }
    if (type === 'paint') {
      return [{startTime: fcp, entryType: 'paint', name: 'first-contentful-paint'}];
    }
    if (type === 'navigation') {
      return [{responseStart: ttfb, entryType: 'navigation'}];
    }
    return [];
  });
}

/**
 * Create mock PerformanceEntry
 */
export function createMockPerformanceEntry(options: {
  entryType?: string;
  name?: string;
  startTime?: number;
  duration?: number;
}): PerformanceEntry {
  return {
    entryType: options.entryType || 'resource',
    name: options.name || 'mock-resource',
    startTime: options.startTime || 0,
    duration: options.duration || 0,
  } as PerformanceEntry;
}

/**
 * Create mock ResourceTiming entry
 */
export function createMockResourceTiming(options: {
  name?: string;
  startTime?: number;
  duration?: number;
  transferSize?: number;
  decodedBodySize?: number;
  initiatorType?: string;
}): PerformanceResourceTiming {
  return {
    name: options.name || 'https://example.com/resource.js',
    entryType: 'resource',
    initiatorType: options.initiatorType || 'script',
    nextHopProtocol: 'http/1.1',
    workerStart: 0,
    redirectStart: 0,
    redirectEnd: 0,
    fetchStart: 0,
    domainLookupStart: 0,
    domainLookupEnd: 0,
    connectStart: 0,
    connectEnd: 0,
    secureConnectionStart: 0,
    requestStart: 0,
    responseStart: options.startTime || 0,
    responseEnd: (options.startTime || 0) + (options.duration || 0),
    startTime: options.startTime || 0,
    Duration: 0,
    transferSize: options.transferSize || 0,
    encodedBodySize: 0,
    decodedBodySize: options.decodedBodySize || 0,
    serverTiming: [],
  } as any as PerformanceResourceTiming;
}
