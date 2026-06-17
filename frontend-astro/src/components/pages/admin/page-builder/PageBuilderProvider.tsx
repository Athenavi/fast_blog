/**
 * PageBuilderProvider — 页面构建器的 Context Provider
 *
 * 将 usePageBuilder 的返回值注入 React Context，方便子组件消费。
 */
import React, {createContext, useContext} from 'react';
import type {PageData, LibraryItem, PreviewDevice} from './types';

interface PageBuilderContextValue {
    // 数据
    pages: PageData[];
    pagesLoading: boolean;
    libraryItems: LibraryItem[];
    selectedPage: PageData | null;
    editingBlocks: any[];
    showComponentLibrary: boolean;
    previewDevice: PreviewDevice;

    // 页面操作
    setShowComponentLibrary: (v: boolean) => void;
    setPreviewDevice: (v: PreviewDevice) => void;
    handleCreatePage: () => void;
    handleSelectPage: (page: PageData) => void;
    handleDeletePage: (page: PageData) => void;

    // 块操作
    handleAddComponent: (item: LibraryItem) => void;
    handleCreateFromTemplate: (item: LibraryItem) => void;
    handleDeleteBlock: (index: number) => void;
    handleBlockDataChange: (index: number, data: any) => void;
    handleBlockStylesChange: (index: number, styles: any) => void;
    handleDragEnd: (event: any) => void;

    // 保存/发布
    handleSave: () => void;
    handlePublish: () => void;
    isSaving: boolean;
    isPublishing: boolean;
    isCreating: boolean;
}

const Ctx = createContext<PageBuilderContextValue | null>(null);

export function usePageBuilderContext(): PageBuilderContextValue {
    const ctx = useContext(Ctx);
    if (!ctx) throw new Error('usePageBuilderContext must be used within PageBuilderProvider');
    return ctx;
}

interface ProviderProps {
    value: PageBuilderContextValue;
    children: React.ReactNode;
}

export function PageBuilderProvider({value, children}: ProviderProps) {
    return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
