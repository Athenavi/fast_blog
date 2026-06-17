/**
 * PageBuilderProvider — 页面构建器的 Context Provider
 */
import React, {createContext, useContext} from 'react';
import type {PageData, LibraryItem, PreviewDevice} from './types';

export interface PageBuilderContextValue {
    pages: PageData[];
    pagesLoading: boolean;
    libraryItems: LibraryItem[];
    selectedPage: PageData | null;
    editingBlocks: any[];
    showComponentLibrary: boolean;
    previewDevice: PreviewDevice;
    isDirty: boolean;
    canUndo: boolean;
    canRedo: boolean;

    showNewPageDialog: boolean;
    newPageTitle: string;
    setNewPageTitle: (v: string) => void;
    setShowNewPageDialog: (v: boolean) => void;
    handleOpenNewPageDialog: () => void;
    handleConfirmNewPage: () => void;

    setShowComponentLibrary: (v: boolean) => void;
    setPreviewDevice: (v: PreviewDevice) => void;
    handleSelectPage: (page: PageData) => void;
    handleDeletePage: (page: PageData) => void;

    handleAddComponent: (item: LibraryItem) => void;
    handleCreateFromTemplate: (item: LibraryItem) => void;
    handleDeleteBlock: (index: number) => void;
    handleBlockDataChange: (index: number, data: any) => void;
    handleBlockStylesChange: (index: number, styles: any) => void;
    handleCopyBlock: (index: number) => void;
    handleDragEnd: (event: any) => void;

    handleUndo: () => void;
    handleRedo: () => void;
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
