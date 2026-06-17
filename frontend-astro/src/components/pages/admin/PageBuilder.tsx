/**
 * PageBuilder — 页面构建器入口组件
 *
 * 职责：组装三栏布局 + 组件库浮层，挂载 Provider / Guards / Wrappers。
 * 所有状态和 API 逻辑委托给 usePageBuilder Hook。
 */
import React, {useCallback} from 'react';
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
                    {/* 三栏布局 */}
                    <div className="flex gap-5 flex-1 min-h-0">
                        {/* 左侧：页面列表 */}
                        <PageListPanel
                            pages={ctx.pages}
                            isLoading={ctx.pagesLoading}
                            selectedPage={ctx.selectedPage}
                            onSelectPage={ctx.handleSelectPage}
                            onDeletePage={ctx.handleDeletePage}
                            onCreatePage={ctx.handleCreatePage}
                        />

                        {/* 中间：块编辑工作区 */}
                        <BlockWorkspace
                            editingBlocks={ctx.editingBlocks}
                            selectedPage={ctx.selectedPage}
                            onDragEnd={ctx.handleDragEnd}
                            onDeleteBlock={ctx.handleDeleteBlock}
                            onBlockDataChange={ctx.handleBlockDataChange}
                            onBlockStylesChange={ctx.handleBlockStylesChange}
                            onOpenLibrary={() => ctx.setShowComponentLibrary(true)}
                            onSave={ctx.handleSave}
                            onPublish={ctx.handlePublish}
                            isSaving={ctx.isSaving}
                            isPublishing={ctx.isPublishing}
                        />

                        {/* 右侧：实时预览 */}
                        <PreviewPane
                            blocks={ctx.editingBlocks}
                            previewDevice={ctx.previewDevice}
                            onChangeDevice={ctx.setPreviewDevice}
                        />
                    </div>
                </div>

                {/* 组件库浮层 */}
                {ctx.showComponentLibrary && (
                    <ComponentLibrary
                        items={ctx.libraryItems}
                        onSelectTemplate={handleSelectTemplate}
                        onSelectComponent={handleSelectComponent}
                        onClose={() => ctx.setShowComponentLibrary(false)}
                    />
                )}
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
