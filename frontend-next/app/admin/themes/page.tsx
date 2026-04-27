/**
 * 主题管理后台 - 支持主题预览、激活、上传、配置
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {Alert, AlertDescription} from '@/components/ui/alert';
import apiClient from '@/lib/api-client';
import {Check, Eye, Image as ImageIcon, Settings, Trash2, Upload, X} from 'lucide-react';

interface Theme {
  id: number | null;
  name: string;
  slug: string;
  version: string;
  description: string;
  author: string;
  author_url: string;
  theme_url: string;
  screenshot: string;
  is_active: boolean;
  is_installed: boolean;
  settings?: Record<string, any>;
  supports?: string[];
  created_at?: string;
  updated_at?: string;
}

const ThemeManagement = () => {
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 对话框状态
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<Theme | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');

  useEffect(() => {
    loadThemes();
  }, []);

  // 加载主题列表
  const loadThemes = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/themes');

      if (response.success && response.data) {
        setThemes((response.data as any).themes || []);
      }
    } catch (err: any) {
      console.error('Failed to load themes:', err);
      setError('加载主题失败');
    } finally {
      setLoading(false);
    }
  };

  // 上传主题
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.zip')) {
      setError('只支持ZIP格式的主题包');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/api/v1/themes/upload', formData);

      if (response.success) {
        loadThemes();
        alert('主题上传成功');
      } else {
        setError(response.error || '上传失败');
      }
    } catch (err: any) {
      console.error('Failed to upload theme:', err);
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
      // 清空input
      e.target.value = '';
    }
  };

  // 检查并修复主题
  const handleScanAndFix = async () => {
    if (!confirm('确定要扫描主题目录并修复数据库记录吗？\n这将添加所有在文件系统中存在但未在数据库中的主题。')) {
      return;
    }

    try {
      setScanning(true);
      setError(null);

      const response = await apiClient.post('/api/v1/themes/scan-and-fix');

      if (response.success) {
        const data = response.data as any;
        await loadThemes();
        
        let message = data.message;
        if (data.added_themes && data.added_themes.length > 0) {
          message += '\n\n新增的主题：\n' + data.added_themes.map((t: any) => `- ${t.name} (${t.slug})`).join('\n');
        }
        
        alert(message);
      } else {
        setError(response.error || '扫描失败');
      }
    } catch (err: any) {
      console.error('Failed to scan themes:', err);
      setError(err.message || '扫描失败');
    } finally {
      setScanning(false);
    }
  };

  // 激活主题
  const handleActivate = async (theme: Theme) => {
    if (!confirm(`确定要激活主题 "${theme.name}" 吗？`)) return;

    try {
        console.log('[ThemeManagement] 开始激活主题:', theme.slug);
      let response;

      if (!theme.is_installed && theme.id === null) {
        // 未安装的主题，先安装
          console.log('[ThemeManagement] 主题未安装，先安装...');
        response = await apiClient.post('/api/v1/themes/install', {
          slug: theme.slug
        });
        
        if (!response.success) {
          setError(response.error || '安装失败');
          return;
        }

          console.log('[ThemeManagement] 安装成功，重新加载主题列表');
        await loadThemes();
      }

      // 激活主题
        console.log('[ThemeManagement] 调用激活API:', `/api/v1/themes/${theme.slug}/activate`);
      response = await apiClient.post(`/api/v1/themes/${theme.slug}/activate`);
        console.log('[ThemeManagement] API响应:', response);

      if (response.success) {
          console.log('[ThemeManagement] 激活成功，重新加载主题列表');
        await loadThemes();
      } else {
          console.error('[ThemeManagement] 激活失败:', response.error);
        setError(response.error || '激活失败');
      }
    } catch (err: any) {
        console.error('[ThemeManagement] 激活主题异常:', err);
      setError(err.message || '激活失败');
    }
  };

  // 停用主题（切换到默认主题）
  const handleDeactivate = async (theme: Theme) => {
    if (!confirm(`确定要停用主题 "${theme.name}" 吗？将切换到默认主题。`)) return;

    try {
      const response = await apiClient.post(`/api/v1/themes/${theme.slug}/deactivate`);

      if (response.success) {
        loadThemes();
      } else {
        setError(response.error || '停用失败');
      }
    } catch (err: any) {
      console.error('Failed to deactivate theme:', err);
      setError(err.message || '停用失败');
    }
  };

  // 删除主题
  const handleDelete = async (theme: Theme) => {
    if (!theme.id) {
      setError('该主题未安装，无法删除');
      return;
    }

    if (!confirm(`确定要删除主题 "${theme.name}" 吗？此操作不可恢复！`)) return;

    try {
      const response = await apiClient.delete(`/api/v1/themes/${theme.id}`);

      if (response.success) {
        loadThemes();
      } else {
        setError(response.error || '删除失败');
      }
    } catch (err: any) {
      console.error('Failed to delete theme:', err);
      setError(err.message || '删除失败');
    }
  };

  // 预览主题
  const handlePreview = (theme: Theme) => {
    setCurrentTheme(theme);
    setPreviewUrl(getScreenshotUrl(theme));
    setShowPreviewDialog(true);
  };

  // 配置主题
  const handleConfigure = (theme: Theme) => {
    setCurrentTheme(theme);
    setShowConfigDialog(true);
  };

  // 获取主题截图URL
  const getScreenshotUrl = (theme: Theme | null) => {
    if (!theme || !theme.screenshot) {
      return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzljYTNhZiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuaXoOazleWKoOi9veWbvueJhzwvdGV4dD48L3N2Zz4=';
    }

    // 如果是相对路径，转换为绝对路径
    if (theme.screenshot.startsWith('/')) {
      return theme.screenshot;
    }
    return theme.screenshot;
  };

  return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* 页面标题和操作栏 */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              主题管理
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              管理和自定义网站外观
            </p>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2">
            {/* 扫描修复按钮 */}
            <Button 
              variant="outline" 
              onClick={handleScanAndFix}
              disabled={scanning}
            >
              {scanning ? (
                <>
                  <Upload className="w-4 h-4 mr-2 animate-spin"/>
                  扫描中...
                </>
              ) : (
                <>
                  <Settings className="w-4 h-4 mr-2"/>
                  检查并修复主题
                </>
              )}
            </Button>

            {/* 上传按钮 */}
            <input
                type="file"
                accept=".zip"
                onChange={handleUpload}
                disabled={uploading}
                className="hidden"
                id="theme-upload"
            />
            <label htmlFor="theme-upload">
              <Button disabled={uploading} className="cursor-pointer">
                {uploading ? (
                    <>
                      <Upload className="w-4 h-4 mr-2 animate-spin"/>
                      上传中...
                    </>
                ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2"/>
                      上传主题
                    </>
                )}
              </Button>
            </label>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertDescription>{error}</AlertDescription>
              <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setError(null)}
                  className="absolute right-2 top-2"
              >
                <X className="w-4 h-4"/>
              </Button>
            </Alert>
        )}

        {/* 主题列表 */}
        {loading ? (
            <div className="text-center py-8">加载中...</div>
        ) : themes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <ImageIcon className="w-16 h-16 mx-auto mb-4 text-gray-400"/>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  暂无主题
                </h3>
                <p className="text-gray-500 mb-4">
                  上传一个主题包开始使用
                </p>
                <label htmlFor="theme-upload">
                  <Button className="cursor-pointer">
                    <Upload className="w-4 h-4 mr-2"/>
                    上传主题
                  </Button>
                </label>
              </CardContent>
            </Card>
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {themes.map((theme) => (
                  <Card
                      key={theme.slug}
                      className={`overflow-hidden transition-all hover:shadow-lg ${
                          theme.is_active
                              ? 'ring-2 ring-blue-500 dark:ring-blue-400'
                              : ''
                      }`}
                  >
                    {/* 主题截图 */}
                    <div className="relative aspect-video bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <img
                          src={getScreenshotUrl(theme)}
                          alt={theme.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzljYTNhZiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuaXoOazleWKoOi9veWbvueJhzwvdGV4dD48L3N2Zz4=';
                          }}
                      />

                      {/* 激活状态徽章 */}
                      {theme.is_active && (
                          <Badge className="absolute top-2 right-2 bg-green-500 hover:bg-green-600">
                            <Check className="w-3 h-3 mr-1"/>
                            当前主题
                          </Badge>
                      )}

                      {/* 悬停遮罩 */}
                      <div
                          className="absolute inset-0 bg-black/50 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                        <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handlePreview(theme)}
                        >
                          <Eye className="w-4 h-4"/>
                        </Button>
                        {theme.is_installed && (
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => handleConfigure(theme)}
                            >
                              <Settings className="w-4 h-4"/>
                            </Button>
                        )}
                      </div>
                    </div>

                    {/* 主题信息 */}
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-lg truncate">{theme.name}</CardTitle>
                          <CardDescription className="text-sm mt-1">
                            v{theme.version} · by {theme.author}
                          </CardDescription>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent className="pb-3">
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {theme.description || '暂无描述'}
                      </p>

                      {/* 支持的标签 */}
                      {theme.supports && theme.supports.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {theme.supports.slice(0, 3).map((tag, index) => (
                                <Badge key={index} variant="outline" className="text-xs">
                                  {tag}
                                </Badge>
                            ))}
                            {theme.supports.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                  +{theme.supports.length - 3}
                                </Badge>
                            )}
                          </div>
                      )}
                    </CardContent>

                    {/* 操作按钮 */}
                    <CardFooter className="flex gap-2 pt-2">
                      {!theme.is_active ? (
                          <Button
                              size="sm"
                              className="flex-1"
                              onClick={() => handleActivate(theme)}
                          >
                            {theme.is_installed ? '激活' : '安装并激活'}
                          </Button>
                      ) : (
                          <Button
                              size="sm"
                              variant="outline"
                              className="flex-1"
                              onClick={() => handleDeactivate(theme)}
                          >
                            停用
                          </Button>
                      )}

                      {theme.is_installed && (
                          <>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleConfigure(theme)}
                            >
                              <Settings className="w-4 h-4"/>
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDelete(theme)}
                                className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="w-4 h-4"/>
                            </Button>
                          </>
                      )}
                    </CardFooter>
                  </Card>
              ))}
            </div>
        )}

        {/* 预览对话框 */}
        <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>{currentTheme?.name} - 预览</DialogTitle>
              <DialogDescription>
                {currentTheme?.description}
              </DialogDescription>
            </DialogHeader>

            <div className="aspect-video bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
              <img
                  src={previewUrl || getScreenshotUrl(currentTheme!)}
                  alt={currentTheme?.name}
                  className="w-full h-full object-contain"
              />
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowPreviewDialog(false)}>
                关闭
              </Button>
              {currentTheme && !currentTheme.is_active && (
                  <Button onClick={() => {
                    handleActivate(currentTheme);
                    setShowPreviewDialog(false);
                  }}>
                    激活此主题
                  </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 配置对话框（简化版） */}
        <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>配置主题</DialogTitle>
              <DialogDescription>
                {currentTheme?.name} 的配置选项
              </DialogDescription>
            </DialogHeader>

            <div className="py-4">
              <Alert>
                <AlertDescription>
                  主题配置功能正在开发中。您可以通过编辑主题的配置文件来自定义主题。
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button onClick={() => setShowConfigDialog(false)}>
                关闭
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
  );
};

export default ThemeManagement;
