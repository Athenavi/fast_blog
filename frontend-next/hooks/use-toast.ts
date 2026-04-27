/**
 * Toast notification hook
 * 提供简单的 toast 通知功能
 */

'use client';

import {useCallback, useState} from 'react';

export interface Toast {
    id: string;
    message: string;
    type?: 'success' | 'error' | 'warning' | 'info';
    duration?: number;
}

export function useToast() {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((message: string, type: Toast['type'] = 'info', duration: number = 3000) => {
        const id = Math.random().toString(36).substr(2, 9);
        const newToast: Toast = {id, message, type, duration};

        setToasts(prev => [...prev, newToast]);

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }

        return id;
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const success = useCallback((message: string, duration?: number) => {
        return addToast(message, 'success', duration);
    }, [addToast]);

    const error = useCallback((message: string, duration?: number) => {
        return addToast(message, 'error', duration);
    }, [addToast]);

    const warning = useCallback((message: string, duration?: number) => {
        return addToast(message, 'warning', duration);
    }, [addToast]);

    const info = useCallback((message: string, duration?: number) => {
        return addToast(message, 'info', duration);
    }, [addToast]);

    // 兼容旧的 toast() API
    const toast = useCallback((options: {
        title: string;
        description?: string;
        variant?: 'default' | 'destructive'
    }) => {
        const message = options.description ? `${options.title}: ${options.description}` : options.title;
        const type = options.variant === 'destructive' ? 'error' : 'success';
        return addToast(message, type);
    }, [addToast]);

    return {
        toasts,
        addToast,
        removeToast,
        success,
        error,
        warning,
        info,
        toast,
    };
}

export default useToast;
