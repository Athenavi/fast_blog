/**
 * 翻译管理后台 - 管理多语言翻译
 */

'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Badge} from '@/components/ui/badge';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {AlertCircle, BarChart3, Edit, FileJson, Languages, Plus, Search, Trash2, Upload} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Language {
    code: string;
    name: string;
    native_name: string;
    locale: string;
    direction: 'ltr' | 'rtl';
    flag: string;
}

interface TranslationStats {
    total_translations: number;
    is_default: boolean;
    is_rtl: boolean;
}

const TranslationManagement = () => {
    const [activeTab, setActiveTab] = useState('translations');
    const [languages, setLanguages] = useState<Language[]>([]);
    const [selectedLanguage, setSelectedLanguage] = useState<string>('zh-CN');
    const [translations, setTranslations] = useState<Record<string, string>>({});
    const [stats, setStats] = useState<Record<string, TranslationStats>>({});
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);

    // 编辑对话框状态
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [editingKey, setEditingKey] = useState('');
    const [editingValue, setEditingValue] = useState('');
    const [newTranslationDialog, setNewTranslationDialog] = useState(false);
    const [newKey, setNewKey] = useState('');
    const [newValue, setNewValue] = useState('');

    useEffect(() => {
        loadLanguages();
        loadStats();
    }, []);

    useEffect(() => {
        if (selectedLanguage) {
            loadTranslations(selectedLanguage);
        }
    }, [selectedLanguage]);

    // 加载支持的语言
    const loadLanguages = async () => {
        try {
            const response = await apiClient.get('/api/v1/i18n/languages');
            if (response.success && (response.data as any)?.languages) {
                const langs = Object.entries((response.data as any).languages).map(([code, info]: [string, any]) => ({
                    code,
                    ...info
                }));
                setLanguages(langs);
            }
        } catch (error) {
            console.error('Failed to load languages:', error);
        }
    };

    // 加载统计信息
    const loadStats = async () => {
        try {
            const response = await apiClient.get('/api/v1/i18n/stats');
            if (response.success && (response.data as any)?.stats) {
                setStats((response.data as any).stats);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    };

    // 加载翻译
    const loadTranslations = async (lang: string) => {
        setLoading(true);
        try {
            const response = await apiClient.get(`/api/v1/i18n/translations/${lang}`);
            if (response.success && (response.data as any)?.translations) {
                setTranslations((response.data as any).translations);
            }
        } catch (error) {
            console.error('Failed to load translations:', error);
        } finally {
            setLoading(false);
        }
    };

    // 添加翻译
    const handleAddTranslation = async () => {
        if (!newKey || !newValue) {
            alert('请填写键和值');
            return;
        }

        try {
            const response = await apiClient.post('/api/v1/i18n/translations/add', {
                language: selectedLanguage,
                key: newKey,
                value: newValue
            });

            if (response.success) {
                setNewTranslationDialog(false);
                setNewKey('');
                setNewValue('');
                loadTranslations(selectedLanguage);
                loadStats();
                alert('翻译添加成功');
            } else {
                alert(response.error || '添加失败');
            }
        } catch (error) {
            console.error('Failed to add translation:', error);
            alert('添加失败');
        }
    };

    // 更新翻译
    const handleUpdateTranslation = async () => {
        if (!editingKey || !editingValue) {
            alert('请填写翻译内容');
            return;
        }

        try {
            const response = await apiClient.put('/api/v1/i18n/translations/update', {
                language: selectedLanguage,
                key: editingKey,
                value: editingValue
            });

            if (response.success) {
                setEditDialogOpen(false);
                loadTranslations(selectedLanguage);
                alert('翻译更新成功');
            } else {
                alert(response.error || '更新失败');
            }
        } catch (error) {
            console.error('Failed to update translation:', error);
            alert('更新失败');
        }
    };

    // 删除翻译
    const handleDeleteTranslation = async (key: string) => {
        if (!confirm(`确定要删除翻译键 "${key}" 吗？`)) {
            return;
        }

        try {
            const response = await apiClient.request('/api/v1/i18n/translations/delete', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    language: selectedLanguage,
                    key: key
                })
            });

            if (response.success) {
                loadTranslations(selectedLanguage);
                loadStats();
                alert('翻译删除成功');
            } else {
                alert(response.error || '删除失败');
            }
        } catch (error) {
            console.error('Failed to delete translation:', error);
            alert('删除失败');
        }
    };

    // 导出翻译
    const handleExport = async (format: 'json' | 'yaml') => {
        try {
            const response = await apiClient.get(`/api/v1/i18n/export?language=${selectedLanguage}&format=${format}`);

            if (response.success && (response.data as any)?.content) {
                const blob = new Blob([(response.data as any).content], {
                    type: format === 'json' ? 'application/json' : 'text/yaml'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `translations-${selectedLanguage}.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Failed to export translations:', error);
            alert('导出失败');
        }
    };

    // 导入翻译
    const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            const content = e.target?.result as string;

            try {
                const response = await apiClient.post('/api/v1/i18n/import', {
                    language: selectedLanguage,
                    content: content,
                    format: file.name.endsWith('.json') ? 'json' : 'yaml'
                });

                if (response.success) {
                    loadTranslations(selectedLanguage);
                    loadStats();
                    alert('翻译导入成功');
                } else {
                    alert(response.error || '导入失败');
                }
            } catch (error) {
                console.error('Failed to import translations:', error);
                alert('导入失败');
            }
        };
        reader.readAsText(file);
    };

    // 过滤翻译
    const filteredTranslations = Object.entries(translations).filter(([key, value]) => {
        return key.toLowerCase().includes(searchQuery.toLowerCase()) ||
            value.toLowerCase().includes(searchQuery.toLowerCase());
    });

    // 获取当前语言信息
    const getCurrentLanguage = () => {
        return languages.find(l => l.code === selectedLanguage);
    };

    const currentLang = getCurrentLanguage();

    return (
        <div className="space-y-6">
            {/* 页面标题 */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">翻译管理</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                    管理系统多语言翻译，支持导入导出
                </p>
            </div>

            {/* 标签页 */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="translations" className="flex items-center gap-2">
                        <Languages className="w-4 h-4"/>
                        翻译列表
                    </TabsTrigger>
                    <TabsTrigger value="stats" className="flex items-center gap-2">
                        <BarChart3 className="w-4 h-4"/>
                        统计分析
                    </TabsTrigger>
                </TabsList>

                {/* 翻译列表 */}
                <TabsContent value="translations" className="space-y-4">
                    {/* 语言和工具栏 */}
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex flex-col md:flex-row gap-4">
                                {/* 语言选择 */}
                                <div className="flex-1">
                                    <Label>选择语言</Label>
                                    <div className="flex gap-2 mt-2 flex-wrap">
                                        {languages.map((lang) => (
                                            <Button
                                                key={lang.code}
                                                variant={selectedLanguage === lang.code ? "default" : "outline"}
                                                size="sm"
                                                onClick={() => setSelectedLanguage(lang.code)}
                                                className="gap-2"
                                            >
                                                <span>{lang.flag}</span>
                                                <span>{lang.native_name}</span>
                                                {stats[lang.code] && (
                                                    <Badge variant="secondary" className="ml-1">
                                                        {stats[lang.code].total_translations}
                                                    </Badge>
                                                )}
                                            </Button>
                                        ))}
                                    </div>
                                </div>

                                {/* 操作按钮 */}
                                <div className="flex gap-2 items-end">
                                    <Button onClick={() => setNewTranslationDialog(true)}>
                                        <Plus className="w-4 h-4 mr-2"/>
                                        添加翻译
                                    </Button>
                                    <Button variant="outline" onClick={() => handleExport('json')}>
                                        <FileJson className="w-4 h-4 mr-2"/>
                                        导出JSON
                                    </Button>
                                    <div className="relative">
                                        <Input
                                            type="file"
                                            accept=".json,.yaml,.yml"
                                            onChange={handleImport}
                                            className="absolute inset-0 opacity-0 cursor-pointer"
                                        />
                                        <Button variant="outline">
                                            <Upload className="w-4 h-4 mr-2"/>
                                            导入
                                        </Button>
                                    </div>
                                </div>
                            </div>

                            {/* 搜索框 */}
                            <div className="mt-4">
                                <div className="relative">
                                    <Search
                                        className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                                    <Input
                                        placeholder="搜索翻译键或内容..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10"
                                    />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* 当前语言信息 */}
                    {currentLang && (
                        <Card>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-4">
                                    <span className="text-4xl">{currentLang.flag}</span>
                                    <div className="flex-1">
                                        <h3 className="font-medium text-lg">
                                            {currentLang.native_name} ({currentLang.name})
                                        </h3>
                                        <p className="text-sm text-gray-500">
                                            代码: {currentLang.code} | Locale: {currentLang.locale} |
                                            方向: {currentLang.direction === 'rtl' ? '从右到左' : '从左到右'}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-2xl font-bold">
                                            {stats[selectedLanguage]?.total_translations || 0}
                                        </div>
                                        <div className="text-xs text-gray-500">翻译条目</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* 翻译列表 */}
                    <Card>
                        <CardHeader>
                            <CardTitle>翻译列表</CardTitle>
                            <CardDescription>
                                共 {filteredTranslations.length} 条翻译
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <div className="text-center py-8">加载中...</div>
                            ) : filteredTranslations.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    <AlertCircle className="w-12 h-12 mx-auto mb-2 text-gray-300"/>
                                    <p>没有找到翻译</p>
                                </div>
                            ) : (
                                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                                    {filteredTranslations.map(([key, value]) => (
                                        <div
                                            key={key}
                                            className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                        >
                                            <div className="flex-1 min-w-0">
                                                <div
                                                    className="font-mono text-sm font-medium text-blue-600 dark:text-blue-400 mb-1">
                                                    {key}
                                                </div>
                                                <div className="text-sm text-gray-700 dark:text-gray-300 break-words">
                                                    {value}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 flex-shrink-0">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => {
                                                        setEditingKey(key);
                                                        setEditingValue(value);
                                                        setEditDialogOpen(true);
                                                    }}
                                                >
                                                    <Edit className="w-4 h-4"/>
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => handleDeleteTranslation(key)}
                                                    className="text-red-600"
                                                >
                                                    <Trash2 className="w-4 h-4"/>
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 统计分析 */}
                <TabsContent value="stats" className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {languages.map((lang) => {
                            const stat = stats[lang.code];
                            if (!stat) return null;

                            return (
                                <Card key={lang.code}>
                                    <CardContent className="pt-6">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-2">
                                                <span className="text-2xl">{lang.flag}</span>
                                                <div>
                                                    <div className="font-medium">{lang.native_name}</div>
                                                    <div className="text-xs text-gray-500">{lang.code}</div>
                                                </div>
                                            </div>
                                            {stat.is_default && (
                                                <Badge variant="default">默认</Badge>
                                            )}
                                        </div>

                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-gray-600">翻译数量</span>
                                                <span className="font-bold text-lg">{stat.total_translations}</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-gray-600">RTL支持</span>
                                                <span>{stat.is_rtl ? '是' : '否'}</span>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                </TabsContent>
            </Tabs>

            {/* 编辑翻译对话框 */}
            <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>编辑翻译</DialogTitle>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div>
                            <Label>翻译键</Label>
                            <Input value={editingKey} disabled className="font-mono"/>
                        </div>

                        <div>
                            <Label>翻译内容</Label>
                            <Textarea
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                rows={4}
                                placeholder="输入翻译内容"
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleUpdateTranslation}>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 添加翻译对话框 */}
            <Dialog open={newTranslationDialog} onOpenChange={setNewTranslationDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>添加新翻译</DialogTitle>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div>
                            <Label htmlFor="new-key">翻译键</Label>
                            <Input
                                id="new-key"
                                value={newKey}
                                onChange={(e) => setNewKey(e.target.value)}
                                placeholder="例如: common.submit"
                                className="font-mono"
                            />
                        </div>

                        <div>
                            <Label htmlFor="new-value">翻译内容</Label>
                            <Textarea
                                id="new-value"
                                value={newValue}
                                onChange={(e) => setNewValue(e.target.value)}
                                rows={4}
                                placeholder="输入翻译内容"
                            />
                        </div>

                        <div className="text-sm text-gray-500">
                            当前语言: {currentLang?.native_name} ({selectedLanguage})
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setNewTranslationDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={handleAddTranslation}>
                            添加
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default TranslationManagement;
