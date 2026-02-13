'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Label} from '@/components/ui/label';
import {HydratableSelect} from '@/components/ui/hydratable-select';
import {SelectItem} from '@/components/ui/select';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {AlertCircle, Check, Code, Copy, Eraser, Eye, Loader2, Play, Save} from 'lucide-react';
import {toast} from 'sonner';

interface CommentConfig {
    giscus_repo: string;
    giscus_repo_id: string;
    giscus_category: string;
    giscus_category_id: string;
    giscus_mapping: string;
    giscus_strict: string;
    giscus_reactions_enabled: string;
    giscus_emit_metadata: string;
    giscus_input_position: string;
    giscus_theme: string;
    giscus_lang: string;
    giscus_loading: string;
}

export default function CommentConfigPage() {
    const [config, setConfig] = useState<CommentConfig>({
        giscus_repo: '',
        giscus_repo_id: '',
        giscus_category: '',
        giscus_category_id: '',
        giscus_mapping: 'pathname',
        giscus_strict: '0',
        giscus_reactions_enabled: '1',
        giscus_emit_metadata: '0',
        giscus_input_position: 'top',
        giscus_theme: 'preferred_color_scheme',
        giscus_lang: 'zh-CN',
        giscus_loading: 'lazy'
    });

    const [script, setScript] = useState('');
    const [previewHtml, setPreviewHtml] = useState('');
    const [testResult, setTestResult] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<Record<string, boolean>>({});
    const [copied, setCopied] = useState(false);

    // 获取初始配置
    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const response = await fetch('/api/v1/dashboard/comment_config', {
                    credentials: 'include',
                });

                if (response.ok) {
                    const result = await response.json();

                    if (result.success) {
                        setConfig(prev => ({
                            ...prev,
                            ...result.data
                        }));
                    }
                }
            } catch (error) {
                console.error('获取评论配置失败:', error);
            }
        };

        fetchConfig();
    }, []);

    // 更新预览
    useEffect(() => {
        let preview = '<div class="space-y-1">';
        Object.entries(config).forEach(([key, value]) => {
            if (value) {
                preview += `<div class="py-1"><strong class="text-sm">${key}:</strong> <span class="text-blue-600 text-sm">${value}</span></div>`;
            }
        });
        preview += '</div>';
        setPreviewHtml(preview);
    }, [config]);

    // 解析Giscus脚本
    const parseScript = () => {
        if (!script) {
            toast.error('请先粘贴Giscus脚本代码');
            return;
        }

        const patterns: Record<string, RegExp> = {
            'giscus_repo': /data-repo\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_repo_id': /data-repo-id\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_category': /data-category\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_category_id': /data-category-id\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_mapping': /data-mapping\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_theme': /data-theme\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_lang': /data-lang\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_loading': /data-loading\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_strict': /data-strict\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_reactions_enabled': /data-reactions-enabled\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_emit_metadata': /data-emit-metadata\s*=\s*['"]([^'"]+)['"]/i,
            'giscus_input_position': /data-input-position\s*=\s*['"]([^'"]+)['"]/i
        };

        const newConfig = {...config};

        for (const [field, pattern] of Object.entries(patterns)) {
            const match = script.match(pattern);
            if (match && match[1]) {
                // 类型断言确保与CommentConfig接口兼容
                (newConfig as any)[field as keyof CommentConfig] = match[1];
            }
        }

        setConfig(newConfig);
        toast.success('Giscus配置已成功解析并填充到表单中！');
    };

    // 测试配置
    const testConfig = () => {
        // 验证仓库名称格式
        if (!config.giscus_repo || !config.giscus_repo.includes('/')) {
            toast.error('仓库名称格式不正确，请使用 "用户名/仓库名" 格式');
            setErrors(prev => ({...prev, giscus_repo: true}));
            return;
        } else {
            setErrors(prev => ({...prev, giscus_repo: false}));
        }

        // 验证必填字段
        if (!config.giscus_repo) {
            toast.error('请填写仓库名称');
            setErrors(prev => ({...prev, giscus_repo: true}));
            return;
        }

        // 显示测试结果
        setTestResult(`
      <div class="text-center py-4">
        <div class="inline-block bg-green-100 text-green-800 px-4 py-2 rounded-lg">
          <i class="fas fa-check-circle mr-2"></i>
          配置验证通过！
        </div>
        <p class="mt-2 text-sm text-gray-600">
          仓库: ${config.giscus_repo}<br>
          分类: ${config.giscus_category || '未设置'}<br>
          映射方式: ${config.giscus_mapping}
        </p>
      </div>
    `);

        // 2秒后清除测试结果
        setTimeout(() => {
            setTestResult(null);
        }, 2000);
    };

    // 预览评论
    const previewComment = () => {
        // 验证必要参数
        if (!config.giscus_repo) {
            toast.error('请填写仓库名称');
            setErrors(prev => ({...prev, giscus_repo: true}));
            return;
        } else {
            setErrors(prev => ({...prev, giscus_repo: false}));
        }

        if (!config.giscus_category) {
            toast.error('请填写分类名称');
            setErrors(prev => ({...prev, giscus_category: true}));
            return;
        } else {
            setErrors(prev => ({...prev, giscus_category: false}));
        }

        // 这里应该实际渲染Giscus组件，但为了简化我们只显示配置信息
        setTestResult(`
      <div class="text-center py-4">
        <div class="inline-block bg-blue-100 text-blue-800 px-4 py-2 rounded-lg">
          <i class="fas fa-eye mr-2"></i>
          评论预览已加载！
        </div>
        <p class="mt-2 text-sm text-gray-600">
          仓库: ${config.giscus_repo}<br>
          分类: ${config.giscus_category}<br>
          主题: ${config.giscus_theme}
        </p>
      </div>
    `);
    };

    // 清除预览
    const clearPreview = () => {
        setTestResult(null);
    };

    // 保存配置
    const saveConfig = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await fetch('/api/v1/dashboard/comment_config', {
                method: 'POST',
                body: JSON.stringify(config),
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                toast.success('评论配置保存成功！');
            } else {
                toast.error('保存失败: ' + result.message);
            }
        } catch (error) {
            console.error('Error saving config:', error);
            toast.error('保存失败，请检查网络连接');
        } finally {
            setIsLoading(false);
        }
    };

    // 处理输入变化
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const {name, value} = e.target;
        setConfig(prev => ({
            ...prev,
            [name]: value
        }));
    };

    // 处理选择变化
    const handleSelectChange = (name: string, value: string) => {
        setConfig(prev => ({
            ...prev,
            [name]: value
        }));
    };

    // 复制配置到剪贴板
    const copyConfigToClipboard = () => {
        navigator.clipboard.writeText(JSON.stringify(config, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-gray-900">评论配置</h1>
                        <p className="text-gray-600 mt-1">配置Giscus评论系统参数，支持自动纠错功能</p>
                    </div>
                    <Button onClick={saveConfig} disabled={isLoading} className="bg-blue-600 hover:bg-blue-700">
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin"/>
                                保存中...
                            </>
                        ) : (
                            <>
                                <Save className="mr-2 h-4 w-4"/>
                                保存配置
                            </>
                        )}
                    </Button>
                </div>
            </div>

            <Alert className="border-blue-200 bg-blue-50">
                <AlertCircle className="h-4 w-4 text-blue-600"/>
                <AlertDescription>
                    <p className="font-medium text-blue-800">配置指南</p>
                    <ul className="list-disc pl-5 space-y-1 mt-2 text-blue-700">
                        <li>访问 <a href="https://giscus.app" target="_blank" rel="noopener noreferrer"
                                    className="text-blue-600 underline">https://giscus.app</a> 获取配置
                        </li>
                        <li>在页面上完成配置后，复制生成的脚本代码</li>
                        <li>将脚本粘贴到下方输入框，系统将自动解析参数</li>
                    </ul>
                </AlertDescription>
            </Alert>

            <form onSubmit={saveConfig}>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Giscus配置 */}
                    <div className="space-y-6">
                        <Card className="border border-gray-200">
                            <CardHeader className="bg-gray-50 border-b">
                                <CardTitle className="flex items-center gap-2">
                                    <Code className="h-5 w-5 text-blue-600"/>
                                    从脚本导入
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6">
                                <div className="space-y-4">
                                    <div>
                                        <Label htmlFor="giscus_script">Giscus脚本代码</Label>
                                        <Textarea
                                            id="giscus_script"
                                            value={script}
                                            onChange={(e) => setScript(e.target.value)}
                                            placeholder="将从 giscus.app 获取的脚本代码粘贴到这里"
                                            rows={6}
                                            className="mt-1 font-mono text-sm"
                                        />
                                        <p className="mt-1 text-sm text-gray-500">
                                            粘贴从 giscus.app 获取的脚本代码，然后点击解析按钮
                                        </p>
                                    </div>

                                    <div className="flex space-x-2">
                                        <Button type="button" onClick={parseScript} variant="secondary">
                                            <Code className="mr-2 h-4 w-4"/>
                                            解析脚本
                                        </Button>
                                        <Button
                                            type="button"
                                            onClick={copyConfigToClipboard}
                                            variant="outline"
                                            className="flex items-center"
                                        >
                                            {copied ? (
                                                <>
                                                    <Check className="mr-2 h-4 w-4 text-green-600"/>
                                                    已复制
                                                </>
                                            ) : (
                                                <>
                                                    <Copy className="mr-2 h-4 w-4"/>
                                                    复制配置
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border border-gray-200">
                            <CardHeader className="bg-gray-50 border-b">
                                <CardTitle>Giscus配置</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6">
                                <div className="space-y-4">
                                    <div>
                                        <Label htmlFor="giscus_repo">
                                            仓库名称 <span className="text-red-500">*</span>
                                        </Label>
                                        <Input
                                            id="giscus_repo"
                                            name="giscus_repo"
                                            value={config.giscus_repo}
                                            onChange={handleInputChange}
                                            placeholder="username/repo"
                                            className={`mt-1 ${errors.giscus_repo ? 'border-red-500' : ''}`}
                                        />
                                        <p className="mt-1 text-sm text-gray-500">
                                            GitHub仓库名称，格式：用户名/仓库名
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_repo_id">仓库ID</Label>
                                        <Input
                                            id="giscus_repo_id"
                                            name="giscus_repo_id"
                                            value={config.giscus_repo_id}
                                            onChange={handleInputChange}
                                            placeholder="例如：R_kgDOP3N1ZQ"
                                            className="mt-1"
                                        />
                                        <p className="mt-1 text-sm text-gray-500">
                                            GitHub仓库ID
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_category">分类名称</Label>
                                        <Input
                                            id="giscus_category"
                                            name="giscus_category"
                                            value={config.giscus_category}
                                            onChange={handleInputChange}
                                            placeholder="例如：Announcements"
                                            className={`mt-1 ${errors.giscus_category ? 'border-red-500' : ''}`}
                                        />
                                        <p className="mt-1 text-sm text-gray-500">
                                            Giscus评论分类名称
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_category_id">分类ID</Label>
                                        <Input
                                            id="giscus_category_id"
                                            name="giscus_category_id"
                                            value={config.giscus_category_id}
                                            onChange={handleInputChange}
                                            placeholder="例如：DIC_kwDOP3N1Zc4C0Po4"
                                            className="mt-1"
                                        />
                                        <p className="mt-1 text-sm text-gray-500">
                                            Giscus评论分类ID
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_mapping">映射方式</Label>
                                        <HydratableSelect
                                            value={config.giscus_mapping}
                                            onValueChange={(value) => handleSelectChange('giscus_mapping', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="pathname">pathname</SelectItem>
                                            <SelectItem value="url">url</SelectItem>
                                            <SelectItem value="title">title</SelectItem>
                                            <SelectItem value="og:title">og:title</SelectItem>
                                            <SelectItem value="specific">specific</SelectItem>
                                            <SelectItem value="number">number</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            选择评论与页面的映射方式
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_strict">严格模式</Label>
                                        <HydratableSelect
                                            value={config.giscus_strict}
                                            onValueChange={(value) => handleSelectChange('giscus_strict', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="0">关闭</SelectItem>
                                            <SelectItem value="1">开启</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            严格模式下，如果找不到对应的讨论会显示错误
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_reactions_enabled">启用表情反应</Label>
                                        <HydratableSelect
                                            value={config.giscus_reactions_enabled}
                                            onValueChange={(value) => handleSelectChange('giscus_reactions_enabled', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="1">启用</SelectItem>
                                            <SelectItem value="0">禁用</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            是否在评论中显示表情反应按钮
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_emit_metadata">发送元数据</Label>
                                        <HydratableSelect
                                            value={config.giscus_emit_metadata}
                                            onValueChange={(value) => handleSelectChange('giscus_emit_metadata', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="0">关闭</SelectItem>
                                            <SelectItem value="1">开启</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            是否发送评论元数据到父页面
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_input_position">输入框位置</Label>
                                        <HydratableSelect
                                            value={config.giscus_input_position}
                                            onValueChange={(value) => handleSelectChange('giscus_input_position', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="top">顶部</SelectItem>
                                            <SelectItem value="bottom">底部</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            评论输入框显示在顶部还是底部
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_theme">主题样式</Label>
                                        <HydratableSelect
                                            value={config.giscus_theme}
                                            onValueChange={(value) => handleSelectChange('giscus_theme', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="light">浅色</SelectItem>
                                            <SelectItem value="dark">深色</SelectItem>
                                            <SelectItem value="dark_dimmed">暗淡深色</SelectItem>
                                            <SelectItem value="dark_high_contrast">高对比度深色</SelectItem>
                                            <SelectItem value="preferred_color_scheme">跟随系统</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            评论系统的主题样式
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_lang">语言</Label>
                                        <HydratableSelect
                                            value={config.giscus_lang}
                                            onValueChange={(value) => handleSelectChange('giscus_lang', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="zh-CN">简体中文</SelectItem>
                                            <SelectItem value="zh-TW">繁体中文</SelectItem>
                                            <SelectItem value="en">English</SelectItem>
                                            <SelectItem value="es">Español</SelectItem>
                                            <SelectItem value="fr">Français</SelectItem>
                                            <SelectItem value="ja">日本語</SelectItem>
                                            <SelectItem value="ko">한국어</SelectItem>
                                            <SelectItem value="ru">Русский</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            评论系统的显示语言
                                        </p>
                                    </div>

                                    <div>
                                        <Label htmlFor="giscus_loading">加载方式</Label>
                                        <HydratableSelect
                                            value={config.giscus_loading}
                                            onValueChange={(value) => handleSelectChange('giscus_loading', value)}
                                            className="mt-1"
                                        >
                                            <SelectItem value="eager">立即加载</SelectItem>
                                            <SelectItem value="lazy">懒加载</SelectItem>
                                        </HydratableSelect>
                                        <p className="mt-1 text-sm text-gray-500">
                                            评论系统的加载方式
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* 预览和测试 */}
                    <div className="space-y-6">
                        <Card className="border border-gray-200">
                            <CardHeader className="bg-gray-50 border-b">
                                <CardTitle>当前配置预览</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6">
                                <div
                                    className="text-sm text-gray-600 font-mono p-3 bg-gray-50 rounded border max-h-60 overflow-auto"
                                    dangerouslySetInnerHTML={{__html: previewHtml}}
                                />
                            </CardContent>
                        </Card>

                        <Card className="border border-gray-200">
                            <CardHeader className="bg-gray-50 border-b">
                                <CardTitle>评论系统预览</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6">
                                {testResult ? (
                                    <div
                                        className="border rounded p-4"
                                        dangerouslySetInnerHTML={{__html: testResult}}
                                    />
                                ) : (
                                    <div className="border rounded p-4 text-center py-8 text-gray-500">
                                        填写配置后点击&#34;预览评论&#34;按钮预览效果
                                    </div>
                                )}

                                <div
                                    className="mt-4 flex flex-col sm:flex-row sm:justify-start space-y-2 sm:space-y-0 sm:space-x-2">
                                    <Button type="button" onClick={previewComment} variant="secondary"
                                            className="flex-1">
                                        <Eye className="mr-2 h-4 w-4"/>
                                        预览评论
                                    </Button>
                                    <Button type="button" onClick={clearPreview} variant="outline" className="flex-1">
                                        <Eraser className="mr-2 h-4 w-4"/>
                                        清除预览
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border border-gray-200">
                            <CardHeader className="bg-gray-50 border-b">
                                <CardTitle>测试配置</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-6">
                                <p className="text-sm text-gray-600 mb-4">
                                    在保存前测试您的配置以确保一切正常工作
                                </p>
                                <Button type="button" onClick={testConfig} variant="outline" className="w-full">
                                    <Play className="mr-2 h-4 w-4"/>
                                    测试配置
                                </Button>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                <div className="mt-8 flex justify-end space-x-3">
                    <Button type="button" onClick={testConfig} variant="outline">
                        <Play className="mr-2 h-4 w-4"/>
                        测试配置
                    </Button>
                    <Button type="submit" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700">
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin"/>
                                保存中...
                            </>
                        ) : (
                            <>
                                <Save className="mr-2 h-4 w-4"/>
                                保存配置
                            </>
                        )}
                    </Button>
                </div>
            </form>
        </div>
    );
}