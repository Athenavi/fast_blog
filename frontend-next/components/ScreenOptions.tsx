'use client';

import {useEffect, useState} from 'react';
import {Button} from '@/components/ui/button';
import {Checkbox} from '@/components/ui/checkbox';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Settings, X} from 'lucide-react';
import {toast} from 'sonner';
import {getConfig} from '@/lib/config';

interface ScreenOptionsProps {
  pageName: string;
  availableColumns?: Array<{ key: string; label: string }>;
  defaultPerPage?: number;
  onOptionsChange?: (options: ScreenOptions) => void;
}

interface ScreenOptions {
  columns?: string[];
  per_page?: number;
  sidebar_visible?: boolean;
  [key: string]: any;
}

export default function ScreenOptions({ 
  pageName, 
  availableColumns = [],
  defaultPerPage = 20,
  onOptionsChange 
}: ScreenOptionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ScreenOptions>({
    columns: availableColumns.map(col => col.key),
    per_page: defaultPerPage,
    sidebar_visible: true,
  });
  const [loading, setLoading] = useState(false);

  // 加载用户偏好
  useEffect(() => {
    loadOptions();
  }, [pageName]);

  const loadOptions = async () => {
    try {
      const config = getConfig();
      const apiUrl = `${config.API_BASE_URL}${config.API_PREFIX}/screen-options/options?page_name=${pageName}`;

      console.log('Loading screen options from:', apiUrl);

      const response = await fetch(apiUrl, {
        credentials: 'include',
      });

      if (!response.ok) return;

      const result = await response.json();
      if (result.success && result.data) {
        const loadedOptions = {
          columns: result.data.columns || availableColumns.map(col => col.key),
          per_page: result.data.per_page || defaultPerPage,
          sidebar_visible: result.data.sidebar_visible !== undefined ? result.data.sidebar_visible : true,
          ...result.data,
        };
        setOptions(loadedOptions);
        if (onOptionsChange) {
          onOptionsChange(loadedOptions);
        }
      }
    } catch (error) {
      console.error('Error loading screen options:', error);
    }
  };

  // 保存选项
  const saveOptions = async (newOptions: ScreenOptions) => {
    try {
      setLoading(true);

      const config = getConfig();
      const apiUrl = `${config.API_BASE_URL}${config.API_PREFIX}/screen-options/options/batch`;

      console.log('Saving screen options to:', apiUrl);
      console.log('Data:', {pageName, options: newOptions});

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          page_name: pageName,
          options: newOptions,
        }),
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      // 先检查Content-Type
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        // 尝试读取响应文本以查看实际返回了什么
        const text = await response.text();
        console.error('Non-JSON response:', text.substring(0, 500));
        throw new Error(`服务器返回了非JSON响应 (HTTP ${response.status})`);
      }

      // 解析JSON响应
      let result;
      try {
        result = await response.json();
        console.log('Response data:', result);
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        throw new Error(`HTTP ${response.status}: 服务器响应格式错误`);
      }

      // 检查HTTP状态码
      if (!response.ok) {
        const errorMessage = result?.error || result?.message || `HTTP ${response.status}: 请求失败`;
        throw new Error(errorMessage);
      }

      // 检查业务逻辑是否成功
      if (!result.success) {
        throw new Error(result.error || result.message || '保存失败');
      }

      toast.success('设置已保存');
      if (onOptionsChange) {
        onOptionsChange(newOptions);
      }
    } catch (error) {
      console.error('Error saving screen options:', error);
      const errorMessage = error instanceof Error ? error.message : '保存失败';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 处理列显示/隐藏
  const handleColumnToggle = (columnKey: string, checked: boolean) => {
    const newColumns = checked
      ? [...(options.columns || []), columnKey]
      : (options.columns || []).filter(key => key !== columnKey);
    
    const newOptions = { ...options, columns: newColumns };
    setOptions(newOptions);
    saveOptions(newOptions);
  };

  // 处理每页数量变化
  const handlePerPageChange = (value: string) => {
    const perPage = parseInt(value);
    const newOptions = { ...options, per_page: perPage };
    setOptions(newOptions);
    saveOptions(newOptions);
  };

  // 处理侧边栏显示/隐藏
  const handleSidebarToggle = (checked: boolean) => {
    const newOptions = { ...options, sidebar_visible: checked };
    setOptions(newOptions);
    saveOptions(newOptions);
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2"
      >
        <Settings className="w-4 h-4" />
        <span>屏幕选项</span>
      </Button>

      {isOpen && (
        <>
          {/* 遮罩层 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          {/* 面板 */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-white border rounded-lg shadow-lg z-50 p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold text-gray-900">屏幕选项</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(false)}
                className="h-6 w-6 p-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="space-y-4">
              {/* 列显示控制 */}
              {availableColumns.length > 0 && (
                <div>
                  <Label className="text-sm font-medium text-gray-700 mb-2 block">
                    显示列
                  </Label>
                  <div className="space-y-2">
                    {availableColumns.map((column) => (
                      <div key={column.key} className="flex items-center space-x-2">
                        <Checkbox
                          id={`column-${column.key}`}
                          checked={(options.columns || []).includes(column.key)}
                          onCheckedChange={(checked) => 
                            handleColumnToggle(column.key, checked as boolean)
                          }
                        />
                        <Label
                          htmlFor={`column-${column.key}`}
                          className="text-sm text-gray-700 cursor-pointer"
                        >
                          {column.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 每页显示数量 */}
              <div>
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  每页显示数量
                </Label>
                <Select
                  value={String(options.per_page)}
                  onValueChange={handlePerPageChange}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* 侧边栏显示 */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="sidebar-visible"
                  checked={options.sidebar_visible}
                  onCheckedChange={(checked) => 
                    handleSidebarToggle(checked as boolean)
                  }
                />
                <Label
                  htmlFor="sidebar-visible"
                  className="text-sm text-gray-700 cursor-pointer"
                >
                  显示侧边栏
                </Label>
              </div>
            </div>

            {/* 保存按钮 */}
            <div className="mt-4 pt-4 border-t">
              <Button
                size="sm"
                className="w-full"
                onClick={() => setIsOpen(false)}
                disabled={loading}
              >
                {loading ? '保存中...' : '完成'}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
