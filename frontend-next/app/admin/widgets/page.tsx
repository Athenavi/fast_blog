/**
 * Widget管理后台 - 支持Widget配置、排序、启用/禁用
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Switch} from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import apiClient from '@/lib/api-client';
import {Eye, EyeOff, GripVertical, Plus, Save, Settings, Trash2} from 'lucide-react';
import {
    closestCenter,
    DndContext,
    DragEndEvent,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy
} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';

interface WidgetType {
    name: string;
    description: string;
    icon: string;
    category: string;
    default_config: Record<string, any>;
}

interface WidgetInstance {
    id: number;
    widget_type: string;
    area: string;
    title: string;
    config: Record<string, any>;
    order_index: number;
    is_active: boolean;
    conditions?: Record<string, any>;
    created_at: string;
    updated_at: string;
}

interface WidgetArea {
    name: string;
    description: string;
    max_widgets: number | null;
}

// 可排序的 Widget 项组件
const SortableWidgetItem = ({
    widget,
    widgetType,
    areaWidgets,
    onOpenConfig,
    onOpenPreview,
    onToggleActive,
    onDelete,
    onMoveUp,
    onMoveDown
}: {
    widget: WidgetInstance;
    widgetType: WidgetType | undefined;
    areaWidgets: WidgetInstance[];
    onOpenConfig: (w: WidgetInstance) => void;
    onOpenPreview: (w: WidgetInstance) => void;
    onToggleActive: (id: number, active: boolean) => void;
    onDelete: (id: number) => void;
    onMoveUp: (w: WidgetInstance) => void;
    onMoveDown: (w: WidgetInstance) => void;
}) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({id: widget.id});

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`flex items-center gap-3 p-3 rounded-lg border ${
                widget.is_active
                    ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                    : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 opacity-60'
            }`}
        >
            {/* 拖拽手柄 */}
            <div {...attributes} {...listeners} className="cursor-move">
                <GripVertical className="w-5 h-5 text-gray-400"/>
            </div>

            {/* Widget图标和信息 */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="text-xl">{widgetType?.icon || '📦'}</span>
                    <span className="font-medium truncate">{widget.title}</span>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                    {widgetType?.name || widget.widget_type}
                </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onOpenPreview(widget)}
                    title="预览"
                >
                    <Eye className="w-4 h-4 text-blue-600"/>
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onOpenConfig(widget)}
                    title="配置"
                >
                    <Settings className="w-4 h-4"/>
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onToggleActive(widget.id, widget.is_active)}
                    title={widget.is_active ? '禁用' : '启用'}
                >
                    {widget.is_active ? (
                        <Eye className="w-4 h-4 text-green-600"/>
                    ) : (
                        <EyeOff className="w-4 h-4 text-gray-400"/>
                    )}
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onMoveUp(widget)}
                    disabled={areaWidgets.indexOf(widget) === 0}
                    title="上移"
                >
                    ↑
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onMoveDown(widget)}
                    disabled={areaWidgets.indexOf(widget) === areaWidgets.length - 1}
                    title="下移"
                >
                    ↓
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(widget.id)}
                    title="删除"
                >
                    <Trash2 className="w-4 h-4 text-red-600"/>
                </Button>
            </div>
        </div>
    );
};

const WidgetManagement = () => {
    const [widgetTypes, setWidgetTypes] = useState<Record<string, WidgetType>>({});
    const [widgetAreas, setWidgetAreas] = useState<Record<string, WidgetArea>>({});
    const [widgets, setWidgets] = useState<WidgetInstance[]>([]);
    const [loading, setLoading] = useState(true);

    // 对话框状态
    const [showConfigDialog, setShowConfigDialog] = useState(false);
    const [showPreviewDialog, setShowPreviewDialog] = useState(false);
    const [currentWidget, setCurrentWidget] = useState<WidgetInstance | null>(null);
    const [configForm, setConfigForm] = useState<Record<string, any>>({});
    const [previewHtml, setPreviewHtml] = useState('');

    useEffect(() => {
        loadWidgetData();
    }, []);

    // 加载Widget数据
    const loadWidgetData = async () => {
        try {
            setLoading(true);

            // 获取所有区域的Widget
            const areas = ['sidebar_primary', 'sidebar_secondary', 'footer_1', 'footer_2', 'footer_3', 'header_top'];
            const allWidgets: WidgetInstance[] = [];

            for (const area of areas) {
                const response = await apiClient.get(`/api/v1/widgets/area/${area}`);
                if (response.success && response.data) {
                    const widgets = (response.data as any).widgets || [];
                    // 解析 config 字段（JSON 字符串 -> 对象）
                    const parsedWidgets = widgets.map((w: any) => ({
                        ...w,
                        config: typeof w.config === 'string' ? JSON.parse(w.config) : w.config
                    }));
                    allWidgets.push(...parsedWidgets);
                }
            }

            setWidgets(allWidgets);

            // Widget类型和区域信息从后端获取或使用默认值
            setWidgetTypes(getDefaultWidgetTypes());
            setWidgetAreas(getDefaultWidgetAreas());
        } catch (error: any) {
            console.error('Failed to load widgets:', error);
        } finally {
            setLoading(false);
        }
    };

    // 获取默认Widget类型（如果API未实现）
    const getDefaultWidgetTypes = (): Record<string, WidgetType> => ({
        recent_posts: {
            name: '最新文章',
            description: '显示最近发布的文章列表',
            icon: '📝',
            category: 'content',
            default_config: {count: 5, show_thumbnail: true, show_date: true}
        },
        categories: {
            name: '分类目录',
            description: '显示文章分类列表',
            icon: '📂',
            category: 'navigation',
            default_config: {show_count: true, hierarchical: true}
        },
        tags: {
            name: '标签云',
            description: '显示热门标签云',
            icon: '🏷️',
            category: 'navigation',
            default_config: {count: 20, display_type: 'cloud'}
        },
        search: {
            name: '搜索框',
            description: '站内搜索功能',
            icon: '🔍',
            category: 'utility',
            default_config: {placeholder: '搜索文章...'}
        },
        archives: {
            name: '文章归档',
            description: '按月份显示文章归档',
            icon: '📅',
            category: 'navigation',
            default_config: {type: 'monthly', show_count: true}
        },
        social_links: {
            name: '社交链接',
            description: '显示社交媒体链接',
            icon: '🌐',
            category: 'social',
            default_config: {platforms: ['weibo', 'wechat']}
        },
        newsletter: {
            name: '邮件订阅',
            description: '邮件订阅表单',
            icon: '📧',
            category: 'marketing',
            default_config: {button_text: '订阅'}
        },
        advertisement: {
            name: '广告位',
            description: '自定义广告内容',
            icon: '📢',
            category: 'monetization',
            default_config: {content: '', link: ''}
        },
        html: {
            name: '自定义HTML',
            description: '插入自定义HTML代码',
            icon: '💻',
            category: 'custom',
            default_config: {html_content: ''}
        },
        recent_comments: {
            name: '最新评论',
            description: '显示最近的评论',
            icon: '💬',
            category: 'content',
            default_config: {count: 5, show_avatar: true}
        },
        popular_posts: {
            name: '热门文章',
            description: '显示浏览量最高的文章',
            icon: '🔥',
            category: 'content',
            default_config: {count: 5, period: 'week'}
        }
    });

    // 获取默认Widget区域
    const getDefaultWidgetAreas = (): Record<string, WidgetArea> => ({
        sidebar_primary: {name: '主边栏', description: '网站右侧边栏', max_widgets: null},
        sidebar_secondary: {name: '次边栏', description: '网站左侧边栏', max_widgets: null},
        footer_1: {name: '页脚区域1', description: '页脚第一列', max_widgets: 5},
        footer_2: {name: '页脚区域2', description: '页脚第二列', max_widgets: 5},
        footer_3: {name: '页脚区域3', description: '页脚第三列', max_widgets: 5},
        header_top: {name: '顶部区域', description: '网站顶部横幅', max_widgets: 3}
    });

    // 打开配置对话框
    const handleOpenConfig = (widget: WidgetInstance) => {
        setCurrentWidget(widget);
        setConfigForm({...widget.config});
        setShowConfigDialog(true);
    };

    // 打开预览对话框
    const handleOpenPreview = async (widget: WidgetInstance) => {
        setCurrentWidget(widget);
        try {
            const response = await apiClient.get(`/api/v1/widgets/render/${widget.id}`);
            if (response.success && response.data) {
                setPreviewHtml((response.data as any).html || '');
                setShowPreviewDialog(true);
            }
        } catch (error: any) {
            console.error('Failed to load preview:', error);
        }
    };

    // 保存配置
    const handleSaveConfig = async () => {
        if (!currentWidget) return;

        try {
            const response = await apiClient.put(`/api/v1/widgets/${currentWidget.id}`, {
                config: configForm,
                title: currentWidget.title
            });

            if (response.success) {
                loadWidgetData();
                setShowConfigDialog(false);
            }
        } catch (error: any) {
            console.error('Failed to save config:', error);
        }
    };

    // 切换启用/禁用
    const handleToggleActive = async (widgetId: number, isActive: boolean) => {
        try {
            const response = await apiClient.patch(`/api/v1/widgets/${widgetId}/toggle`, {
                is_active: !isActive
            });

            if (response.success) {
                loadWidgetData();
            }
        } catch (error: any) {
            console.error('Failed to toggle widget:', error);
        }
    };

    // 删除Widget
    const handleDelete = async (widgetId: number) => {
        if (!confirm('确定要删除这个Widget吗？')) return;

        try {
            const response = await apiClient.delete(`/api/v1/widgets/${widgetId}`);
            if (response.success) {
                loadWidgetData();
            }
        } catch (error: any) {
            console.error('Failed to delete widget:', error);
        }
    };

    // 添加Widget到区域
    const handleAddWidget = async (area: string, widgetType: string) => {
        const widgetTypeInfo = widgetTypes[widgetType];
        if (!widgetTypeInfo) return;

        try {
            const response = await apiClient.post('/api/v1/widgets', {
                widget_type: widgetType,
                area: area,
                title: widgetTypeInfo.name,
                config: widgetTypeInfo.default_config,
                order_index: 0,
                is_active: true
            });

            if (response.success) {
                loadWidgetData();
            }
        } catch (error: any) {
            console.error('Failed to add widget:', error);
        }
    };

    // 上移Widget
    const handleMoveUp = async (widget: WidgetInstance) => {
        const areaWidgets = widgets
            .filter(w => w.area === widget.area)
            .sort((a, b) => a.order_index - b.order_index);

        const index = areaWidgets.findIndex(w => w.id === widget.id);
        if (index === 0) return;

        const prevWidget = areaWidgets[index - 1];

        try {
            await apiClient.patch(`/api/v1/widgets/${widget.id}/reorder`, {
                order_index: prevWidget.order_index
            });
            await apiClient.patch(`/api/v1/widgets/${prevWidget.id}/reorder`, {
                order_index: widget.order_index
            });
            loadWidgetData();
        } catch (error: any) {
            console.error('Failed to reorder:', error);
        }
    };

    // 下移Widget
    const handleMoveDown = async (widget: WidgetInstance) => {
        const areaWidgets = widgets
            .filter(w => w.area === widget.area)
            .sort((a, b) => a.order_index - b.order_index);

        const index = areaWidgets.findIndex(w => w.id === widget.id);
        if (index === areaWidgets.length - 1) return;

        const nextWidget = areaWidgets[index + 1];

        try {
            await apiClient.patch(`/api/v1/widgets/${widget.id}/reorder`, {
                order_index: nextWidget.order_index
            });
            await apiClient.patch(`/api/v1/widgets/${nextWidget.id}/reorder`, {
                order_index: widget.order_index
            });
            loadWidgetData();
        } catch (error: any) {
            console.error('Failed to reorder:', error);
        }
    };

    // 渲染配置表单字段
    const renderConfigField = (key: string, value: any) => {
        if (typeof value === 'boolean') {
            return (
                <div key={key} className="flex items-center justify-between">
                    <Label htmlFor={key}>{key}</Label>
                    <Switch
                        id={key}
                        checked={configForm[key]}
                        onCheckedChange={(checked) => setConfigForm({...configForm, [key]: checked})}
                    />
                </div>
            );
        } else if (typeof value === 'number') {
            return (
                <div key={key}>
                    <Label htmlFor={key}>{key}</Label>
                    <Input
                        id={key}
                        type="number"
                        value={configForm[key]}
                        onChange={(e) => setConfigForm({...configForm, [key]: parseInt(e.target.value)})}
                    />
                </div>
            );
        } else {
            return (
                <div key={key}>
                    <Label htmlFor={key}>{key}</Label>
                    {key.includes('content') || key.includes('description') ? (
                        <Textarea
                            id={key}
                            value={configForm[key]}
                            onChange={(e) => setConfigForm({...configForm, [key]: e.target.value})}
                            rows={3}
                        />
                    ) : (
                        <Input
                            id={key}
                            value={configForm[key]}
                            onChange={(e) => setConfigForm({...configForm, [key]: e.target.value})}
                        />
                    )}
                </div>
            );
        }
    };

    // 按区域分组Widget
    const getWidgetsByArea = (area: string) => {
        return widgets
            .filter(w => w.area === area)
            .sort((a, b) => a.order_index - b.order_index);
    };

    // 拖拽结束处理
    const handleDragEnd = async (event: DragEndEvent) => {
        const {active, over} = event;

        if (!over || active.id === over.id) return;

        // 找到对应的 widget
        const activeWidget = widgets.find(w => w.id === active.id);
        const overWidget = widgets.find(w => w.id === over.id);

        if (!activeWidget || !overWidget) return;

        // 确保只在同一区域内拖拽
        if (activeWidget.area !== overWidget.area) return;

        const areaWidgets = getWidgetsByArea(activeWidget.area);
        const oldIndex = areaWidgets.findIndex(w => w.id === activeWidget.id);
        const newIndex = areaWidgets.findIndex(w => w.id === overWidget.id);

        // 更新本地状态
        const newOrderWidgets = arrayMove(areaWidgets, oldIndex, newIndex);

        // 准备批量更新的数据
        const updates = newOrderWidgets.map((widget, index) => ({
            id: widget.id,
            order_index: index
        }));

        try {
            // 调用 API 更新排序
            const response = await apiClient.post('/api/v1/widgets/batch-reorder', {
                updates
            });

            if (response.success) {
                loadWidgetData();
            }
        } catch (error: any) {
            console.error('Failed to reorder widgets:', error);
        }
    };

    // 设置拖拽传感器
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    Widget 管理
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                    配置和管理网站的小部件
                </p>
            </div>

            {loading ? (
                <div className="text-center py-8">加载中...</div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {Object.entries(widgetAreas).map(([areaKey, areaInfo]) => {
                        const areaWidgets = getWidgetsByArea(areaKey);

                        return (
                            <Card key={areaKey}>
                                <CardHeader>
                                    <CardTitle className="flex items-center justify-between">
                                        <span>{areaInfo.name}</span>
                                        <Badge variant="secondary">
                                            {areaWidgets.length} 个 Widget
                                        </Badge>
                                    </CardTitle>
                                    <CardDescription>{areaInfo.description}</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {/* Widget列表 - 支持拖拽排序 */}
                                    <DndContext
                                        sensors={sensors}
                                        collisionDetection={closestCenter}
                                        onDragEnd={handleDragEnd}
                                    >
                                        <SortableContext
                                            items={areaWidgets.map(w => w.id)}
                                            strategy={verticalListSortingStrategy}
                                        >
                                            <div className="space-y-3 mb-4">
                                                {areaWidgets.length === 0 ? (
                                                    <div className="text-center py-4 text-gray-500 text-sm">
                                                        暂无 Widget
                                                    </div>
                                                ) : (
                                                    areaWidgets.map((widget) => {
                                                        const widgetType = widgetTypes[widget.widget_type];
                                                        return (
                                                            <SortableWidgetItem
                                                                key={widget.id}
                                                                widget={widget}
                                                                widgetType={widgetType}
                                                                areaWidgets={areaWidgets}
                                                                onOpenConfig={handleOpenConfig}
                                                                onOpenPreview={handleOpenPreview}
                                                                onToggleActive={handleToggleActive}
                                                                onDelete={handleDelete}
                                                                onMoveUp={handleMoveUp}
                                                                onMoveDown={handleMoveDown}
                                                            />
                                                        );
                                                    })
                                                )}
                                            </div>
                                        </SortableContext>
                                    </DndContext>

                                    {/* 添加Widget按钮 */}
                                    <div className="relative">
                                        <details className="group">
                                            <summary className="cursor-pointer list-none">
                                                <Button variant="outline" size="sm" className="w-full">
                                                    <Plus className="w-4 h-4 mr-2"/>
                                                    添加 Widget
                                                </Button>
                                            </summary>
                                            <div
                                                className="absolute z-10 mt-2 w-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-lg p-3 max-h-96 overflow-y-auto">
                                                <div className="grid grid-cols-2 gap-2">
                                                    {Object.entries(widgetTypes).map(([typeKey, typeInfo]) => (
                                                        <button
                                                            key={typeKey}
                                                            onClick={() => handleAddWidget(areaKey, typeKey)}
                                                            className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-left"
                                                        >
                                                            <span className="text-xl">{typeInfo.icon}</span>
                                                            <div className="flex-1 min-w-0">
                                                                <div
                                                                    className="text-sm font-medium truncate">{typeInfo.name}</div>
                                                                <div
                                                                    className="text-xs text-gray-500 truncate">{typeInfo.category}</div>
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </details>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* 配置对话框 */}
            <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>配置 Widget</DialogTitle>
                        <DialogDescription>
                            {currentWidget && widgetTypes[currentWidget.widget_type]?.description}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        {/* Widget标题 */}
                        <div>
                            <Label htmlFor="widget-title">标题</Label>
                            <Input
                                id="widget-title"
                                value={currentWidget?.title || ''}
                                onChange={(e) => currentWidget && setCurrentWidget({
                                    ...currentWidget,
                                    title: e.target.value
                                })}
                            />
                        </div>

                        {/* 动态配置字段 */}
                        {currentWidget && Object.entries(configForm).map(([key, value]) =>
                            renderConfigField(key, value)
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={handleSaveConfig}>
                            <Save className="w-4 h-4 mr-2"/>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 预览对话框 */}
            <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
                <DialogContent className="max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>Widget 预览</DialogTitle>
                        <DialogDescription>
                            {currentWidget?.title || 'Widget'}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4">
                        <div 
                            className="border rounded-lg p-6 bg-white dark:bg-gray-800 min-h-[200px]"
                            dangerouslySetInnerHTML={{__html: previewHtml}}
                        />
                    </div>

                    <DialogFooter>
                        <Button onClick={() => setShowPreviewDialog(false)}>
                            关闭
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default WidgetManagement;
