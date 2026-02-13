'use client';

import React, {useState} from 'react';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Menu, MenuItem} from '@/lib/api/admin-settings-service';
import {ChevronDown, ChevronRight, Edit, Plus, Trash2} from 'lucide-react';

interface MenuManagementTabProps {
  menus: Menu[];
  menuItems: Record<string, MenuItem[]>; // 按菜单ID分组的菜单项
  onAddMenu: () => void;
  onEditMenu: (menu: Menu) => void;
  onDeleteMenu: (menuId: number) => void;
  onAddMenuItem: (menu: Menu) => void;
  onEditMenuItem: (item: MenuItem) => void;
  onDeleteMenuItem: (itemId: number) => void;
}

const MenuManagementTab: React.FC<MenuManagementTabProps> = ({ 
  menus, 
  menuItems,
  onAddMenu,
  onEditMenu,
  onDeleteMenu,
  onAddMenuItem,
  onEditMenuItem,
  onDeleteMenuItem
}) => {
  const [expandedMenus, setExpandedMenus] = useState<number[]>([]);

  const toggleMenu = (menuId: number) => {
    if (expandedMenus.includes(menuId)) {
      setExpandedMenus(expandedMenus.filter(id => id !== menuId));
    } else {
      setExpandedMenus([...expandedMenus, menuId]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">菜单管理</h3>
        <Button onClick={onAddMenu} className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          新建菜单
        </Button>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>菜单名称</TableHead>
              <TableHead>标识符</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {menus.length > 0 ? (
              menus.map((menu) => {
                const items = menuItems[menu.id] || [];
                
                return (
                  <React.Fragment key={menu.id}>
                    <TableRow key={menu.id} className="hover:bg-gray-50">
                      <TableCell className="font-medium">
                        <button 
                          onClick={() => toggleMenu(menu.id)}
                          className="flex items-center gap-1 text-left"
                        >
                          {expandedMenus.includes(menu.id) ? 
                            <ChevronDown className="w-4 h-4" /> : 
                            <ChevronRight className="w-4 h-4" />
                          }
                          {menu.name}
                        </button>
                      </TableCell>
                      <TableCell>
                        <code className="bg-gray-100 px-2 py-1 rounded text-xs">{menu.slug}</code>
                      </TableCell>
                      <TableCell>{menu.description}</TableCell>
                      <TableCell>
                        <Badge variant={menu.is_active ? 'default' : 'secondary'}>
                          {menu.is_active ? '启用' : '禁用'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => onEditMenu(menu)}
                            className="p-2"
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => onDeleteMenu(menu.id)}
                            className="p-2"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    
                    {expandedMenus.includes(menu.id) && items.length > 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="bg-gray-50 p-0">
                          <div className="pl-8 pr-4 py-3">
                            <div className="flex justify-between items-center mb-3">
                              <h4 className="font-medium">菜单项</h4>
                              <Button 
                                size="sm" 
                                variant="outline" 
                                onClick={() => onAddMenuItem(menu)}
                                className="flex items-center gap-1"
                              >
                                <Plus className="w-3 h-3" />
                                添加菜单项
                              </Button>
                            </div>
                            
                            <div className="ml-6">
                              <Table className="bg-white rounded-md">
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>标题</TableHead>
                                    <TableHead>链接</TableHead>
                                    <TableHead>打开方式</TableHead>
                                    <TableHead>排序</TableHead>
                                    <TableHead className="text-right">操作</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {items.map((item: MenuItem) => (
                                    <TableRow key={item.id}>
                                      <TableCell className="font-medium">{item.title}</TableCell>
                                      <TableCell>
                                        <code className="text-xs bg-gray-100 px-2 py-1 rounded break-all">
                                          {item.url}
                                        </code>
                                      </TableCell>
                                      <TableCell>
                                        <Badge variant="outline">{item.target}</Badge>
                                      </TableCell>
                                      <TableCell>{item.order_index}</TableCell>
                                      <TableCell className="text-right">
                                        <div className="flex justify-end gap-2">
                                          <Button 
                                            size="sm" 
                                            variant="ghost" 
                                            onClick={() => onEditMenuItem(item)}
                                            className="p-2"
                                          >
                                            <Edit className="w-4 h-4" />
                                          </Button>
                                          <Button 
                                            size="sm" 
                                            variant="ghost" 
                                            onClick={() => onDeleteMenuItem(item.id)}
                                            className="p-2 text-red-600 hover:text-red-700"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </Button>
                                        </div>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                    
                    {expandedMenus.includes(menu.id) && items.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="bg-gray-50 pl-12 py-4 text-center text-gray-500">
                          此菜单暂无菜单项，
                          <Button 
                            variant="link" 
                            className="p-0 h-auto m-0 ml-1 text-blue-600 hover:text-blue-800"
                            onClick={() => onAddMenuItem(menu)}
                          >
                            点击添加菜单项
                          </Button>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                )
              })
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                  还没有创建任何菜单，点击上方按钮创建一个新菜单
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default MenuManagementTab;