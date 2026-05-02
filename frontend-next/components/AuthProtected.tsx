'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import LoadingState from '@/components/LoadingState';

interface AuthProtectedProps {
    children: React.ReactNode;
}

export function AuthProtected({children}: AuthProtectedProps) {
    const router = useRouter();
    const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

    useEffect(() => {
        // 检查用户是否已登录
        const checkAuth = () => {
            const token = localStorage.getItem('access_token');

            if (!token) {
                // 未登录，重定向到登录页
                const currentPath = window.location.pathname + window.location.search;
                router.push(`/login?next=${encodeURIComponent(currentPath)}`);
                return;
            }

            // 已登录
            setIsAuthenticated(true);
        };

        checkAuth();
    }, [router]);

    // 正在检查认证状态
    if (isAuthenticated === null) {
        return <LoadingState message="验证身份中..."/>;
    }

    // 未认证，显示加载中（即将重定向）
    if (!isAuthenticated) {
        return <LoadingState message="重定向到登录页..."/>;
    }

    // 已认证，渲染子组件
    return <>{children}</>;
}
