/**
 * PageBuilder — 页面构建器入口组件
 *
 * 职责：组装三栏布局 + 组件库浮层 + 新建页面对话框，挂载 Provider / Guards / Wrappers。
 */
import React, {useCallback} from 'react';
import {X} from 'lucide-react';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {ToastProvider} from '@/components/ui/toast-provider';
import {AdminShell} from '@/components/admin/AdminShell';
import {usePageBuilder} from './page-builder/hooks/usePageBuilder';
import {PageBuilderProvider} from './page-builder/PageBuilderProvider';
import PageListPanel from './page-builder/components/PageListPanel';
import BlockWorkspace from './page-builder/components/BlockWorkspace';
import PreviewPane from './page-builder/components/PreviewPane';
import ComponentLibrary from './page-builder/components/ComponentLibrary';

function NewPageDialog({open, title, onTitleChange, onConfirm, onCancel, isCreating}: {
    open: boolean;
    title: string;
    onTitleChange: (v: string) => void;
    onConfirm: () => void;
    onCancel: () => void;
    isCreating: boolean;
}) {
    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
             onClick={onCancel}>
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-md w-full shadow-2xl"
                 onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold">新建页面</h3>
                    <button onClick={onCancel}
                            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition">
                        <X className="w-4 h-4"/>
                    </button>
                </div>
                <div className="mb-4">
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                        页面标题
                    </label>
                    <input type="text" value={title}
                           onChange={e => onTitleChange(e.target.value)}
                           onKeyDown={e => e.key === 'Enter' && onConfirm()}
                           placeholder="输入页面标题..."
                           className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                           autoFocus/>
                </div>
                <div className="flex justify-end gap-3">
                    <button onClick={onCancel}
                            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
                        取消
                    </button>
                    <button onClick={onConfirm} disabled={isCreating}
                            className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 rounded-xl transition-all shadow-lg shadow-blue-500/25 disabled:opacity-50">
                        {isCreating ? '创建中...' : '创建'}
                    </button>
                </div>
            </div>
        </div>
    );
}

function PageBuilderLayout() {
    const ctx = usePageBuilder();

    const handleSelectTemplate = useCallback((item: any) => {
        ctx.handleCreateFromTemplate(item);
    }, [ctx.handleCreateFromTemplate]);

    const handleSelectComponent = useCallback((item: any) => {
        ctx.handleAddComponent(item);
    }, [ctx.handleAddComponent]);

    return (
        <PageBuilderProvider value={ctx}>
            <AdminShell title="页面构建器">
                <div className="flex flex-col h-[calc(100vh-200px)] min-h-0">
                    <div className="flex gap-5 flex-1 min-h-0">
                        <PageListPanel
                            pages={ctx.pages}
                            isLoading={ctx.pagesLoading}
                            selectedPage={ctx.selectedPage}
                            onSelectPage={ctx.handleSelectPage}
                            onDeletePage={ctx.handleDeletePage}
                            onCreatePage={ctx.handleOpenNewPageDialog}
                        />
                        <BlockWorkspace
                            editingBlocks={ctx.editingBlocks}
                            selectedPage={ctx.selectedPage}
                            onDragEnd={ctx.handleDragEnd}
                            onDeleteBlock={ctx.handleDeleteBlock}
                            onCopyBlock={ctx.handleCopyBlock}
                            onBlockDataChange={ctx.handleBlockDataChange}
                            onBlockStylesChange={ctx.handleBlockStylesChange}
                            onOpenLibrary={() => ctx.setShowComponentLibrary(true)}
                            onSave={ctx.handleSave}
                            onPublish={ctx.handlePublish}
                            onUndo={ctx.handleUndo}
                            onRedo={ctx.handleRedo}
                            isSaving={ctx.isSaving}
                            isPublishing={ctx.isPublishing}
                            isDirty={ctx.isDirty}
                            canUndo={ctx.canUndo}
                            canRedo={ctx.canRedo}
                        />
                        <PreviewPane
                            blocks={ctx.editingBlocks}
                            previewDevice={ctx.previewDevice}
                            onChangeDevice={ctx.setPreviewDevice}
                        />
                    </div>
                </div>

                {ctx.showComponentLibrary && (
                    <ComponentLibrary
                        items={ctx.libraryItems}
                        onSelectTemplate={handleSelectTemplate}
                        onSelectComponent={handleSelectComponent}
                        onClose={() => ctx.setShowComponentLibrary(false)}
                    />
                )}

                <NewPageDialog
                    open={ctx.showNewPageDialog}
                    title={ctx.newPageTitle}
                    onTitleChange={ctx.setNewPageTitle}
                    onConfirm={ctx.handleConfirmNewPage}
                    onCancel={() => ctx.setShowNewPageDialog(false)}
                    isCreating={ctx.isCreating}
                />
            </AdminShell>
        </PageBuilderProvider>
    );
}

export default function PageBuilder() {
    return (
        <AuthGuard>
            <QueryProvider>
                <ToastProvider>
                    <PageBuilderLayout/>
                </ToastProvider>
            </QueryProvider>
        </AuthGuard>
    );
}
