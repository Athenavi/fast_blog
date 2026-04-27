'use client';

import React, { useState } from 'react';
import { Check, X, Trash2, Download, Upload, MoreHorizontal } from 'lucide-react';

interface BulkAction {
  id: string;
  label: string;
  icon?: React.ReactNode;
  confirm?: boolean;
  confirmMessage?: string;
}

interface BulkActionsProps {
  actions: BulkAction[];
  selectedCount: number;
  onAction: (actionId: string) => void | Promise<void>;
  onSelectAll?: () => void;
  onDeselectAll?: () => void;
  className?: string;
}

/**
 * 批量操作组件
 * 
 * @example
 * ```tsx
 * <BulkActions
 *   actions={[
 *     { id: 'publish', label: '发布', confirm: true },
 *     { id: 'delete', label: '删除', icon: <Trash2 />, confirm: true, confirmMessage: '确定要删除选中的项目吗？' }
 *   ]}
 *   selectedCount={5}
 *   onAction={(actionId) => handleAction(actionId)}
 * />
 * ```
 */
const BulkActions: React.FC<BulkActionsProps> = ({
  actions,
  selectedCount,
  onAction,
  onSelectAll,
  onDeselectAll,
  className = ''
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirm, setShowConfirm] = useState<string | null>(null);

  if (selectedCount === 0) {
    return null;
  }

  const handleActionClick = async (action: BulkAction) => {
    if (action.confirm && !showConfirm) {
      setShowConfirm(action.id);
      return;
    }

    setIsProcessing(true);
    try {
      await onAction(action.id);
      setShowConfirm(null);
    } catch (error) {
      console.error('Bulk action failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirm = () => {
    if (showConfirm) {
      const action = actions.find(a => a.id === showConfirm);
      if (action) {
        handleActionClick(action);
      }
    }
  };

  const handleCancel = () => {
    setShowConfirm(null);
  };

  return (
    <div className={`flex items-center gap-3 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg ${className}`}>
      {/* 选中数量显示 */}
      <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
        已选择 {selectedCount} 项
      </span>

      {/* 全选/取消全选 */}
      <div className="flex items-center gap-2">
        {onSelectAll && (
          <button
            onClick={onSelectAll}
            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 transition-colors"
          >
            全选
          </button>
        )}
        {onDeselectAll && (
          <button
            onClick={onDeselectAll}
            className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            取消选择
          </button>
        )}
      </div>

      {/* 分隔线 */}
      <div className="w-px h-4 bg-blue-200 dark:bg-blue-700"></div>

      {/* 批量操作按钮 */}
      <div className="flex items-center gap-2">
        {actions.map((action) => (
          <React.Fragment key={action.id}>
            {showConfirm === action.id ? (
              // 确认对话框
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {action.confirmMessage || `确定要${action.label}吗？`}
                </span>
                <button
                  onClick={handleConfirm}
                  disabled={isProcessing}
                  className="p-1.5 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                  title="确认"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={handleCancel}
                  disabled={isProcessing}
                  className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  title="取消"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              // 操作按钮
              <button
                onClick={() => handleActionClick(action)}
                disabled={isProcessing}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                  isProcessing
                    ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600'
                }`}
              >
                {action.icon}
                {action.label}
              </button>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* 加载指示器 */}
      {isProcessing && (
        <div className="ml-2">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
        </div>
      )}
    </div>
  );
};

export default BulkActions;
