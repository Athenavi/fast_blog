'use client';

import React from 'react';
import {Button} from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select';
import {Trash2, CheckSquare, Square, X} from 'lucide-react';

interface BatchActionsToolbarProps {
    selectedCount: number;
    totalCount: number;
    isAllSelected: boolean;
    onSelectAll: () => void;
    onDeselectAll: () => void;
    onDelete: () => void;
    onStatusChange?: (status: string) => void;
    onCategoryChange?: (categoryId: string) => void;
    categories?: Array<{id: number; name: string}>;
    loading?: boolean;
}

/**
 * 批量操作工具栏组件
 */
const BatchActionsToolbar: React.FC<BatchActionsToolbarProps> = ({
                                                                     selectedCount,
                                                                     totalCount,
                                                                     isAllSelected,
                                                                     onSelectAll,
                                                                     onDeselectAll,
                                                                     onDelete,
                                                                     onStatusChange,
                                                                     onCategoryChange,
                                                                     categories,
                                                                     loading = false
                                                                 }) => {
    if (selectedCount === 0) {
        return null;
    }

    const handleDelete = () => {
        if (window.confirm(`确定要删除选中的 ${selectedCount} 个项目吗?此操作不可恢复。`)) {
            onDelete();
        }
    };

    return (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
                {/* 左侧:选择信息 */}
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        已选择 <strong className="text-blue-600 dark:text-blue-400">{selectedCount}</strong> / {totalCount} 项
                    </span>
                    
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={isAllSelected ? onDeselectAll : onSelectAll}
                        className="text-blue-600 hover:text-blue-700 dark:text-blue-400"
                    >
                        {isAllSelected ? (
                            <>
                                <X className="w-4 h-4 mr-1"/>
                                取消全选
                            </>
                        ) : (
                            <>
                                <CheckSquare className="w-4 h-4 mr-1"/>
                                全选
                            </>
                        )}
                    </Button>
                </div>

                {/* 右侧:批量操作按钮 */}
                <div className="flex items-center gap-2 flex-wrap">
                    {/* 批量修改状态 */}
                    {onStatusChange && (
                        <Select onValueChange={onStatusChange}>
                            <SelectTrigger className="w-[140px] h-9">
                                <SelectValue placeholder="修改状态"/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="published">发布</SelectItem>
                                <SelectItem value="draft">草稿</SelectItem>
                                <SelectItem value="hidden">隐藏</SelectItem>
                            </SelectContent>
                        </Select>
                    )}

                    {/* 批量分配分类 */}
                    {onCategoryChange && categories && categories.length > 0 && (
                        <Select onValueChange={onCategoryChange}>
                            <SelectTrigger className="w-[140px] h-9">
                                <SelectValue placeholder="分配分类"/>
                            </SelectTrigger>
                            <SelectContent>
                                {categories.map(category => (
                                    <SelectItem key={category.id} value={String(category.id)}>
                                        {category.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}

                    {/* 批量删除 */}
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleDelete}
                        disabled={loading}
                    >
                        <Trash2 className="w-4 h-4 mr-1"/>
                        删除选中
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default BatchActionsToolbar;
