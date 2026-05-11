import type {Metadata} from 'next';
import '../globals.css';
import '../styles/rtl.css';
import {getDirection} from '@/i18n';
import Navbar from '@/components/Navbar';
import {GlobalShortcuts} from '@/components/GlobalShortcuts';
import MobileGestures from '@/components/MobileGestures';
import MobileBottomNav from '@/components/MobileBottomNav';
import PWAInstallPrompt from '@/components/PWAInstallPrompt';

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
        <body className="antialiased" suppressHydrationWarning>
        <Navbar/>
        <GlobalShortcuts/>
        <MobileGestures/>
        {children}
        <MobileBottomNav/>
        <PWAInstallPrompt/>
        </body>
        </html>
    );
}