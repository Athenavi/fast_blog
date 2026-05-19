'use client';

import {useEffect} from 'react';
import {useLocale} from 'next-intl';
import {applyRTLToDocument, getRTLClass} from '@/lib/rtl-utils';
import '@/styles/rtl.css';

/**
 * RTL 布局提供者
 *
 * 自动应用 RTL 样式到整个应用
 */
export default function RTLProvider({
                                        children,
                                    }: {
    children: React.ReactNode;
}) {
    const locale = useLocale();

    useEffect(() => {
        // 应用 RTL 到 document
        applyRTLToDocument(locale as any);
    }, [locale]);

    return (
        <div className={locale === 'ar' || locale === 'he' ? 'rtl' : 'ltr'}>
            {children}
        </div>
    );
}

/**
 * RTL 感知的容器组件
 */
export function RTLContainer({
                                 children,
                                 className = '',
                             }: {
    children: React.ReactNode;
    className?: string;
}) {
    const locale = useLocale();
    const isRTL = locale === 'ar' || locale === 'he';

    return (
        <div
            className={`${className} ${isRTL ? 'rtl' : 'ltr'}`}
            dir={isRTL ? 'rtl' : 'ltr'}
        >
            {children}
        </div>
    );
}

/**
 * RTL 感知的 Flex 布局
 */
export function RTLFlex({
                            children,
                            className = '',
                            direction = 'row',
                            gap = '4',
                        }: {
    children: React.ReactNode;
    className?: string;
    direction?: 'row' | 'row-reverse' | 'column' | 'column-reverse';
    gap?: string;
}) {
    const locale = useLocale();
    const isRTL = locale === 'ar' || locale === 'he';

    // 在 RTL 模式下反转 row 方向
    const finalDirection = isRTL && direction === 'row' ? 'row-reverse' : direction;

    return (
        <div
            className={`flex flex-${finalDirection} gap-${gap} ${className}`}
            dir={isRTL ? 'rtl' : 'ltr'}
        >
            {children}
        </div>
    );
}

/**
 * RTL 感知的间距组件
 */
export function RTLSpace({
                             children,
                             className = '',
                             size = '4',
                         }: {
    children: React.ReactNode;
    className?: string;
    size?: string;
}) {
    const locale = useLocale();
    const isRTL = locale === 'ar' || locale === 'he';

    // RTL 模式下使用 margin-right 代替 margin-left
    const marginClass = isRTL ? `mr-${size}` : `ml-${size}`;

    return (
        <div className={`${marginClass} ${className}`} dir={isRTL ? 'rtl' : 'ltr'}>
            {children}
        </div>
    );
}

/**
 * RTL 感知的图标组件
 */
export function RTLIcon({
                            icon: Icon,
                            className = '',
                            shouldFlip = false,
                        }: {
    icon: React.ElementType;
    className?: string;
    shouldFlip?: boolean;
}) {
    const locale = useLocale();
    const isRTL = locale === 'ar' || locale === 'he';

    const flipClass = shouldFlip && isRTL ? 'rtl-icon-flip' : '';

    return (
        <Icon className={`${className} ${flipClass}`}/>
    );
}
