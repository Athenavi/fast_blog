/**
 * Performance Monitor Tests
 * 测试性能监控 API 是否正确工作
 */

import {beforeEach, describe, expect, it} from 'vitest';
import {getPerformanceReport, perfClear, perfMark, perfMeasure, PerformanceTimer,} from '@/lib/perf-monitor';
import {clearPerformanceMocks, mockWebVitals, setupPerformanceMocks,} from './perf-utils';

describe('Performance Monitor', () => {
  beforeEach(() => {
    setupPerformanceMocks();
    clearPerformanceMocks();
  });

  describe('perfMark', () => {
    it('should call performance.mark', () => {
      perfMark('test-mark');
      expect(performance.mark).toHaveBeenCalledWith('test-mark');
    });
  });

  describe('perfMeasure', () => {
    it('should call performance.measure', () => {
      perfMeasure('test-measure', 'start', 'end');
      expect(performance.measure).toHaveBeenCalledWith('test-measure', 'start', 'end');
    });
  });

  describe('perfClear', () => {
    it('should clear all marks and measures when no name provided', () => {
      perfClear();
      expect(performance.clearMarks).toHaveBeenCalledWith();
      expect(performance.clearMeasures).toHaveBeenCalledWith();
    });

    it('should clear specific mark and measure', () => {
      perfClear('test');
      expect(performance.clearMarks).toHaveBeenCalledWith('test');
      expect(performance.clearMeasures).toHaveBeenCalledWith('test');
    });
  });

  describe('getPerformanceReport', () => {
    it('should return performance report', () => {
      const report = getPerformanceReport();
      expect(report).toHaveProperty('navigation');
      expect(report).toHaveProperty('resources');
      expect(report).toHaveProperty('entries');
      expect(report).toHaveProperty('memory');
    });
  });

  describe('PerformanceTimer', () => {
    it('should mark and measure time', () => {
      const timer = new PerformanceTimer();
      timer.mark('start');
      expect(performance.mark).toHaveBeenCalledWith('start');
    });

    it('should clear marks', () => {
      const timer = new PerformanceTimer();
      timer.clear();
      expect(performance.clearMarks).toHaveBeenCalled();
    });
  });

  describe('Web Vitals Mock', () => {
    it('should mock web vitals data', () => {
      mockWebVitals(2000, 100, 0.05, 1000, 500);
      const entries = performance.getEntriesByType('largest-contentful-paint');
      expect(entries).toHaveLength(1);
      expect((entries[0] as any).startTime).toBe(2000);
    });
  });
});
