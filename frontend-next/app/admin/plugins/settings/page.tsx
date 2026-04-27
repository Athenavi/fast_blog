'use client';

import {Suspense, useEffect, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {apiClient} from '@/lib/api/base-client';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Switch} from '@/components/ui/switch';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {ArrowLeft, Save, Settings} from 'lucide-react';

interface PluginSetting {
  key: string;
  label: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'textarea';
  default?: any;
  options?: Array<{ value: string; label: string }>;
  help_text?: string;
}

interface PluginSettingsUI {
  fields: PluginSetting[];
}

interface PluginInfo {
  id: number;
  name: string;
  slug: string;
  version: string;
  description: string;
  author: string;
  active: boolean;
  installed: boolean;
  settings: Record<string, any>;
}

// 包装组件以支持 Suspense
const PluginSettingsContent = () => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pluginSlug = searchParams.get('slug') || '';

  const [plugin, setPlugin] = useState<PluginInfo | null>(null);
  const [settingsUI, setSettingsUI] = useState<PluginSettingsUI | null>(null);
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPluginSettings();
  }, [pluginSlug]);

  // 加载插件设置
  const loadPluginSettings = async () => {
    try {
      setLoading(true);
      
      // 获取插件信息
      const infoResponse = await apiClient.get(`/api/v1/plugins/${pluginSlug}`);
      if (infoResponse.success && infoResponse.data) {
        const pluginData = infoResponse.data as PluginInfo;
        setPlugin(pluginData);
        setSettings(pluginData.settings || {});
      }

      // 获取设置UI配置
      const uiResponse = await apiClient.get(`/api/v1/plugins/${pluginSlug}/settings`);
      if (uiResponse.success && uiResponse.data) {
        const uiData = uiResponse.data as { ui?: PluginSettingsUI };
        setSettingsUI(uiData.ui || {fields: []});
      }
    } catch (error) {
      console.error('Failed to load plugin settings:', error);
      alert('加载插件设置失败');
    } finally {
      setLoading(false);
    }
  };

  // 保存设置
  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      const response = await apiClient.put(`/api/v1/plugins/${pluginSlug}/settings`, {
        settings: settings
      });

      if (response.success) {
        alert('设置已保存');
        loadPluginSettings();
      } else {
        alert(response.error || '保存失败');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 更新设置值
  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // 渲染设置字段
  const renderField = (field: PluginSetting) => {
    const value = settings[field.key] ?? field.default;

    switch (field.type) {
      case 'boolean':
        return (
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor={field.key}>{field.label}</Label>
              {field.help_text && (
                <p className="text-sm text-gray-500 mt-1">{field.help_text}</p>
              )}
            </div>
            <Switch
              id={field.key}
              checked={value}
              onCheckedChange={(checked) => updateSetting(field.key, checked)}
            />
          </div>
        );

      case 'select':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.key}>{field.label}</Label>
            {field.help_text && (
              <p className="text-sm text-gray-500">{field.help_text}</p>
            )}
            <Select
              value={value?.toString()}
              onValueChange={(val) => updateSetting(field.key, val)}
            >
              <SelectTrigger>
                <SelectValue placeholder="请选择" />
              </SelectTrigger>
              <SelectContent>
                {field.options?.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );

      case 'textarea':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.key}>{field.label}</Label>
            {field.help_text && (
              <p className="text-sm text-gray-500">{field.help_text}</p>
            )}
            <textarea
              id={field.key}
              value={value || ''}
              onChange={(e) => updateSetting(field.key, e.target.value)}
              className="w-full min-h-[100px] px-3 py-2 border rounded-md"
              placeholder={field.label}
            />
          </div>
        );

      case 'number':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.key}>{field.label}</Label>
            {field.help_text && (
              <p className="text-sm text-gray-500">{field.help_text}</p>
            )}
            <Input
              id={field.key}
              type="number"
              value={value || ''}
              onChange={(e) => updateSetting(field.key, parseFloat(e.target.value))}
              placeholder={field.label}
            />
          </div>
        );

      default: // text
        return (
          <div className="space-y-2">
            <Label htmlFor={field.key}>{field.label}</Label>
            {field.help_text && (
              <p className="text-sm text-gray-500">{field.help_text}</p>
            )}
            <Input
              id={field.key}
              type="text"
              value={value || ''}
              onChange={(e) => updateSetting(field.key, e.target.value)}
              placeholder={field.label}
            />
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!plugin) {
    return (
      <div className="text-center py-8">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">插件不存在</h2>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push('/admin/plugins')}
        >
          返回插件列表
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/admin/plugins')}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="w-8 h-8" />
            {plugin.name} - 设置
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {plugin.description}
          </p>
        </div>
      </div>

      {/* 插件信息卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>插件信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-500">版本</div>
              <div className="font-medium">{plugin.version}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">作者</div>
              <div className="font-medium">{plugin.author}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">状态</div>
              <div className="font-medium">
                {plugin.active ? (
                  <span className="text-green-600">已激活</span>
                ) : (
                  <span className="text-gray-600">未激活</span>
                )}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">标识</div>
              <div className="font-medium text-sm">{plugin.slug}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 设置表单 */}
      <Card>
        <CardHeader>
          <CardTitle>插件设置</CardTitle>
          <CardDescription>
            配置插件的各项参数
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!settingsUI || settingsUI.fields.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>该插件暂无可配置项</p>
            </div>
          ) : (
            <div className="space-y-6">
              {settingsUI.fields.map((field) => (
                <div key={field.key}>
                  {renderField(field)}
                </div>
              ))}

              <div className="flex justify-end pt-4 border-t">
                <Button
                  onClick={handleSaveSettings}
                  disabled={saving}
                  className="gap-2"
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      保存设置
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// 主组件，包含 Suspense 边界
const PluginSettingsPage = () => {
  return (
      <Suspense fallback={
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">加载中...</div>
        </div>
      }>
        <PluginSettingsContent/>
      </Suspense>
  );
};

export default PluginSettingsPage;
