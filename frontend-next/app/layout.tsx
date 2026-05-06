import type {Metadata} from 'next';
import Script from 'next/script';
import '../globals.css';
import '../styles/rtl.css';
import {getDirection} from '@/i18n';
import Navbar from '@/components/Navbar';
import ThemeProvider from '@/components/ThemeProvider';
// import {PerformanceReportTrigger} from '@/components/PerformanceMonitor'; // 暂时保持注释

export const metadata: Metadata = {
  title: 'FastBlog',
  description: 'A modern blog platform',
  manifest: '/manifest.json',
    other: {
        // 添加自定义元数据
    }
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
        {/* Scripts will be loaded via next/script in body */}
    </head>
    <body className="antialiased" suppressHydrationWarning>
    <ThemeProvider>
        <Navbar/>
        {children}
    </ThemeProvider>

    {/* Initialize theme only - removed config.js to avoid HMR issues */}
    <Script id="theme-init" strategy="beforeInteractive">
            {`
            (function() {
              try {
                function getThemeFromCookie() {
                  var cookies = document.cookie.split(';');
                  for (var i = 0; i < cookies.length; i++) {
                    var cookie = cookies[i].trim();
                    if (cookie.startsWith('theme=')) {
                      return cookie.substring('theme='.length);
                    }
                  }
                  return null;
                }
                
                var theme = getThemeFromCookie();
                if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                }
              } catch (e) {}
            })();
          `}
    </Script>
    {/* <PerformanceReportTrigger/> */}
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
      </body>
    </html>
  );
}