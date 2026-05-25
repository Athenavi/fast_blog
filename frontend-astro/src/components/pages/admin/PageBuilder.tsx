import React, {useState, useEffect} from 'react';
import AdminShell from '@/components/layouts/AdminShell';
import AuthGuard from '@/components/auth/AuthGuard';
import QueryProvider from '@/components/providers/QueryProvider';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import {
    Layout, Plus, Save, Eye, Trash2, Edit3, MoveUp, MoveDown,
    Type, Image as ImageIcon, Video, Grid, Star, MessageSquare,
    DollarSign, HelpCircle, Users, Mail
} from 'lucide-react';

interface PageData {
    id: number;
    title: string;
    slug: string;
    blocks_data: any[];
    template_name?: string;
    is_published: boolean;
    created_at?: string;
    updated_at?: string;
}

interface ComponentTemplate {
    name: string;
    category: string;
    description: string;
    preview_html: string;
    default_data: any;
}

const COMPONENT_ICONS: Record<string, any> = {
    'hero-section': Star,
    'features-grid': Grid,
    'cta-section': MessageSquare,
    'testimonials': Users,
    'pricing-table': DollarSign,
    'faq-section': HelpCircle,
    'team-members': Users,
    'contact-form': Mail
};

function PageBuilderInner() {
    const qc = useQueryClient();
    const [selectedPage, setSelectedPage] = useState<PageData | null>(null);
    const [editingBlocks, setEditingBlocks] = useState<any[]>([]);
    const [showComponentLibrary, setShowComponentLibrary] = useState(false);
    const [previewMode, setPreviewMode] = useState(false);

    // 查询页面列表
    const {data: pages, isLoading: pagesLoading} = useQuery({
        queryKey: ['page-builder-pages'],
        queryFn: async () => {
            const res = await apiClient.get('/page-builder/pages');
            return res.data || [];
        }
    });

    // 查询组件模板
    const {data: components} = useQuery({
        queryKey: ['component-templates'],
        queryFn: async () => {
            const res = await apiClient.get('/components/templates');
            return res.data || [];
        }
    });

    // 创建页面
    const createPageMut = useMutation({
        mutationFn: (data: { title: string; slug: string }) =>
            apiClient.post('/page-builder/pages', {
                ...data,
                blocks_data: [],
                is_published: false
            }),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
        }
    });

    // 保存页面
    const savePageMut = useMutation({
        mutationFn: ({id, blocks}: { id: number; blocks: any[] }) =>
            apiClient.put(`/page-builder/pages/${id}`, {blocks_data: blocks}),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            alert('页面已保存！');
        }
    });

    // 发布页面
    const publishMut = useMutation({
        mutationFn: (id: number) => apiClient.post(`/page-builder/pages/${id}/publish`),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            alert('页面已发布！');
        }
    });

    // 删除页面
    const deleteMut = useMutation({
        mutationFn: (id: number) => apiClient.delete(`/page-builder/pages/${id}`),
        onSuccess: () => {
            qc.invalidateQueries({queryKey: ['page-builder-pages']});
            setSelectedPage(null);
        }
    });

    const handleCreatePage = () => {
        const title = prompt('页面标题:');
        if (!title) return;

        const slug = title.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        createPageMut.mutate({title, slug});
    };

    const handleEditPage = (page: PageData) => {
        setSelectedPage(page);
        setEditingBlocks(page.blocks_data || []);
        setPreviewMode(false);
    };

    const handleAddComponent = (component: ComponentTemplate) => {
        setEditingBlocks([...editingBlocks, {
            type: component.name,
            data: component.default_data
        }]);
        setShowComponentLibrary(false);
    };

    const handleMoveBlock = (index: number, direction: 'up' | 'down') => {
        const newBlocks = [...editingBlocks];
        const newIndex = direction === 'up' ? index - 1 : index + 1;
        if (newIndex < 0 || newIndex >= newBlocks.length) return;

        [newBlocks[index], newBlocks[newIndex]] = [newBlocks[newIndex], newBlocks[index]];
        setEditingBlocks(newBlocks);
    };

    const handleDeleteBlock = (index: number) => {
        setEditingBlocks(editingBlocks.filter((_, i) => i !== index));
    };

    const handleSave = () => {
        if (!selectedPage) return;
        savePageMut.mutate({id: selectedPage.id, blocks: editingBlocks});
    };

    const handlePublish = () => {
        if (!selectedPage) return;
        handleSave();
        setTimeout(() => publishMut.mutate(selectedPage.id), 500);
    };

    return (
        <AdminShell title="页面构建器">
            <div className="flex gap-6 h-[calc(100vh-200px)]">
                {/* 左侧：页面列表 */}
                <div className="w-64 bg-white dark:bg-gray-900 rounded-xl border overflow-hidden flex flex-col">
                    <div className="px-4 py-3 border-b flex items-center justify-between">
                        <h3 className="font-semibold text-sm">页面列表</h3>
                        <button
                            onClick={handleCreatePage}
                            className="p-1.5 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-600 rounded-lg transition"
                            title="新建页面"
                        >
                            <Plus className="w-4 h-4"/>
                        </button>
                    </div>

                    {pagesLoading ? (
                        <div className="p-4 text-center text-sm text-gray-400">加载中...</div>
                    ) : !pages?.length ? (
                        <div className="p-4 text-center text-sm text-gray-400">暂无页面</div>
                    ) : (
                        <div className="flex-1 overflow-y-auto divide-y">
                            {pages.map((page: PageData) => (
                                <div
                                    key={page.id}
                                    onClick={() => handleEditPage(page)}
                                    className={`px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition ${
                                        selectedPage?.id === page.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                    }`}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-sm font-medium truncate">{page.title}</span>
                                        {page.is_published && (
                                            <span
                                                className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-700 rounded">已发布</span>
                                        )}
                                    </div>
                                    <div className="text-xs text-gray-400 font-mono truncate">/{page.slug}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 中间：编辑器 */}
                <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border overflow-hidden flex flex-col">
                    {!selectedPage ? (
                        <div className="flex-1 flex items-center justify-center text-gray-400">
                            <div className="text-center">
                                <Layout className="w-16 h-16 mx-auto mb-4 opacity-30"/>
                                <p>选择一个页面开始编辑</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* 工具栏 */}
                            <div className="px-4 py-3 border-b flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <h3 className="font-semibold">{selectedPage.title}</h3>
                                    <span className="text-xs text-gray-400 font-mono">/{selectedPage.slug}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setPreviewMode(!previewMode)}
                                        className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-1.5"
                                    >
                                        <Eye className="w-4 h-4"/>
                                        {previewMode ? '编辑' : '预览'}
                                    </button>
                                    <button
                                        onClick={() => setShowComponentLibrary(true)}
                                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-1.5"
                                    >
                                        <Plus className="w-4 h-4"/>
                                        添加组件
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        disabled={savePageMut.isPending}
                                        className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-1.5"
                                    >
                                        <Save className="w-4 h-4"/>
                                        保存
                                    </button>
                                    <button
                                        onClick={handlePublish}
                                        disabled={!selectedPage || publishMut.isPending}
                                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                                    >
                                        发布
                                    </button>
                                </div>
                            </div>

                            {/* 编辑区域 */}
                            <div className="flex-1 overflow-y-auto p-6">
                                {previewMode ? (
                                    <div className="max-w-4xl mx-auto space-y-6">
                                        {editingBlocks.map((block, index) => (
                                            <div key={index} className="border rounded-lg p-4">
                                                <div className="text-xs text-gray-400 mb-2">组件: {block.type}</div>
                                                <pre
                                                    className="text-xs bg-gray-50 dark:bg-gray-800 p-3 rounded overflow-x-auto">
                          {JSON.stringify(block.data, null, 2)}
                        </pre>
                                            </div>
                                        ))}
                                        {editingBlocks.length === 0 && (
                                            <div className="text-center py-12 text-gray-400">
                                                <p>点击"添加组件"开始构建页面</p>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="max-w-4xl mx-auto space-y-4">
                                        {editingBlocks.map((block, index) => {
                                            const Icon = COMPONENT_ICONS[block.type] || Layout;
                                            return (
                                                <div key={index}
                                                     className="border rounded-lg p-4 hover:shadow-md transition bg-white dark:bg-gray-800">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <div className="flex items-center gap-2">
                                                            <Icon className="w-4 h-4 text-blue-600"/>
                                                            <span className="text-sm font-medium">{block.type}</span>
                                                        </div>
                                                        <div className="flex items-center gap-1">
                                                            <button
                                                                onClick={() => handleMoveBlock(index, 'up')}
                                                                disabled={index === 0}
                                                                className="p-1.5 text-gray-400 hover:text-blue-600 disabled:opacity-30 transition"
                                                            >
                                                                <MoveUp className="w-4 h-4"/>
                                                            </button>
                                                            <button
                                                                onClick={() => handleMoveBlock(index, 'down')}
                                                                disabled={index === editingBlocks.length - 1}
                                                                className="p-1.5 text-gray-400 hover:text-blue-600 disabled:opacity-30 transition"
                                                            >
                                                                <MoveDown className="w-4 h-4"/>
                                                            </button>
                                                            <button
                                                                onClick={() => handleDeleteBlock(index)}
                                                                className="p-1.5 text-gray-400 hover:text-red-600 transition"
                                                            >
                                                                <Trash2 className="w-4 h-4"/>
                                                            </button>
                                                        </div>
                                                    </div>
                                                    <div className="text-xs text-gray-500">
                                                        {JSON.stringify(block.data, null, 2).slice(0, 200)}...
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        {editingBlocks.length === 0 && (
                                            <div className="text-center py-12 border-2 border-dashed rounded-lg">
                                                <Layout className="w-12 h-12 mx-auto mb-3 text-gray-300"/>
                                                <p className="text-gray-400 mb-3">拖拽或点击添加组件</p>
                                                <button
                                                    onClick={() => setShowComponentLibrary(true)}
                                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                                                >
                                                    浏览组件库
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* 组件库对话框 */}
            {showComponentLibrary && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div
                        className="bg-white dark:bg-gray-900 rounded-2xl max-w-5xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                        <div className="px-6 py-4 border-b flex items-center justify-between">
                            <h3 className="font-semibold text-lg">选择组件</h3>
                            <button
                                onClick={() => setShowComponentLibrary(false)}
                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {components?.map((comp: ComponentTemplate) => {
                                    const Icon = COMPONENT_ICONS[comp.name] || Layout;
                                    return (
                                        <div
                                            key={comp.name}
                                            onClick={() => handleAddComponent(comp)}
                                            className="border rounded-xl p-4 hover:border-blue-600 hover:shadow-md cursor-pointer transition"
                                        >
                                            <div className="flex items-center gap-2 mb-2">
                                                <Icon className="w-5 h-5 text-blue-600"/>
                                                <span className="font-medium">{comp.name}</span>
                                            </div>
                                            <p className="text-xs text-gray-500 mb-3">{comp.description}</p>
                                            <div className="text-[10px] text-gray-400">分类: {comp.category}</div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </AdminShell>
    );
}

export default function PageBuilder() {
    return (
        <AuthGuard>
            <QueryProvider>
                <PageBuilderInner/>
            </QueryProvider>
        </AuthGuard>
    );
}
