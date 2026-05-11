'use client';

import React from 'react';
import SettingCard from './SettingCard';
import InputField from './InputField';
import {Button} from '@/components/ui/button';

interface Setting {
  key: string;
  value: string;
}

interface GeneralSettingsTabProps {
  settings: Record<string, string>;
  handleSettingChange: (key: string, value: string) => void;
  handleSaveGeneralSettings: () => void;
}

const GeneralSettingsTab: React.FC<GeneralSettingsTabProps> = ({ 
  settings, 
  handleSettingChange, 
  handleSaveGeneralSettings 
}) => {
  return (
    <div className="space-y-6">
      <SettingCard 
        title="站点信息" 
        description="配置您的站点基本名称和描述信息"
      >
        <InputField
          label="站点名称"
          description="显示在浏览器标签和SEO中的站点名称"
          value={settings.site_name || ''}
          onChange={(value) => handleSettingChange('site_name', value)}
          placeholder="我的博客"
        />
        <InputField
          label="站点描述"
          description="简短描述您的站点，用于搜索引擎结果摘要"
          value={settings.site_description || ''}
          onChange={(value) => handleSettingChange('site_description', value)}
          placeholder="这是一个精彩的博客站点"
          type="textarea"
          rows={2}
        />
        <InputField
          label="站点URL"
          description="站点的主要访问地址"
          value={settings.site_url || ''}
          onChange={(value) => handleSettingChange('site_url', value)}
          placeholder="https://www.example.com"
          type="url"
        />
      </SettingCard>
      
      <div className="flex justify-end">
        <Button onClick={handleSaveGeneralSettings} size="lg">
          保存所有设置
        </Button>
      </div>
    </div>
  );
};

export default GeneralSettingsTab;