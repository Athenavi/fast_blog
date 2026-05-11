'use client';

import React from 'react';
import SettingCard from './SettingCard';
import InputField from './InputField';
import {Button} from '@/components/ui/button';

interface HomeConfigTabProps {
  homeConfig: Record<string, string>;
  handleHomeConfigChange: (key: string, value: string) => void;
  handleSaveHomeConfig: () => void;
  homeConfigLoading: boolean;
}

const HomeConfigTab: React.FC<HomeConfigTabProps> = ({ 
  homeConfig, 
  handleHomeConfigChange, 
  handleSaveHomeConfig,
  homeConfigLoading
}) => {
  return (
    <div className="space-y-6">
      <SettingCard 
        title="英雄区域配置" 
        description="配置首页顶部英雄区域的内容和样式"
      >
        <InputField
          label="标题"
          value={homeConfig.hero_title || ''}
          onChange={(value) => handleHomeConfigChange('hero_title', value)}
          placeholder="欢迎来到我的博客"
        />
        <InputField
          label="副标题"
          value={homeConfig.hero_subtitle || ''}
          onChange={(value) => handleHomeConfigChange('hero_subtitle', value)}
          placeholder="探索世界的无限可能"
          type="textarea"
          rows={2}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InputField
            label="按钮文字"
            value={homeConfig.hero_button_text || ''}
            onChange={(value) => handleHomeConfigChange('hero_button_text', value)}
            placeholder="了解更多"
          />
          <InputField
            label="按钮链接"
            value={homeConfig.hero_button_url || ''}
            onChange={(value) => handleHomeConfigChange('hero_button_url', value)}
            placeholder="/about"
            type="url"
          />
        </div>
      </SettingCard>

      <SettingCard 
        title="特色文章配置" 
        description="配置首页特色文章展示的数量和筛选条件"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InputField
            label="展示文章数量"
            type="number"
            min={1}
            max={10}
            value={homeConfig.featured_posts_count || '3'}
            onChange={(value) => handleHomeConfigChange('featured_posts_count', value)}
            placeholder="3"
          />
          <InputField
            label="分类筛选"
            value={homeConfig.featured_posts_category || ''}
            onChange={(value) => handleHomeConfigChange('featured_posts_category', value)}
            placeholder="留空则显示全部"
          />
        </div>
      </SettingCard>

      <SettingCard 
        title="主内容区域" 
        description="配置首页主内容区域的静态内容"
      >
        <InputField
          label="首页内容"
          value={homeConfig.home_content || ''}
          onChange={(value) => handleHomeConfigChange('home_content', value)}
          placeholder="首页主内容..."
          type="textarea"
          rows={5}
        />
      </SettingCard>
      
      <div className="flex justify-end">
        <Button 
          onClick={handleSaveHomeConfig} 
          disabled={homeConfigLoading}
          size="lg"
        >
          {homeConfigLoading ? '保存中...' : '保存所有配置'}
        </Button>
      </div>
    </div>
  );
};

export default HomeConfigTab;