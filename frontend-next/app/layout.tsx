import type {Metadata} from 'next';
import '../globals.css';
import '../styles/rtl.css';
import {getDirection} from '@/i18n';
import {ThemeProvider} from '@/components/ThemeProvider';

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
      <html lang={defaultLocale} dir={direction}>
    <head>
        {/* Load runtime config */}
        <script src="/config.js"/>
    </head>
      <body className="antialiased">
      <ThemeProvider>
          {children}
      </ThemeProvider>
        {/* PWA Service Worker Registration */}
        <script
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
        />
      </body>
    </html>
  );
}