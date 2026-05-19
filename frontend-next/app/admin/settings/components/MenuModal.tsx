'use client';

import React, {useState} from 'react';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';
import InputField from './InputField';
import {Menu} from '@/lib/api/admin-settings-service';

interface MenuModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  menu?: Menu;
  onSave: (menu: Menu) => void;
}

const MenuModal: React.FC<MenuModalProps> = ({ open, onOpenChange, menu, onSave }) => {
  const [formData, setFormData] = useState({
    name: menu?.name || '',
    slug: menu?.slug || '',
    position: menu?.slug || 'header',
    description: menu?.description || ''
  });

  const handleSubmit = () => {
    // 创建临时菜单对象
    const tempMenu = {
      id: menu?.id,
      name: formData.name,
      slug: formData.slug,
      description: formData.description,
      is_active: menu?.is_active ?? true,
      created_at: menu?.created_at || new Date().toISOString(),
      updated_at: menu?.updated_at || new Date().toISOString()
    };
    
    onSave(tempMenu as Menu);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>{menu?.id ? '编辑菜单' : '新建菜单'}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <InputField
            label="名称"
            value={formData.name}
            onChange={(value) => setFormData({...formData, name: value})}
            placeholder="例如：主导航"
          />
          <InputField
            label="标识符"
            value={formData.slug}
            onChange={(value) => setFormData({...formData, slug: value})}
            placeholder="例如：main-navigation"
            description="用于在代码中引用此菜单"
          />
          <InputField
            type="select"
            label="位置"
            value={formData.position}
            onChange={(value) => setFormData({...formData, position: value})}
            options={[
              { value: 'header', label: '头部' },
              { value: 'footer', label: '底部' },
              { value: 'sidebar', label: '侧边栏' }
            ]}
            placeholder="选择位置"
          />
          <InputField
            type="textarea"
            label="描述"
            value={formData.description}
            onChange={(value) => setFormData({...formData, description: value})}
            placeholder="描述此菜单的用途..."
            rows={2}
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

export default MenuModal;