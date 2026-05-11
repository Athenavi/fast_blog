import {useCallback, useEffect, useRef, useState} from 'react';

interface AutoSaveOptions {
    /** 防抖延迟时间（毫秒） */
    debounceDelay?: number;
    /** 是否启用自动保存 */
    enabled?: boolean;
    /** 保存成功回调 */
    onSaveSuccess?: () => void;
    /** 保存失败回调 */
    onSaveError?: (error: Error) => void;
}

interface AutoSaveStatus {
    status: 'idle' | 'saving' | 'saved' | 'error';
    lastSaved: Date | null;
    errorMessage: string | null;
}

/**
 * 自动保存 Hook
 * 提供带防抖的自动保存功能，支持本地缓存和云端同步
 *
 * @param data - 需要保存的数据
 * @param saveFunction - 保存函数
 * @param options - 配置选项
 *
 * @example
 * ```tsx
 * const { status, lastSaved, triggerSave } = useAutoSave(
 *   formData,
 *   async (data) => await api.saveArticle(data),
 *   { debounceDelay: 2000, enabled: true }
 * );
 * ```
 */
export function useAutoSave<T extends Record<string, any>>(
    data: T,
    saveFunction: (data: T) => Promise<void>,
    options: AutoSaveOptions = {}
) {
    const {
        debounceDelay = 2000,
        enabled = true,
        onSaveSuccess,
        onSaveError,
    } = options;

    const [status, setStatus] = useState<AutoSaveStatus['status']>('idle');
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const previousDataRef = useRef<string>('');
    const isSavingRef = useRef(false);

    // 检查数据是否有变化
    const hasChanges = useCallback(() => {
        const currentData = JSON.stringify(data);
        return currentData !== previousDataRef.current;
    }, [data]);

    // 执行保存
    const executeSave = useCallback(async () => {
        if (!hasChanges() || isSavingRef.current) {
            return;
        }

        isSavingRef.current = true;
        setStatus('saving');
        setErrorMessage(null);

        try {
            await saveFunction(data);

            // 保存成功
            previousDataRef.current = JSON.stringify(data);
            setLastSaved(new Date());
            setStatus('saved');
            onSaveSuccess?.();

            // 3秒后恢复为 idle 状态
            setTimeout(() => {
                setStatus((prev) => (prev === 'saved' ? 'idle' : prev));
            }, 3000);
        } catch (error) {
            // 保存失败
            setStatus('error');
            const errorMsg = error instanceof Error ? error.message : '保存失败';
            setErrorMessage(errorMsg);
            onSaveError?.(error instanceof Error ? error : new Error(errorMsg));

            // 5秒后恢复为 idle 状态
            setTimeout(() => {
                setStatus((prev) => (prev === 'error' ? 'idle' : prev));
            }, 5000);
        } finally {
            isSavingRef.current = false;
        }
    }, [data, saveFunction, hasChanges, onSaveSuccess, onSaveError]);

    // 触发立即保存
    const triggerSave = useCallback(async () => {
        if (timerRef.current) {
            clearTimeout(timerRef.current);
            timerRef.current = null;
        }
        await executeSave();
    }, [executeSave]);

    // 设置自动保存定时器（带防抖）
    useEffect(() => {
        if (!enabled || !hasChanges()) {
            return;
        }

        // 清除之前的定时器
        if (timerRef.current) {
            clearTimeout(timerRef.current);
        }

        // 设置新的定时器
        timerRef.current = setTimeout(() => {
            executeSave();
        }, debounceDelay);

        // 清理函数
        return () => {
            if (timerRef.current) {
                clearTimeout(timerRef.current);
            }
        };
    }, [data, enabled, debounceDelay, executeSave, hasChanges]);

    // 组件卸载时清理
    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearTimeout(timerRef.current);
            }
        };
    }, []);

    return {
        status,
        lastSaved,
        errorMessage,
        triggerSave,
        hasChanges: hasChanges(),
    };
}

export default useAutoSave;
