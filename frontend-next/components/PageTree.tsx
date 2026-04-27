'use client';

import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, FileText, Plus, Trash2 } from 'lucide-react';

interface PageNode {
  id: number;
  title: string;
  slug: string;
  parent_id?: number | null;
  children?: PageNode[];
  order_index?: number;
}

interface PageTreeProps {
  pages: PageNode[];
  expandedIds?: number[];
  onExpand?: (pageId: number) => void;
  onSelect?: (pageId: number) => void;
  selectedId?: number | null;
  onAddChild?: (parentId: number) => void;
  onDelete?: (pageId: number) => void;
  className?: string;
}

/**
 * 页面树形结构组件
 * 
 * @example
 * ```tsx
 * <PageTree
 *   pages={pages}
 *   onSelect={(id) => setSelectedPage(id)}
 *   selectedId={selectedPage}
 * />
 * ```
 */
const PageTree: React.FC<PageTreeProps> = ({
  pages,
  expandedIds: controlledExpandedIds,
  onExpand,
  onSelect,
  selectedId,
  onAddChild,
  onDelete,
  className = ''
}) => {
  const [internalExpandedIds, setInternalExpandedIds] = useState<number[]>([]);
  
  const expandedIds = controlledExpandedIds || internalExpandedIds;

  // 构建树形结构
  const buildTree = (items: PageNode[], parentId: number | null = null): PageNode[] => {
    return items
      .filter(item => item.parent_id === parentId)
      .sort((a, b) => (a.order_index || 0) - (b.order_index || 0))
      .map(item => ({
        ...item,
        children: buildTree(items, item.id)
      }));
  };

  const tree = buildTree(pages);

  const handleToggle = (pageId: number) => {
    if (onExpand) {
      onExpand(pageId);
    } else {
      setInternalExpandedIds(prev =>
        prev.includes(pageId)
          ? prev.filter(id => id !== pageId)
          : [...prev, pageId]
      );
    }
  };

  const isExpanded = (pageId: number) => expandedIds.includes(pageId);

  const renderNode = (node: PageNode, level: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isSelected = selectedId === node.id;
    const paddingLeft = level * 24 + 12;

    return (
      <div key={node.id}>
        <div
          className={`flex items-center gap-2 py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors ${
            isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
          }`}
          style={{ paddingLeft: `${paddingLeft}px` }}
          onClick={() => onSelect?.(node.id)}
        >
          {/* 展开/折叠按钮 */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleToggle(node.id);
              }}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
            >
              {isExpanded(node.id) ? (
                <ChevronDown className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              )}
            </button>
          ) : (
            <div className="w-6"></div>
          )}

          {/* 图标 */}
          {hasChildren ? (
            <Folder className="w-4 h-4 text-yellow-500" />
          ) : (
            <FileText className="w-4 h-4 text-blue-500" />
          )}

          {/* 标题 */}
          <span className={`flex-1 text-sm ${isSelected ? 'font-medium text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}`}>
            {node.title}
          </span>

          {/* 操作按钮 */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {onAddChild && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddChild(node.id);
                }}
                className="p-1 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                title="添加子页面"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            )}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(node.id);
                }}
                className="p-1 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                title="删除页面"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* 子节点 */}
        {hasChildren && isExpanded(node.id) && (
          <div className="border-l-2 border-gray-200 dark:border-gray-700 ml-6">
            {node.children!.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (tree.length === 0) {
    return (
      <div className={`p-8 text-center text-gray-500 dark:text-gray-400 ${className}`}>
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>暂无页面</p>
      </div>
    );
  }

  return (
    <div className={`border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 overflow-hidden ${className}`}>
      {tree.map(node => (
        <div key={node.id} className="group">
          {renderNode(node)}
        </div>
      ))}
    </div>
  );
};

export default PageTree;
