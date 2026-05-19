/**
 * 性能监控组件
 * 跟踪和报告页面加载性能指标
 */

'use client';

import React, {useEffect, useState} from 'react';

interface PerformanceMetrics {
    loadTime: number;
    domContentLoaded: number;
    firstPaint: number;
    firstContentfulPaint: number;
    largestContentfulPaint?: number;
    cumulativeLayoutShift?: number;
    firstInputDelay?: number;
}

export const PerformanceMonitor: React.FC<{ enabled?: boolean }> = ({enabled = true}) => {
    const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
    const [showReport, setShowReport] = useState(false);

    // 发送性能数据到分析服务
    const sendToAnalytics = (metricsData: PerformanceMetrics) => {
        // 这里可以集成你的分析服务
        // 例如：Google Analytics, Mixpanel, 或自定义端点
        if (navigator.sendBeacon) {
            try {
                navigator.sendBeacon('/api/v2/performance/metrics', JSON.stringify(metricsData));
            } catch (e) {
                // 静默失败
            }
        }
    };

    useEffect(() => {
        if (!enabled || typeof window === 'undefined') return;

        const collectMetrics = () => {
            const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
            const paintEntries = performance.getEntriesByType('paint');

            let firstPaint = 0;
            let firstContentfulPaint = 0;

            paintEntries.forEach((entry) => {
                if (entry.name === 'first-paint') {
                    firstPaint = entry.startTime;
                } else if (entry.name === 'first-contentful-paint') {
                    firstContentfulPaint = entry.startTime;
                }
            });

            const metricsData: PerformanceMetrics = {
                loadTime: navigation.loadEventEnd - navigation.fetchStart,
                domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
                firstPaint,
                firstContentfulPaint,
            };

            // 尝试获取 LCP (Largest Contentful Paint)
            const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
            if (lcpEntries.length > 0) {
                const lastLcp = lcpEntries[lcpEntries.length - 1] as any;
                metricsData.largestContentfulPaint = lastLcp.startTime;
            }

            // 尝试获取 CLS (Cumulative Layout Shift)
            const clsEntries = performance.getEntriesByType('layout-shift');
            if (clsEntries.length > 0) {
                let totalCls = 0;
                clsEntries.forEach((entry: any) => {
                    if (!entry.hadRecentInput) {
                        totalCls += entry.value;
                    }
                });
                metricsData.cumulativeLayoutShift = totalCls;
            }

            setMetrics(metricsData);

            // 在控制台输出性能报告
            console.group('🚀 Performance Report');
            console.log(`Load Time: ${metricsData.loadTime.toFixed(2)}ms`);
            console.log(`DOM Content Loaded: ${metricsData.domContentLoaded.toFixed(2)}ms`);
            console.log(`First Paint: ${metricsData.firstPaint.toFixed(2)}ms`);
            console.log(`First Contentful Paint: ${metricsData.firstContentfulPaint.toFixed(2)}ms`);
            if (metricsData.largestContentfulPaint) {
                console.log(`Largest Contentful Paint: ${metricsData.largestContentfulPaint.toFixed(2)}ms`);
            }
            if (metricsData.cumulativeLayoutShift !== undefined) {
                console.log(`Cumulative Layout Shift: ${metricsData.cumulativeLayoutShift.toFixed(3)}`);
            }
            console.groupEnd();

            // 发送性能数据到分析服务（如果配置了）
            sendToAnalytics(metricsData);
        };

        // 等待页面完全加载后收集指标
        if (document.readyState === 'complete') {
            setTimeout(collectMetrics, 0);
        } else {
            window.addEventListener('load', collectMetrics);
            return () => window.removeEventListener('load', collectMetrics);
        }
    }, [enabled]);

    // 显示性能报告
    if (!showReport) {
        return null;
    }

    return (
        <div style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            color: 'white',
            padding: '15px',
            borderRadius: '8px',
            fontSize: '12px',
            zIndex: 9999,
            maxWidth: '300px'
        }}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px'}}>
                <strong>Performance Metrics</strong>
                <button
                    onClick={() => setShowReport(false)}
                    style={{background: 'none', border: 'none', color: 'white', cursor: 'pointer'}}
                >
                    ×
                </button>
            </div>

            {metrics ? (
                <div>
                    <div>Load: {metrics.loadTime.toFixed(0)}ms</div>
                    <div>DOM Ready: {metrics.domContentLoaded.toFixed(0)}ms</div>
                    <div>First Paint: {metrics.firstPaint.toFixed(0)}ms</div>
                    <div>FCP: {metrics.firstContentfulPaint.toFixed(0)}ms</div>
                    {metrics.largestContentfulPaint && (
                        <div>LCP: {metrics.largestContentfulPaint.toFixed(0)}ms</div>
                    )}
                    {metrics.cumulativeLayoutShift !== undefined && (
                        <div>CLS: {metrics.cumulativeLayoutShift.toFixed(3)}</div>
                    )}
                </div>
            ) : (
                <div>Collecting metrics...</div>
            )}
        </div>
    );
};

// 性能报告触发器组件
export const PerformanceReportTrigger: React.FC = () => {
    const [showReport, setShowReport] = useState(false);

    useEffect(() => {
        // 'Ctrl+Shift+P 显示性能报告
        const handleKeyPress = (e: KeyboardEvent) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                setShowReport(prev => !prev);
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        return () => window.removeEventListener('keydown', handleKeyPress);
    }, []);

    return <PerformanceMonitor enabled={showReport}/>;
};

export default PerformanceMonitor;
