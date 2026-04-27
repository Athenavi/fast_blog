/**
 * 可视化菜单编辑器 - 支持拖拽排序、嵌套菜单、实时预览
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import {Badge} from '@/components/ui/badge';
import apiClient from '@/lib/api-client';
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
import {Edit2, GripVertical, Plus, Save, Trash2, X} from 'lucide-react';

interface MenuItem {
  id: number;
  title: string;
  url: string;
  target: string;
  order_index: number;
  is_active: boolean;
  menu_id: number;
  parent_id?: number | null;
  children?: MenuItem[];
}

interface Menu {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  items?: MenuItem[];
}

// 可排序的菜单项组件
interface SortableMenuItemProps {
  item: MenuItem;
  depth: number;
  onEdit: (item: MenuItem) => void;
  onDelete: (id: number) => void;
  onAddChild: (parentId: number) => void;
}

const SortableMenuItem: React.FC<SortableMenuItemProps> = ({
                                                             item,
                                                             depth,
                                                             onEdit,
                                                             onDelete,
                                                             onAddChild
                                                           }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({id: item.id});

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    marginLeft: `${depth * 24}px`,
  };

  return (
      <div
          ref={setNodeRef}
          style={style}
          className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg mb-2 hover:shadow-md transition-shadow"
      >
        {/* 拖拽手柄 */}
        <div {...attributes} {...listeners} className="cursor-move">
          <GripVertical className="w-5 h-5 text-gray-400"/>
        </div>

        {/* 菜单项信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{item.title}</span>
            {item.target === '_blank' && (
                <Badge variant="outline" className="text-xs">新窗口</Badge>
            )}
          </div>
          <div className="text-xs text-gray-500 truncate">{item.url}</div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-1">
          <Button
              variant="ghost"
              size="sm"
              onClick={() => onAddChild(item.id)}
              title="添加子菜单"
          >
            <Plus className="w-4 h-4"/>
          </Button>
          <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(item)}
              title="编辑"
          >
            <Edit2 className="w-4 h-4"/>
          </Button>
          <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(item.id)}
              title="删除"
              className="text-red-600"
          >
            <Trash2 className="w-4 h-4"/>
          </Button>
        </div>
      </div>
  );
};

const MenuEditor = () => {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [selectedMenu, setSelectedMenu] = useState<Menu | null>(null);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  // 对话框状态
  const [showItemDialog, setShowItemDialog] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [itemForm, setItemForm] = useState({
    title: '',
    url: '',
    target: '_self',
    parent_id: null as number | null
  });

  // dnd-kit传感器
  const sensors = useSensors(
      useSensor(PointerSensor),
      useSensor(KeyboardSensor, {
        coordinateGetter: sortableKeyboardCoordinates,
      })
  );

  useEffect(() => {
    loadMenus();
  }, []);

  // 加载菜单列表
  const loadMenus = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/menus');

      if (response.success && response.data) {
        setMenus((response.data as any).menus || []);
        if ((response.data as any).menus && (response.data as any).menus.length > 0) {
          selectMenu((response.data as any).menus[0]);
        }
      }
    } catch (err: any) {
      console.error('Failed to load menus:', err);
    } finally {
      setLoading(false);
    }
  };

  // 选择菜单
  const selectMenu = async (menu: Menu) => {
    setSelectedMenu(menu);

    try {
      const response = await apiClient.get(`/api/v1/menus/${menu.id}/items`);

      if (response.success && response.data) {
        setMenuItems((response.data as any).items || []);
      }
    } catch (err: any) {
      console.error('Failed to load menu items:', err);
    }
  };

  // 拖拽结束处理
  const handleDragEnd = async (event: DragEndEvent) => {
    const {active, over} = event;

    if (over && active.id !== over.id) {
      const oldIndex = menuItems.findIndex(item => item.id === active.id);
      const newIndex = menuItems.findIndex(item => item.id === over.id);

      const newItems = arrayMove(menuItems, oldIndex, newIndex);

      // 更新order_index
      const updatedItems = newItems.map((item, index) => ({
        ...item,
        order_index: index
      }));

      setMenuItems(updatedItems);

      // 保存到后端
      try {
        await apiClient.put(`/api/v1/menus/${selectedMenu?.id}/reorder`, {
          items: updatedItems.map(item => ({
            id: item.id,
            order_index: item.order_index
          }))
        });
      } catch (err: any) {
        console.error('Failed to save order:', err);
      }
    }
  };

  // 打开添加/编辑对话框
  const handleOpenDialog = (item?: MenuItem, parentId?: number) => {
    if (item) {
      setEditingItem(item);
      setItemForm({
        title: item.title,
        url: item.url,
        target: item.target,
        parent_id: item.parent_id || null
      });
    } else {
      setEditingItem(null);
      setItemForm({
        title: '',
        url: '',
        target: '_self',
        parent_id: parentId || null
      });
    }
    setShowItemDialog(true);
  };

  // 保存菜单项
  const handleSaveItem = async () => {
    if (!selectedMenu) return;

    try {
      let response;

      if (editingItem) {
        // 更新
        response = await apiClient.put(`/api/v1/menu-items/${editingItem.id}`, {
          ...itemForm
        });
      } else {
        // 创建
        response = await apiClient.post('/api/v1/menu-items', {
          menu_id: selectedMenu.id,
          ...itemForm,
          order_index: menuItems.length
        });
      }

      if (response.success) {
        selectMenu(selectedMenu);
        setShowItemDialog(false);
      }
    } catch (err: any) {
      console.error('Failed to save menu item:', err);
    }
  };

  // 删除菜单项
  const handleDeleteItem = async (itemId: number) => {
    if (!confirm('确定要删除这个菜单项吗？')) return;

    try {
      const response = await apiClient.delete(`/api/v1/menu-items/${itemId}`);

      if (response.success) {
        selectMenu(selectedMenu!);
      }
    } catch (err: any) {
      console.error('Failed to delete menu item:', err);
    }
  };

  // 将平铺的菜单项转换为树形结构
  const buildMenuTree = (items: MenuItem[]): MenuItem[] => {
    const itemMap = new Map<number, MenuItem>();
    const rootItems: MenuItem[] = [];

    items.forEach(item => {
      itemMap.set(item.id, {...item, children: []});
    });

    items.forEach(item => {
      const itemNode = itemMap.get(item.id)!;
      if (item.parent_id && itemMap.has(item.parent_id)) {
        const parent = itemMap.get(item.parent_id)!;
        if (!parent.children) {
          parent.children = [];
        }
        parent.children.push(itemNode);
      } else {
        rootItems.push(itemNode);
      }
    });

    return rootItems;
  };

  // 递归渲染菜单项
  const renderMenuItems = (items: MenuItem[], depth: number = 0) => {
    return items.map(item => (
        <div key={item.id}>
          <SortableMenuItem
              item={item}
              depth={depth}
              onEdit={handleOpenDialog}
              onDelete={handleDeleteItem}
              onAddChild={(parentId) => handleOpenDialog(undefined, parentId)}
          />
          {item.children && item.children.length > 0 && (
              <div className="ml-6 border-l-2 border-gray-200 dark:border-gray-700 pl-2">
                {renderMenuItems(item.children, depth + 1)}
              </div>
          )}
        </div>
    ));
  };

  const menuTree = buildMenuTree(menuItems);

  return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            菜单编辑器
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            拖拽排序和管理网站菜单
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧：菜单列表 */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>菜单列表</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {menus.map(menu => (
                    <button
                        key={menu.id}
                        onClick={() => selectMenu(menu)}
                        className={`w-full text-left p-3 rounded-lg border transition-all ${
                            selectedMenu?.id === menu.id
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                        }`}
                    >
                      <div className="font-medium">{menu.name}</div>
                      <div className="text-xs text-gray-500">{menu.slug}</div>
                    </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 右侧：菜单项编辑器 */}
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{selectedMenu?.name || '选择菜单'}</CardTitle>
                  <CardDescription>{selectedMenu?.description}</CardDescription>
                </div>
                <Button onClick={() => handleOpenDialog()}>
                  <Plus className="w-4 h-4 mr-2"/>
                  添加菜单项
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                  <div className="text-center py-8">加载中...</div>
              ) : !selectedMenu ? (
                  <div className="text-center py-8 text-gray-500">
                    请从左侧选择一个菜单
                  </div>
              ) : menuItems.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    暂无菜单项，点击上方按钮添加
                  </div>
              ) : (
                  <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                        items={menuItems.map(item => item.id)}
                        strategy={verticalListSortingStrategy}
                    >
                      {renderMenuItems(menuTree)}
                    </SortableContext>
                  </DndContext>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 菜单项编辑对话框 */}
        <Dialog open={showItemDialog} onOpenChange={setShowItemDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingItem ? '编辑菜单项' : '添加菜单项'}
              </DialogTitle>
              <DialogDescription>
                {itemForm.parent_id ? '添加子菜单项' : '添加顶级菜单项'}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="title">标题 *</Label>
                <Input
                    id="title"
                    value={itemForm.title}
                    onChange={(e) => setItemForm({...itemForm, title: e.target.value})}
                    placeholder="菜单显示文本"
                />
              </div>

              <div>
                <Label htmlFor="url">URL *</Label>
                <Input
                    id="url"
                    value={itemForm.url}
                    onChange={(e) => setItemForm({...itemForm, url: e.target.value})}
                    placeholder="/path or https://example.com"
                />
              </div>

              <div>
                <Label htmlFor="target">打开方式</Label>
                <Select
                    value={itemForm.target}
                    onValueChange={(value) => setItemForm({...itemForm, target: value})}
                >
                  <SelectTrigger>
                    <SelectValue/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_self">当前窗口</SelectItem>
                    <SelectItem value="_blank">新窗口</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowItemDialog(false)}>
                <X className="w-4 h-4 mr-2"/>
                取消
              </Button>
              <Button onClick={handleSaveItem}>
                <Save className="w-4 h-4 mr-2"/>
                保存
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
  );
};

export default MenuEditor;
