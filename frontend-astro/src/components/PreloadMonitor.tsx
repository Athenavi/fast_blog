/**
 * PreloadMonitor - 预加载监控组件
 * 在页面空闲时预加载关键资源，优化后续页面切换体验
 */

'use client';

import {useEffect, useRef} from 'react';

interface PreloadMonitorProps {
  preloadRoutes?: string[];
  preconnectOrigins?: string[];
  delay?: number;
}

const PreloadMonitor: React.FC<PreloadMonitorProps> = ({
                                                         preloadRoutes = ['/articles', '/categories'],
                                                         preconnectOrigins = [],
                                                         delay = 1000,
                                                       }) => {
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    preconnectOrigins.forEach(origin => {
      if (!document.querySelector(`link[ href="${origin}" ]`)) {
        const link = document.createElement('link');
        link.rel = 'preconnect';
        link.href = origin;
        document.head.appendChild(link);
      }
    });

    const schedulePreload = () => {
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(() => doPreload(), {timeout: delay});
      } else {
        setTimeout(() => doPreload(), delay);
      }
    };

    const doPreload = () => {
      const nav = navigator as any;
      const conn = nav.connection || nav.mozConnection || nav.webkitConnection;
      if (conn?.saveData || conn?.effectiveType === 'slow-2g' || conn?.effectiveType === '2g') return;
      preloadRoutes.forEach(route => {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.as = 'document';
        link.href = route;
        document.head.appendChild(link);
      });
    };

    if (document.readyState === 'complete') {
      schedulePreload();
    } else {
      window.addEventListener('load', schedulePreload, {once: true});
      return () => window.removeEventListener('load', schedulePreload);
    }
  }, [preloadRoutes, preconnectOrigins, delay]);

  return null;
};

export default PreloadMonitor;
