/**
 * BlockWorkspace — 块编辑工作区（dnd-kit 拖拽排序 + 块卡片列表）
 */
import React from 'react';
import {
    DndContext,
    PointerSensor,
    useSensor,
    useSensors,
    closestCenter,
    DragOverlay,
} from '@dnd-kit/core';
import {
    SortableContext,
    verticalListSortingStrategy,
    useSortable,
} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {Plus, Undo2, Redo2, ExternalLink} from 'lucide-react';
import BlockCard from './BlockCard';

interface Props {
    editingBlocks: any[];
    selectedPage: { title: string } | null;
    onDragEnd: (event: any) => void;
    onDeleteBlock: (index: number) => void;
    onCopyBlock: (index: number) => void;
    onBlockDataChange: (index: number, data: any) => void;
    onBlockStylesChange: (index: number, styles: any) => void;
    onOpenLibrary: () => void;
    onSave: () => void;
    onPublish: () => void;
    onUndo: () => void;
    onRedo: () => void;
    isSaving: boolean;
    isPublishing: boolean;
    isDirty: boolean;
    canUndo: boolean;
    canRedo: boolean;
}

export function SortableBlock({
                                  block,
                                  index,
                                  onDelete,
                                  onCopy,
                                  onDataChange,
                                  onStylesChange,
                              }: {
    block: any;
    index: number;
    onDelete: (index: number) => void;
    onCopy: (index: number) => void;
    onDataChange: (index: number, data: any) => void;
    onStylesChange: (index: number, styles: any) => void;
}) {
    const {attributes, listeners, setNodeRef, transform, transition, isDragging} = useSortable({id: index});
    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
    };

    return (
        <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
            <BlockCard block={block} index={index}
                       onDelete={onDelete}
                       onCopy={onCopy}
                       onDataChange={onDataChange}
                       onStylesChange={onStylesChange}/>
        </div>
    );
}

export default function BlockWorkspace({
                                           editingBlocks,
                                           selectedPage,
                                           onDragEnd,
                                           onDeleteBlock,
                                           onCopyBlock,
                                           onBlockDataChange,
                                           onBlockStylesChange,
                                           onOpenLibrary,
                                           onSave,
                                           onPublish,
                                           onUndo,
                                           onRedo,
                                           isSaving,
                                           isPublishing,
                                           isDirty,
                                           canUndo,
                                           canRedo,
                                       }: Props) {
    const sensors = useSensors(
        useSensor(PointerSensor, {activationConstraint: {distance: 8}}),
    );

    if (!selectedPage) {
        return (
            <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
                <div className="text-center space-y-3">
                    <div className="text-4xl">📄</div>
                    <p className="text-sm">从左侧选择一个页面开始编辑</p>
                    <p className="text-xs opacity-60">快捷键: Ctrl+S 保存 · Ctrl+Z 撤销</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col min-w-0">
            {/* 工具栏 */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-t-xl">
                <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm truncate max-w-[200px]">{selectedPage.title}</h3>
                    {isDirty && <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="有未保存的修改"/>}
                </div>
                <div className="flex items-center gap-1.5">
                    {/* 撤销/重做 */}
                    <button onClick={onUndo} disabled={!canUndo}
                            className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
                            title="撤销 (Ctrl+Z)">
                        <Undo2 className="w-3.5 h-3.5"/>
                    </button>
                    <button onClick={onRedo} disabled={!canRedo}
                            className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
                            title="重做 (Ctrl+Shift+Z)">
                        <Redo2 className="w-3.5 h-3.5"/>
                    </button>

                    <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1"/>

                    {/* 查看已发布页面 */}
                    {'is_published' in selectedPage && (selectedPage as any).is_published && (
                        <a href={`/p/${(selectedPage as any).slug}`} target="_blank" rel="noopener noreferrer"
                           className="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition"
                           title="查看已发布页面 (新窗口)">
                            <ExternalLink className="w-3.5 h-3.5"/>
                        </a>
                    )}

                    <button onClick={onSave} disabled={!isDirty || isSaving}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                                isDirty
                                    ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-500/25'
                                    : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-default'
                            }`}>
                        {isSaving ? '保存中...' : '保存'}
                    </button>
                    <button onClick={onPublish} disabled={isPublishing}
                            className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition">
                        {isPublishing ? '发布中...' : '发布'}
                    </button>
                    <button onClick={onOpenLibrary}
                            className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition">
                        <Plus className="w-3.5 h-3.5 inline mr-1"/>组件
                    </button>
                </div>
            </div>

            {/* 块列表 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {editingBlocks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
                        <div className="text-5xl mb-4">🧩</div>
                        <p className="text-sm mb-1">此页面还没有内容块</p>
                        <p className="text-xs mb-4">点击「组件」按钮从组件库添加，或试试这些：</p>
                        <div className="flex gap-2">
                            {[
                                {label: 'Hero 区域', item: null},
                                {label: '特性网格', item: null},
                                {label: 'CTA', item: null},
                            ].map(({label}) => (
                                <button key={label} onClick={onOpenLibrary}
                                        className="px-3 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-400 hover:text-blue-600 transition">
                                    + {label}
                                </button>
                            ))}
                        </div>
                        <p className="text-xs text-gray-300 dark:text-gray-600 mt-4">
                            Ctrl+S 保存 · Ctrl+Z 撤销 · Ctrl+Shift+Z 重做
                        </p>
                    </div>
                ) : (
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
                        <SortableContext items={editingBlocks.map((_, i) => i)} strategy={verticalListSortingStrategy}>
                            <div className="space-y-3">
                                {editingBlocks.map((block, index) => (
                                    <SortableBlock key={index} block={block} index={index}
                                                   onDelete={onDeleteBlock}
                                                   onCopy={onCopyBlock}
                                                   onDataChange={onBlockDataChange}
                                                   onStylesChange={onBlockStylesChange}/>
                                ))}
                            </div>
                        </SortableContext>
                        <DragOverlay>
                            {/* 拖拽时的幽灵占位 */}
                        </DragOverlay>
                    </DndContext>
                )}
            </div>
        </div>
    );
}
