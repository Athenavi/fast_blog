'use client';

import {useState, useCallback} from 'react';

/**
 * 批量操作Hook
 * 提供选择、全选、反选等批量操作功能
 */
export function useBatchOperations<T extends {id: number | string}>(items: T[]) {
    const [selectedIds, setSelectedIds] = useState<Set<number | string>>(new Set());

    // 切换单个项目选中状态
    const toggleSelect = useCallback((id: number | string) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) {
                newSet.delete(id);
            } else {
                newSet.add(id);
            }
            return newSet;
        });
    }, []);

    // 全选
    const selectAll = useCallback(() => {
        setSelectedIds(new Set(items.map(item => item.id)));
    }, [items]);

    // 取消全选
    const deselectAll = useCallback(() => {
        setSelectedIds(new Set());
    }, []);

    // 反选
    const toggleSelectAll = useCallback(() => {
        if (selectedIds.size === items.length) {
            deselectAll();
        } else {
            selectAll();
        }
    }, [selectedIds.size, items.length, selectAll, deselectAll]);

    // 检查是否全选
    const isAllSelected = items.length > 0 && selectedIds.size === items.length;

    // 检查是否部分选中
    const isPartiallySelected = selectedIds.size > 0 && selectedIds.size < items.length;

    // 获取选中的项目
    const getSelectedItems = useCallback(() => {
        return items.filter(item => selectedIds.has(item.id));
    }, [items, selectedIds]);

    // 清除选择
    const clearSelection = useCallback(() => {
        setSelectedIds(new Set());
    }, []);

    // 批量删除指定ID
    const removeSelected = useCallback((ids: number | string | Array<number | string>) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev);
            const idsToRemove = Array.isArray(ids) ? ids : [ids];
            idsToRemove.forEach(id => newSet.delete(id));
            return newSet;
        });
    }, []);

    return {
        selectedIds,
        toggleSelect,
        selectAll,
        deselectAll,
        toggleSelectAll,
        isAllSelected,
        isPartiallySelected,
        getSelectedItems,
        clearSelection,
        removeSelected,
        selectedCount: selectedIds.size
    };
}
