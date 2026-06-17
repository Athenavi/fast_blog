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
} from '@dnd-kit/core';
import {
    SortableContext,
    verticalListSortingStrategy,
    useSortable,
} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {Plus} from 'lucide-react';
import BlockCard from './BlockCard';

interface Props {
    editingBlocks: any[];
    selectedPage: { title: string } | null;
    onDragEnd: (event: any) => void;
    onDeleteBlock: (index: number) => void;
    onBlockDataChange: (index: number, data: any) => void;
    onBlockStylesChange: (index: number, styles: any) => void;
    onOpenLibrary: () => void;
    onSave: () => void;
    onPublish: () => void;
    isSaving: boolean;
    isPublishing: boolean;
}

export function SortableBlock({
                                  block,
                                  index,
                                  onDelete,
                                  onDataChange,
                                  onStylesChange,
                              }: {
    block: any;
    index: number;
    onDelete: (index: number) => void;
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
                                           onBlockDataChange,
                                           onBlockStylesChange,
                                           onOpenLibrary,
                                           onSave,
                                           onPublish,
                                           isSaving,
                                           isPublishing,
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
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col min-w-0">
            {/* 工具栏 */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-t-xl">
                <div>
                    <h3 className="font-semibold text-sm truncate max-w-[240px]">{selectedPage.title}</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={() => onSave()}
                            disabled={isSaving}
                            className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition">
                        {isSaving ? '保存中...' : '保存'}
                    </button>
                    <button onClick={() => onPublish()}
                            disabled={isPublishing}
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
                        <p className="text-xs">点击「组件」按钮从组件库添加</p>
                    </div>
                ) : (
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
                        <SortableContext items={editingBlocks.map((_, i) => i)} strategy={verticalListSortingStrategy}>
                            <div className="space-y-3">
                                {editingBlocks.map((block, index) => (
                                    <SortableBlock key={index} block={block} index={index}
                                                   onDelete={onDeleteBlock}
                                                   onDataChange={onBlockDataChange}
                                                   onStylesChange={onBlockStylesChange}/>
                                ))}
                            </div>
                        </SortableContext>
                    </DndContext>
                )}
            </div>
        </div>
    );
}
