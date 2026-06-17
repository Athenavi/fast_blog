/**
 * usePageBuilder — 页面构建器的核心逻辑 Hook
 *
 * 统一管理页面列表、块编辑、拖拽排序、保存/发布、撤销/重做等状态和操作。
 */
import {useState, useCallback, useRef, useEffect} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {arrayMove} from '@dnd-kit/sortable';
import type {PageData, LibraryItem, PreviewDevice} from '../types';

const MAX_UNDO = 50;

export function usePageBuilder() {
    const toast = useToast();
    const qc = useQueryClient();
    const [selectedPage, setSelectedPage] = useState<PageData | null>(null);
    const [editingBlocks, setEditingBlocks] = useState<any[]>([]);
    const [showComponentLibrary, setShowComponentLibrary] = useState(false);
    const [previewDevice, setPreviewDevice] = useState<PreviewDevice>('desktop');

    // ── 撤销/重做栈 ──
    const [undoStack, setUndoStack] = useState<any[][]>([]);
    const [redoStack, setRedoStack] = useState<any[][]>([]);

    // dirty 标记：blocks 是否未保存
    const [isDirty, setIsDirty] = useState(false);
    const savedBlocksRef = useRef<string>('');

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

    // ── dirty 追踪 ──
    useEffect(() => {
        const key = JSON.stringify(editingBlocks);
        setIsDirty(key !== savedBlocksRef.current);
    }, [editingBlocks]);

    // ── 离开提示 ──
    useEffect(() => {
        const handler = (e: BeforeUnloadEvent) => {
            if (isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        };
        window.addEventListener('beforeunload', handler);
        return () => window.removeEventListener('beforeunload', handler);
    }, [isDirty]);

    // ── 撤销/重做 ──

    const pushUndo = useCallback((blocks: any[]) => {
        setUndoStack(prev => {
            const next = [...prev, blocks];
            return next.length > MAX_UNDO ? next.slice(-MAX_UNDO) : next;
        });
        setRedoStack([]);
    }, []);

    const handleUndo = useCallback(() => {
        setUndoStack(prev => {
            if (prev.length === 0) return prev;
            const current = editingBlocks;
            const prevBlocks = prev[prev.length - 1];
            setRedoStack(r => [...r, current]);
            setEditingBlocks(prevBlocks);
            return prev.slice(0, -1);
        });
    }, [editingBlocks]);

    const handleRedo = useCallback(() => {
        setRedoStack(prev => {
            if (prev.length === 0) return prev;
            const current = editingBlocks;
            const nextBlocks = prev[prev.length - 1];
            pushUndo(current);
            setEditingBlocks(nextBlocks);
            return prev.slice(0, -1);
        });
    }, [editingBlocks, pushUndo]);

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
            savedBlocksRef.current = JSON.stringify(editingBlocks);
            setIsDirty(false);
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
            setEditingBlocks([]);
            setUndoStack([]);
            setRedoStack([]);
            toast.success('已删除');
        },
        onError: (err: any) => toast.error(err?.message || String(err)),
    });

    // ── 新建页面对话框 ──
    const [showNewPageDialog, setShowNewPageDialog] = useState(false);
    const [newPageTitle, setNewPageTitle] = useState('');

    const handleOpenNewPageDialog = useCallback(() => {
        setNewPageTitle('');
        setShowNewPageDialog(true);
    }, []);

    const handleConfirmNewPage = useCallback(() => {
        const title = newPageTitle.trim();
        if (!title) { toast.error('请输入页面标题'); return; }
        let slug = title.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        if (!slug) slug = 'page';
        slug += '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        createPage.mutate({title, slug});
        setShowNewPageDialog(false);
    }, [newPageTitle, createPage, toast]);

    // ── 页面操作 ──

    const handleSelectPage = useCallback((page: PageData) => {
        // 已选同一页不做处理
        if (selectedPage?.id === page.id) return;
        const blocks = page.blocks_data || [];
        setEditingBlocks(blocks);
        savedBlocksRef.current = JSON.stringify(blocks);
        setIsDirty(false);
        setUndoStack([]);
        setRedoStack([]);
        setSelectedPage(page);
    }, [selectedPage]);

    const handleDeletePage = useCallback((page: PageData) => {
        if (confirm(`确定删除页面「${page.title}」吗？`)) {
            deletePage.mutate(page.id);
        }
    }, [deletePage]);

    // ── 快捷键 ──

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            const ctrl = e.ctrlKey || e.metaKey;
            if (ctrl && e.key === 's') {
                e.preventDefault();
                if (selectedPage && isDirty) handleSave();
            }
            if (ctrl && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                handleUndo();
            }
            if (ctrl && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
                e.preventDefault();
                handleRedo();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    });

    // ── 块操作（带撤销栈） ──

    const blocksMutation = useCallback((fn: (prev: any[]) => any[]) => {
        setEditingBlocks(prev => {
            pushUndo(prev);
            return fn(prev);
        });
    }, [pushUndo]);

    const handleAddComponent = useCallback((item: LibraryItem) => {
        const block = item.blocks?.[0] || {};
        blocksMutation(prev => [...prev, {
            type: block.type || item.name || 'unknown',
            data: block.props || {},
            styles: {},
        }]);
        setShowComponentLibrary(false);
    }, [blocksMutation]);

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
        blocksMutation(prev => prev.filter((_, i) => i !== index));
    }, [blocksMutation]);

    const handleBlockDataChange = useCallback((index: number, data: any) => {
        blocksMutation(prev => prev.map((b, i) => (i === index ? {...b, data} : b)));
    }, [blocksMutation]);

    const handleBlockStylesChange = useCallback((index: number, styles: any) => {
        blocksMutation(prev => prev.map((b, i) => (i === index ? {...b, styles} : b)));
    }, [blocksMutation]);

    const handleCopyBlock = useCallback((index: number) => {
        blocksMutation(prev => {
            const block = {...prev[index], data: {...(prev[index].data || {})}};
            const next = [...prev];
            next.splice(index + 1, 0, block);
            return next;
        });
    }, [blocksMutation]);

    // dnd-kit 拖拽排序
    const handleDragEnd = useCallback((event: any) => {
        const {active, over} = event;
        if (over && active.id !== over.id) {
            blocksMutation(prev => arrayMove(prev, active.id, over.id));
        }
    }, [blocksMutation]);

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

    // ── 剩余撤销/重做次数 ──

    return {
        // 数据
        pages,
        pagesLoading,
        libraryItems,
        selectedPage,
        editingBlocks,
        showComponentLibrary,
        previewDevice,
        isDirty,
        canUndo: undoStack.length > 0,
        canRedo: redoStack.length > 0,

        // 新建对话框
        showNewPageDialog,
        newPageTitle,
        setNewPageTitle,
        setShowNewPageDialog,
        handleOpenNewPageDialog,
        handleConfirmNewPage,

        // 页面操作
        setShowComponentLibrary,
        setPreviewDevice,
        handleSelectPage,
        handleDeletePage,

        // 块操作
        handleAddComponent,
        handleCreateFromTemplate,
        handleDeleteBlock,
        handleBlockDataChange,
        handleBlockStylesChange,
        handleCopyBlock,
        handleDragEnd,

        // 撤销/重做
        handleUndo,
        handleRedo,

        // 保存/发布
        handleSave,
        handlePublish,

        // 加载状态
        isSaving: savePage.isPending,
        isPublishing: publishPage.isPending,
        isCreating: createPage.isPending,
    };
}
