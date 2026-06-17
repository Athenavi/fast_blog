/**
 * usePageBuilder — 页面构建器的核心逻辑 Hook
 *
 * 统一管理页面列表、块编辑、拖拽排序、保存/发布等状态和操作。
 */
import {useState, useCallback, useRef, useEffect} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {arrayMove} from '@dnd-kit/sortable';
import type {PageData, LibraryItem, PreviewDevice} from '../types';

export function usePageBuilder() {
    const toast = useToast();
    const qc = useQueryClient();
    const [selectedPage, setSelectedPage] = useState<PageData | null>(null);
    const [editingBlocks, setEditingBlocks] = useState<any[]>([]);
    const [showComponentLibrary, setShowComponentLibrary] = useState(false);
    const [previewDevice, setPreviewDevice] = useState<PreviewDevice>('desktop');

    // 自动保存 debounce ref
    const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // ── API 查询 ──

    const {data: pages = [], isLoading: pagesLoading} = useQuery<PageData[]>({
        queryKey: ['page-builder-pages'],
        queryFn: async () => {
            const res = await apiClient.get('/cms/page-builder/pages');
            return res.data ?? [];
        },
    });

    const {data: libraryItems = []} = useQuery<LibraryItem[]>({
        queryKey: ['component-templates'],
        queryFn: async () => {
            const res = await apiClient.get('/cms/components/templates');
            return res.data ?? [];
        },
    });

    // ── 页面 CRUD ──

    const createPage = useMutation({
        mutationFn: async (data: { title: string; slug: string }) => {
            const res = await apiClient.post('/cms/page-builder/pages', {
                ...data, blocks_data: [], is_published: false,
            });
            if (!res.success) throw new Error(res.error || res.detail || '创建失败');
            return res.data as PageData;
        },
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            toast.success('页面已创建');
        },
        onError: (err: any) => toast.error(err?.message || String(err)),
    });

    const savePage = useMutation({
        mutationFn: async ({id, blocks}: { id: number; blocks: any[] }) => {
            const res = await apiClient.put(`/cms/page-builder/pages/${id}`, {blocks_data: blocks});
            if (!res.success) throw new Error(res.error || res.detail || '保存失败');
            return res.data as PageData;
        },
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            toast.success('已保存');
        },
        onError: (err: any) => toast.error(err?.message || String(err)),
    });

    const publishPage = useMutation({
        mutationFn: async (id: number) => {
            const res = await apiClient.post(`/cms/page-builder/pages/${id}/publish`);
            if (!res.success) throw new Error(res.error || res.detail || '发布失败');
        },
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            toast.success('已发布');
        },
        onError: (err: any) => toast.error(err?.message || String(err)),
    });

    const deletePage = useMutation({
        mutationFn: async (id: number) => {
            const res = await apiClient.delete(`/cms/page-builder/pages/${id}`);
            if (!res.success) throw new Error(res.error || res.detail || '删除失败');
        },
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            setSelectedPage(null);
            toast.success('已删除');
        },
        onError: (err: any) => toast.error(err?.message || String(err)),
    });

    // ── 页面操作 ──

    const handleCreatePage = useCallback(() => {
        const title = prompt('页面标题:');
        if (!title) return;
        let slug = title.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        if (!slug) slug = 'page';
        slug += '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        createPage.mutate({title, slug});
    }, [createPage]);

    const handleSelectPage = useCallback((page: PageData) => {
        setSelectedPage(page);
        setEditingBlocks(page.blocks_data || []);
    }, []);

    const handleDeletePage = useCallback((page: PageData) => {
        if (confirm(`确定删除页面「${page.title}」吗？`)) {
            deletePage.mutate(page.id);
        }
    }, [deletePage]);

    // ── 块操作 ──

    const handleAddComponent = useCallback((item: LibraryItem) => {
        const block = item.blocks?.[0] || {};
        setEditingBlocks(prev => [...prev, {
            type: block.type || item.name || 'unknown',
            data: block.props || {},
            styles: {},
        }]);
        setShowComponentLibrary(false);
    }, []);

    const handleCreateFromTemplate = useCallback(async (item: LibraryItem) => {
        const title = item.title || item.name || '新页面';
        let slug = title.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        if (!slug) slug = 'page';
        slug += '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        try {
            await apiClient.post('/cms/page-builder/pages', {
                title, slug, blocks_data: item.blocks || [], is_published: false,
            });
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            setShowComponentLibrary(false);
            toast.success('模板页面创建成功');
        } catch (error: any) {
            toast.error('创建失败：' + (error?.response?.data?.detail || '未知错误'));
        }
    }, [qc, toast]);

    const handleDeleteBlock = useCallback((index: number) => {
        setEditingBlocks(prev => prev.filter((_, i) => i !== index));
    }, []);

    const handleBlockDataChange = useCallback((index: number, data: any) => {
        setEditingBlocks(prev => prev.map((b, i) => (i === index ? {...b, data} : b)));
    }, []);

    const handleBlockStylesChange = useCallback((index: number, styles: any) => {
        setEditingBlocks(prev => prev.map((b, i) => (i === index ? {...b, styles} : b)));
    }, []);

    // dnd-kit 拖拽排序
    const handleDragEnd = useCallback((event: any) => {
        const {active, over} = event;
        if (over && active.id !== over.id) {
            setEditingBlocks(prev => arrayMove(prev, active.id, over.id));
        }
    }, []);

    // ── 保存/发布 ──

    const handleSave = useCallback(() => {
        if (!selectedPage) return;
        savePage.mutate({id: selectedPage.id, blocks: editingBlocks});
    }, [selectedPage, editingBlocks, savePage]);

    const handlePublish = useCallback(async () => {
        if (!selectedPage) return;
        await savePage.mutateAsync({id: selectedPage.id, blocks: editingBlocks});
        publishPage.mutate(selectedPage.id);
    }, [selectedPage, editingBlocks, savePage, publishPage]);

    // 自动保存（页面切换时触发）
    const saveIfDirty = useCallback(() => {
        if (!selectedPage) return;
        savePage.mutate({id: selectedPage.id, blocks: editingBlocks});
    }, [selectedPage, editingBlocks, savePage]);

    // ── 导出 ──

    return {
        // 数据
        pages,
        pagesLoading,
        libraryItems,
        selectedPage,
        editingBlocks,
        showComponentLibrary,
        previewDevice,

        // 页面操作
        setShowComponentLibrary,
        setPreviewDevice,
        handleCreatePage,
        handleSelectPage,
        handleDeletePage,

        // 块操作
        handleAddComponent,
        handleCreateFromTemplate,
        handleDeleteBlock,
        handleBlockDataChange,
        handleBlockStylesChange,
        handleDragEnd,

        // 保存/发布
        handleSave,
        handlePublish,
        saveIfDirty,

        // 加载状态
        isSaving: savePage.isPending,
        isPublishing: publishPage.isPending,
        isCreating: createPage.isPending,
    };
}
