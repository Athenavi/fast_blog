'use client';

import React, {useState} from 'react';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';
import InputField from './InputField';
import {Menu, MenuItem} from '@/lib/api/admin-settings-service';

interface MenuItemModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  menuItem?: MenuItem;
  menus: Menu[];
  onSave: (menuItem: MenuItem) => void;
}

const MenuItemModal: React.FC<MenuItemModalProps> = ({ open, onOpenChange, menuItem, menus, onSave }) => {
  const [formData, setFormData] = useState({
    title: menuItem?.title || '',
    url: menuItem?.url || '',
    target: menuItem?.target || '_self',
    order_index: String(menuItem?.order_index || 0),
    parent_id: String(menuItem?.parent_id || 'null'),
    menu_id: menuItem?.menu_id || menus[0]?.id || 0,
    is_active: menuItem?.is_active ?? true
  });

  const handleSubmit = () => {
    // 创建临时菜单项对象
    const tempMenuItem = {
      id: menuItem?.id,
      title: formData.title,
      url: formData.url,
      target: formData.target,
      order_index: parseInt(formData.order_index),
      parent_id: formData.parent_id === 'null' ? null : parseInt(formData.parent_id),
      menu_id: formData.menu_id,
      is_active: formData.is_active,
      created_at: menuItem?.created_at || new Date().toISOString(),
      updated_at: menuItem?.updated_at || new Date().toISOString()
    };
    
    onSave(tempMenuItem as MenuItem);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>{menuItem?.id ? '编辑菜单项' : '新建菜单项'}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <InputField
            label="标题"
            value={formData.title}
            onChange={(value) => setFormData({...formData, title: value})}
            placeholder="例如：关于我们"
          />
          <InputField
            label="链接"
            value={formData.url}
            onChange={(value) => setFormData({...formData, url: value})}
            placeholder="例如：/about 或 https://example.com"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InputField
              type="select"
              label="打开方式"
              value={formData.target}
              onChange={(value) => setFormData({...formData, target: value})}
              options={[
                { value: '_self', label: '当前窗口' },
                { value: '_blank', label: '新窗口' }
              ]}
              placeholder="选择打开方式"
            />
            <InputField
              type="number"
              label="排序"
              value={formData.order_index}
              onChange={(value) => setFormData({...formData, order_index: value})}
              min={0}
              placeholder="0"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InputField
              type="select"
              label="所属菜单"
              value={String(formData.menu_id)}
              onChange={(value) => setFormData({...formData, menu_id: parseInt(value)})}
              options={menus.map(menu => ({ value: String(menu.id), label: menu.name }))}
              placeholder="选择菜单"
            />
            <InputField
              type="select"
              label="父菜单项"
              value={formData.parent_id}
              onChange={(value) => setFormData({...formData, parent_id: value})}
              options={[
                { value: 'null', label: '无' },
                // 在实际实现中，这里应该填充当前菜单的现有菜单项
              ]}
              placeholder="选择父菜单项"
            />
          </div>
          <InputField
            type="boolean"
            label="启用"
            value={formData.is_active}
            onChange={(value) => setFormData({...formData, is_active: value})}
          />
        </div>
        <DialogFooter>
          <Button 
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <Button 
            onClick={handleSubmit}
          >
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default MenuItemModal;