'use client';

/**
 * 主题可视化定制器
 * 提供实时预览和配置管理功能
 */

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Label} from '@/components/ui/label';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Switch} from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import {ColorPicker} from '@/components/ColorPicker';
import {apiClient} from '@/lib/api-client';
import {Code, History, Monitor, RotateCcw, Save, Smartphone, Tablet} from 'lucide-react';

interface ThemeConfig {
    colors: {
        primary: string;
        secondary: string;
        accent: string;
        background: string;
        foreground: string;
        [key: string]: string; // 允许额外的颜色属性
    };
    fonts: Record<string, string>;
    layout: {
        sidebarPosition?: string;
        contentWidth?: string;
        showSidebar?: boolean;
        headerStyle?: string;
        footerStyle?: string;
        [key: string]: any;
    };
    typography: {
        fontFamily?: string;
        fontSize?: string;
        lineHeight?: number;
        codeFont?: string;
        [key: string]: any;
    };
    components: Record<string, any>;
    header: Record<string, any>;
    footer: Record<string, any>;
    homepage: Record<string, any>;
    article: Record<string, any>;
    features: Record<string, any>;
}

export default function ThemeCustomizerPage() {
    const [themeSlug, setThemeSlug] = useState('default');
    const [config, setConfig] = useState<ThemeConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [previewCss, setPreviewCss] = useState('');
    const [activeTab, setActiveTab] = useState('colors');
    
    // 新增状态
    const [previewDevice, setPreviewDevice] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
    const [showHistoryDialog, setShowHistoryDialog] = useState(false);
    const [showCssEditorDialog, setShowCssEditorDialog] = useState(false);
    const [customCss, setCustomCss] = useState('');
    const [versionHistory, setVersionHistory] = useState<any[]>([]);
    const [logoFile, setLogoFile] = useState<File | null>(null);
    const [logoPreview, setLogoPreview] = useState<string>('');

    // 加载主题配置
    useEffect(() => {
        loadThemeConfig();
    }, [themeSlug]);

    const loadThemeConfig = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get(`/theme-customizer/config/${themeSlug}`);

            if (response.success) {
                setConfig((response.data as any).config as ThemeConfig);
            }
        } catch (error) {
            console.error('Failed to load theme config:', error);
        } finally {
            setLoading(false);
        }
    };

    // 生成预览CSS
    const generatePreview = async (updatedConfig?: ThemeConfig) => {
        try {
            const response = await apiClient.post('/theme-customizer/preview/css', {
                config: updatedConfig || config,
            });

            if (response.success) {
                setPreviewCss((response.data as any).css);
            }
        } catch (error) {
            console.error('Failed to generate preview:', error);
        }
    };

    // 更新配置
    const updateConfig = (section: keyof ThemeConfig, key: string, value: any) => {
        if (!config) return;

        const newConfig = {...config};
        const sectionData = {...(newConfig[section] || {})} as any;
        sectionData[key] = value;
        (newConfig as any)[section] = sectionData;

        setConfig(newConfig);
        generatePreview(newConfig);
    };

    // 保存配置
    const saveConfig = async () => {
        if (!config) return;

        try {
            setSaving(true);

            // 将配置转换为扁平格式
            const updates = flattenConfig(config);

            const response = await apiClient.put(`/theme-customizer/config/${themeSlug}`, {
                updates,
            });

            if (response.success) {
                alert('配置已保存!');
            } else {
                alert('保存失败: ' + ((response as any).error || '未知错误'));
            }
        } catch (error) {
            console.error('Failed to save config:', error);
            alert('保存失败,请重试');
        } finally {
            setSaving(false);
        }
    };

    // 应用预设颜色方案
    const applyColorPreset = async (presetName: string) => {
        try {
            const response = await apiClient.get('/theme-customizer/presets');

            if (response.success && (response.data as any)[presetName]) {
                const preset = (response.data as any)[presetName];
                updateConfig('colors', 'primary', preset.colors.primary);
                updateConfig('colors', 'secondary', preset.colors.secondary);
                updateConfig('colors', 'accent', preset.colors.accent);

                if (preset.colors.background) {
                    updateConfig('colors', 'background', preset.colors.background);
                }
                if (preset.colors.foreground) {
                    updateConfig('colors', 'foreground', preset.colors.foreground);
                }
            }
        } catch (error) {
            console.error('Failed to apply preset:', error);
        }
    };

    // 导出配置
    const exportConfig = async () => {
        try {
            const response = await apiClient.get(`/theme-customizer/export/${themeSlug}`);

            if (response.success) {
                const blob = new Blob([(response.data as any).config], {type: 'application/json'});
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${themeSlug}-config.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Failed to export config:', error);
        }
    };

    // Logo 上传处理
    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setLogoFile(file);
        
        // 创建预览
        const reader = new FileReader();
        reader.onloadend = () => {
            setLogoPreview(reader.result as string);
        };
        reader.readAsDataURL(file);

        // 上传到服务器并更新配置
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('folder', 'theme-assets');

            // 注意：apiClient.post 只接受 2 个参数，不能传递自定义 headers
            // FormData 会自动设置 Content-Type 为 multipart/form-data
            const response = await apiClient.post('/media/upload', formData);
            
            if (response.success && response.data) {
                const mediaUrl = (response.data as any).url || (response.data as any).path;
                updateConfig('header', 'logo_url', mediaUrl);
            }
        } catch (error) {
            console.error('Failed to upload logo:', error);
        }
    };

    // 加载版本历史
    const loadVersionHistory = async () => {
        try {
            const response = await apiClient.get(`/theme-customizer/history/${themeSlug}`);
            if (response.success) {
                setVersionHistory((response.data as any).versions || []);
            }
        } catch (error) {
            console.error('Failed to load version history:', error);
        }
    };

    // 恢复到指定版本
    const restoreVersion = async (versionId: number) => {
        if (!confirm('确定要恢复到此版本吗？当前未保存的更改将丢失。')) return;
        
        try {
            const response = await apiClient.post(`/theme-customizer/restore/${themeSlug}`, {
                version_id: versionId
            });
            
            if (response.success) {
                loadThemeConfig();
                setShowHistoryDialog(false);
                alert('版本已恢复！');
            }
        } catch (error) {
            console.error('Failed to restore version:', error);
        }
    };

    // 保存自定义 CSS
    const saveCustomCss = async () => {
        try {
            const response = await apiClient.put(`/theme-customizer/custom-css/${themeSlug}`, {
                css: customCss
            });
            
            if (response.success) {
                alert('自定义 CSS 已保存！');
                setShowCssEditorDialog(false);
            }
        } catch (error) {
            console.error('Failed to save custom CSS:', error);
        }
    };

    // 加载自定义 CSS
    const loadCustomCss = async () => {
        try {
            const response = await apiClient.get(`/theme-customizer/custom-css/${themeSlug}`);

            if (response.success) {
                setCustomCss((response.data as any).css || '');
            }
        } catch (error) {
            console.error('Failed to load custom CSS:', error);
        }
    };

    // 辅助函数: 展平配置
    const flattenConfig = (obj: any, prefix = ''): Record<string, any> => {
        const result: Record<string, any> = {};

        for (const key in obj) {
            const value = obj[key];
            const newKey = prefix ? `${prefix}.${key}` : key;

            if (typeof value === 'object' && !Array.isArray(value)) {
                Object.assign(result, flattenConfig(value, newKey));
            } else {
                result[newKey] = value;
            }
        }

        return result;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        );
    }

    if (!config) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <p className="text-gray-600 dark:text-gray-400">无法加载主题配置</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* 顶部工具栏 */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">主题定制器</h1>

                    <div className="flex gap-2">
                        <Button variant="outline" onClick={exportConfig}>
                            导出配置
                        </Button>
                        <Button onClick={saveConfig} disabled={saving}>
                            {saving ? '保存中...' : '保存配置'}
                        </Button>
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* 左侧: 配置面板 */}
                    <div className="lg:col-span-2 space-y-6">
                        <Tabs value={activeTab} onValueChange={setActiveTab}>
                            <TabsList className="grid grid-cols-5 w-full">
                                <TabsTrigger value="colors">颜色</TabsTrigger>
                                <TabsTrigger value="fonts">字体</TabsTrigger>
                                <TabsTrigger value="layout">布局</TabsTrigger>
                                <TabsTrigger value="components">组件</TabsTrigger>
                                <TabsTrigger value="other">其他</TabsTrigger>
                            </TabsList>

                            {/* 颜色配置 */}
                            <TabsContent value="colors" className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>颜色方案</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <Label>主色调</Label>
                                                <ColorPicker
                                                    value={config.colors.primary}
                                                    onChange={(value) => updateConfig('colors', 'primary', value)}
                                                />
                                            </div>
                                            <div>
                                                <Label>次要色</Label>
                                                <ColorPicker
                                                    value={config.colors.secondary}
                                                    onChange={(value) => updateConfig('colors', 'secondary', value)}
                                                />
                                            </div>
                                            <div>
                                                <Label>强调色</Label>
                                                <ColorPicker
                                                    value={config.colors.accent}
                                                    onChange={(value) => updateConfig('colors', 'accent', value)}
                                                />
                                            </div>
                                            <div>
                                                <Label>背景色</Label>
                                                <ColorPicker
                                                    value={config.colors.background}
                                                    onChange={(value) => updateConfig('colors', 'background', value)}
                                                />
                                            </div>
                                        </div>

                                        <div className="pt-4 border-t">
                                            <Label className="mb-2 block">快速预设</Label>
                                            <div className="flex gap-2 flex-wrap">
                                                {['default', 'dark', 'ocean', 'sunset', 'forest', 'purple'].map((preset) => (
                                                    <Button
                                                        key={preset}
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() => applyColorPreset(preset)}
                                                    >
                                                        {preset}
                                                    </Button>
                                                ))}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            {/* 字体配置 */}
                            <TabsContent value="fonts" className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>字体设置</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <Label>标题字体</Label>
                                            <Input
                                                value={config.fonts.heading}
                                                onChange={(e) => updateConfig('fonts', 'heading', e.target.value)}
                                                placeholder="Inter, system-ui, sans-serif"
                                            />
                                        </div>
                                        <div>
                                            <Label>正文字体</Label>
                                            <Input
                                                value={config.fonts.body}
                                                onChange={(e) => updateConfig('fonts', 'body', e.target.value)}
                                                placeholder="Inter, system-ui, sans-serif"
                                            />
                                        </div>
                                        <div>
                                            <Label>等宽字体</Label>
                                            <Input
                                                value={config.fonts.mono}
                                                onChange={(e) => updateConfig('fonts', 'mono', e.target.value)}
                                                placeholder="Fira Code, monospace"
                                            />
                                        </div>
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            {/* 布局配置 */}
                            <TabsContent value="layout" className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>布局设置</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <Label>侧边栏位置</Label>
                                            <Select
                                                value={config.layout.sidebar_position}
                                                onValueChange={(value) => updateConfig('layout', 'sidebar_position', value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue/>
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="left">左侧</SelectItem>
                                                    <SelectItem value="right">右侧</SelectItem>
                                                    <SelectItem value="none">隐藏</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div>
                                            <Label>内容宽度</Label>
                                            <Select
                                                value={config.layout.content_width}
                                                onValueChange={(value) => updateConfig('layout', 'content_width', value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue/>
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="max-w-3xl">窄 (768px)</SelectItem>
                                                    <SelectItem value="max-w-4xl">中等 (896px)</SelectItem>
                                                    <SelectItem value="max-w-5xl">宽 (1024px)</SelectItem>
                                                    <SelectItem value="max-w-7xl">超宽 (1280px)</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            {/* 组件配置 */}
                            <TabsContent value="components" className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>组件样式</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <Label>圆角大小</Label>
                                            <Input
                                                value={config.components.rounded_corners}
                                                onChange={(e) => updateConfig('components', 'rounded_corners', e.target.value)}
                                                placeholder="0.5rem"
                                            />
                                        </div>

                                        <div>
                                            <Label>阴影风格</Label>
                                            <Select
                                                value={config.components.shadow_style}
                                                onValueChange={(value) => updateConfig('components', 'shadow_style', value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue/>
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="none">无</SelectItem>
                                                    <SelectItem value="small">小</SelectItem>
                                                    <SelectItem value="medium">中</SelectItem>
                                                    <SelectItem value="large">大</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            {/* 其他配置 */}
                            <TabsContent value="other" className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Logo 和图标</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <Label>网站 Logo</Label>
                                            <div className="mt-2 flex items-center gap-4">
                                                {logoPreview && (
                                                    <img 
                                                        src={logoPreview} 
                                                        alt="Logo Preview" 
                                                        className="h-12 w-auto border rounded"
                                                    />
                                                )}
                                                <Input
                                                    type="file"
                                                    accept="image/*"
                                                    onChange={handleLogoUpload}
                                                    className="max-w-xs"
                                                />
                                            </div>
                                            <p className="text-xs text-gray-500 mt-1">
                                                建议尺寸: 200x50px, 支持 PNG/JPG/SVG
                                            </p>
                                        </div>

                                        <div>
                                            <Label>Favicon</Label>
                                            <Input
                                                type="file"
                                                accept="image/x-icon,image/png"
                                                className="max-w-xs"
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                建议尺寸: 32x32px 或 64x64px
                                            </p>
                                        </div>
                                    </CardContent>
                                </Card>

                                <Card>
                                    <CardHeader>
                                        <CardTitle>文章页设置</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <Label>显示作者信息</Label>
                                            <Switch
                                                checked={config.article.show_author}
                                                onCheckedChange={(checked) => updateConfig('article', 'show_author', checked)}
                                            />
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <Label>显示目录</Label>
                                            <Switch
                                                checked={config.article.show_toc}
                                                onCheckedChange={(checked) => updateConfig('article', 'show_toc', checked)}
                                            />
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <Label>显示分享按钮</Label>
                                            <Switch
                                                checked={config.article.show_share_buttons}
                                                onCheckedChange={(checked) => updateConfig('article', 'show_share_buttons', checked)}
                                            />
                                        </div>
                                    </CardContent>
                                </Card>
                            </TabsContent>
                        </Tabs>
                    </div>

                    {/* 右侧: 实时预览 */}
                    <div className="lg:col-span-1">
                        <div className="sticky top-24 space-y-4">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center justify-between">
                                        <span>实时预览</span>
                                        <div className="flex gap-1">
                                            <Button
                                                variant={previewDevice === 'desktop' ? 'default' : 'outline'}
                                                size="sm"
                                                onClick={() => setPreviewDevice('desktop')}
                                                title="桌面端"
                                            >
                                                <Monitor className="w-4 h-4"/>
                                            </Button>
                                            <Button
                                                variant={previewDevice === 'tablet' ? 'default' : 'outline'}
                                                size="sm"
                                                onClick={() => setPreviewDevice('tablet')}
                                                title="平板"
                                            >
                                                <Tablet className="w-4 h-4"/>
                                            </Button>
                                            <Button
                                                variant={previewDevice === 'mobile' ? 'default' : 'outline'}
                                                size="sm"
                                                onClick={() => setPreviewDevice('mobile')}
                                                title="手机"
                                            >
                                                <Smartphone className="w-4 h-4"/>
                                            </Button>
                                        </div>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="border rounded-lg overflow-hidden bg-white dark:bg-gray-800">
                                        {/* iframe 预览 */}
                                        <div className={`mx-auto transition-all duration-300 ${
                                            previewDevice === 'desktop' ? 'w-full' :
                                            previewDevice === 'tablet' ? 'w-[768px]' :
                                            'w-[375px]'
                                        }`}>
                                            <iframe
                                                src={`/preview?theme=${themeSlug}`}
                                                className="w-full h-[600px] border-0"
                                                title="Theme Preview"
                                                style={{
                                                    transform: previewDevice !== 'desktop' ? 'scale(0.9)' : 'none',
                                                    transformOrigin: 'top center'
                                                }}
                                            />
                                        </div>
                                        
                                        {/* 备用预览（当 iframe 不可用时） */}
                                        <style dangerouslySetInnerHTML={{__html: previewCss}}/>
                                        <div className="p-4 space-y-4 border-t">
                                            <h2 className="text-2xl font-bold" style={{color: config.colors.primary}}>
                                                示例文章标题
                                            </h2>
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                                2024-01-15 · 阅读时间 5分钟
                                            </p>
                                            <div className="prose dark:prose-invert max-w-none">
                                                <p>这是一段示例文本，用于展示当前的主题配置效果。</p>
                                                <Button style={{backgroundColor: config.colors.primary}}>
                                                    主要按钮
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>快捷操作</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-2">
                                    <Button variant="outline" className="w-full" onClick={() => generatePreview()}>
                                        <RotateCcw className="w-4 h-4 mr-2"/>
                                        刷新预览
                                    </Button>
                                    <Button variant="outline" className="w-full" onClick={loadThemeConfig}>
                                        <RotateCcw className="w-4 h-4 mr-2"/>
                                        重置更改
                                    </Button>
                                    <Button variant="outline" className="w-full" onClick={() => {
                                        loadCustomCss();
                                        setShowCssEditorDialog(true);
                                    }}>
                                        <Code className="w-4 h-4 mr-2"/>
                                        自定义 CSS
                                    </Button>
                                    <Button variant="outline" className="w-full" onClick={() => {
                                        loadVersionHistory();
                                        setShowHistoryDialog(true);
                                    }}>
                                        <History className="w-4 h-4 mr-2"/>
                                        版本历史
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </div>
            </div>

            {/* 自定义 CSS 编辑器对话框 */}
            <Dialog open={showCssEditorDialog} onOpenChange={setShowCssEditorDialog}>
                <DialogContent className="max-w-4xl">
                    <DialogHeader>
                        <DialogTitle>自定义 CSS</DialogTitle>
                        <DialogDescription>
                            在此输入自定义 CSS 代码，将覆盖主题默认样式
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4">
                        <Textarea
                            value={customCss}
                            onChange={(e) => setCustomCss(e.target.value)}
                            placeholder="/* 在此输入您的自定义 CSS */\n.example {\n  color: red;\n}" 
                            className="font-mono text-sm min-h-[400px]"
                        />
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowCssEditorDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={saveCustomCss}>
                            <Save className="w-4 h-4 mr-2"/>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 版本历史对话框 */}
            <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>配置版本历史</DialogTitle>
                        <DialogDescription>
                            查看和恢复之前的配置版本
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4 max-h-[400px] overflow-y-auto">
                        {versionHistory.length === 0 ? (
                            <p className="text-center text-gray-500 py-8">暂无版本历史</p>
                        ) : (
                            <div className="space-y-2">
                                {versionHistory.map((version) => (
                                    <div
                                        key={version.id}
                                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                                    >
                                        <div>
                                            <p className="font-medium">{version.version_name || `版本 ${version.id}`}</p>
                                            <p className="text-xs text-gray-500">
                                                {new Date(version.created_at).toLocaleString('zh-CN')}
                                            </p>
                                        </div>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => restoreVersion(version.id)}
                                        >
                                            <RotateCcw className="w-4 h-4 mr-1"/>
                                            恢复
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button onClick={() => setShowHistoryDialog(false)}>
                            关闭
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
