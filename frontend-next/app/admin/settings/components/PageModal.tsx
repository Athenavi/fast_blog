'use client';

import React, {useState} from 'react';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';
import InputField from './InputField';
import {Page} from '@/lib/api/admin-settings-service';

interface PageModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  page?: Page;
  onSave: (page: Page) => void;
}

const PageModal: React.FC<PageModalProps> = ({ open, onOpenChange, page, onSave }) => {
  const [formData, setFormData] = useState({
    title: page?.title || '',
    slug: page?.slug || '',
    template: page?.template || 'default',
    excerpt: page?.excerpt || '',
    content: page?.content || '',
    meta_title: page?.meta_title || '',
    meta_description: page?.meta_description || '',
    meta_keywords: page?.meta_keywords || '',
    status: String(page?.status || 1),
    is_sticky: page?.is_sticky || false
  });

  const handleSubmit = () => {
    // 创建临时页面对象
    const tempPage = {
      id: page?.id,
      title: formData.title,
      slug: formData.slug,
      template: formData.template,
      excerpt: formData.excerpt,
      content: formData.content,
      meta_title: formData.meta_title,
      meta_description: formData.meta_description,
      meta_keywords: formData.meta_keywords,
      status: parseInt(formData.status),
      is_sticky: formData.is_sticky,
      created_at: page?.created_at || new Date().toISOString(),
      updated_at: page?.updated_at || new Date().toISOString()
    };
    
    onSave(tempPage as Page);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[625px] h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{page?.id ? '编辑页面' : '新建页面'}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4 overflow-y-auto flex-grow">
          <InputField
            label="标题"
            value={formData.title}
            onChange={(value) => setFormData({...formData, title: value})}
            placeholder="页面标题"
          />
          <InputField
            label="URL标识符"
            value={formData.slug}
            onChange={(value) => setFormData({...formData, slug: value})}
            placeholder="例如：about-us"
            description="用于构建页面URL，只能包含字母、数字和连字符"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InputField
              type="select"
              label="模板"
              value={formData.template}
              onChange={(value) => setFormData({...formData, template: value})}
              options={[
                { value: 'default', label: '默认模板' },
                { value: 'blog', label: '博客模板' },
                { value: 'landing', label: '落地页模板' }
              ]}
              placeholder="选择模板"
            />
            <InputField
              type="select"
              label="状态"
              value={formData.status}
              onChange={(value) => setFormData({...formData, status: value})}
              options={[
                { value: '0', label: '草稿' },
                { value: '1', label: '发布' }
              ]}
              placeholder="选择状态"
            />
          </div>
          <InputField
            type="textarea"
            label="摘要"
            value={formData.excerpt}
            onChange={(value) => setFormData({...formData, excerpt: value})}
            placeholder="页面摘要..."
            rows={2}
          />
          <InputField
            type="textarea"
            label="内容"
            value={formData.content}
            onChange={(value) => setFormData({...formData, content: value})}
            placeholder="页面内容..."
            rows={4}
          />
          <div className="space-y-4 pt-2">
            <h3 className="text-lg font-medium">SEO 设置</h3>
            <InputField
              label="SEO标题"
              value={formData.meta_title}
              onChange={(value) => setFormData({...formData, meta_title: value})}
              placeholder="SEO友好标题"
            />
            <InputField
              label="SEO描述"
              value={formData.meta_description}
              onChange={(value) => setFormData({...formData, meta_description: value})}
              placeholder="页面描述，用于搜索引擎结果"
              type="textarea"
              rows={2}
            />
            <InputField
              label="SEO关键词"
              value={formData.meta_keywords}
              onChange={(value) => setFormData({...formData, meta_keywords: value})}
              placeholder="逗号分隔的关键词"
            />
          </div>
          <div className="flex items-center space-x-2 pt-2">
            <InputField
              type="boolean"
              label="设为置顶"
              value={formData.is_sticky}
              onChange={(value) => setFormData({...formData, is_sticky: value})}
            />
          </div>
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

export default PageModal;