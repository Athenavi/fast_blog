import type {Metadata} from 'next';
import Script from 'next/script';
import '../globals.css';
import '../styles/rtl.css';
import {getDirection} from '@/i18n';
import Navbar from '@/components/Navbar';
import ThemeInitializer from '@/components/ThemeInitializer';
import PerformanceOptimizer from '@/components/PerformanceOptimizer';
import {PerformanceReportTrigger} from '@/components/PerformanceMonitor';

export const metadata: Metadata = {
  title: 'FastBlog',
  description: 'A modern blog platform',
  manifest: '/manifest.json',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
    // 静态导出模式下，使用默认语言（服务端渲染时无法访问 localStorage）
    // 客户端 hydration 后会通过 LanguageSwitcher 组件更新
    const defaultLocale = 'zh-CN';
    const direction = getDirection(defaultLocale);
  
  return (
      <html lang={defaultLocale} dir={direction} suppressHydrationWarning>
    <head>
        {/* Load runtime config */}
        <Script src="/config.js" strategy="beforeInteractive"/>
        {/* 初始化主题，避免 hydration 不匹配 */}
        <Script id="theme-init" strategy="beforeInteractive">
            {`
            (function() {
              try {
                var theme = localStorage.getItem('theme');
                if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                }
              } catch (e) {}
            })();
          `}
        </Script>
    </head>
      <body className="antialiased">
      <ThemeInitializer>
          <PerformanceOptimizer enablePreload={true} enableLazyLoad={true}>
              {/* ✅ ThemeProvider 仍然导致无限刷新，完全禁用 */}
              {/* <ThemeProvider> */}
          <Navbar/>
          {children}
              {/* </ThemeProvider> */}
          </PerformanceOptimizer>
      </ThemeInitializer>
        {/* PWA Service Worker Registration */}
      {/* ✅ 临时禁用 Service Worker，测试是否导致刷新 */}
      {/* <Script
          id="sw-register"
          strategy="afterInteractive"
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                      console.log('SW registered: ', registration);
                    })
                    .catch(function(registrationError) {
                      console.log('SW registration failed: ', registrationError);
                    });
                });
              }
            `
          }}
        /> */}
      <PerformanceReportTrigger/>
      </body>
    </html>
  );
}