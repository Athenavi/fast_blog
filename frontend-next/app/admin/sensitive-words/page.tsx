'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {Textarea} from '@/components/ui/textarea';
import apiClient from '@/lib/api-client';
import {AlertTriangle, Edit, Plus, RefreshCw, Search, Shield, Trash2, Upload} from 'lucide-react';

interface SensitiveWord {
    id: number;
    word: string;
    level: number;
    action: string;
    replacement: string | null;
    category: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

interface PaginationInfo {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
}

interface Statistics {
    total: number;
    by_level: Record<number, number>;
    by_action: Record<string, number>;
    by_category: Record<string, number>;
    by_status: {
        active: number;
        inactive: number;
    };
}

const SensitiveWordsManagement = () => {
    const [words, setWords] = useState<SensitiveWord[]>([]);
    const [pagination, setPagination] = useState<PaginationInfo>({
        page: 1,
        per_page: 50,
        total: 0,
        total_pages: 1
    });
    const [loading, setLoading] = useState(true);
    const [statistics, setStatistics] = useState<Statistics | null>(null);

    // 筛选条件
    const [levelFilter, setLevelFilter] = useState<string>('all');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [keywordSearch, setKeywordSearch] = useState('');

    // 对话框状态
    const [showAddDialog, setShowAddDialog] = useState(false);
    const [showEditDialog, setShowEditDialog] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [showImportDialog, setShowImportDialog] = useState(false);
    const [currentWord, setCurrentWord] = useState<SensitiveWord | null>(null);

    // 表单数据
    const [formData, setFormData] = useState({
        word: '',
        level: 1,
        action: 'block',
        replacement: '',
        category: ''
    });

    const [importText, setImportText] = useState('');

    // 加载敏感词列表
    const loadWords = async () => {
        setLoading(true);
        try {
            let url = `/api/v1/sensitive-words?page=${pagination.page}&per_page=${pagination.per_page}`;

            if (levelFilter !== 'all') {
                url += `&level=${levelFilter}`;
            }
            if (categoryFilter !== 'all') {
                url += `&category=${encodeURIComponent(categoryFilter)}`;
            }
            if (statusFilter !== 'all') {
                url += `&is_active=${statusFilter === 'active'}`;
            }
            if (keywordSearch) {
                url += `&keyword=${encodeURIComponent(keywordSearch)}`;
            }

            const response = await apiClient.get(url);

            if (response.success && response.data) {
                setWords(response.data.items || []);
                setPagination({
                    page: response.data.page,
                    per_page: response.data.per_page,
                    total: response.data.total,
                    total_pages: response.data.total_pages
                });
            }
        } catch (error: any) {
            console.error('Failed to load sensitive words:', error);
        } finally {
            setLoading(false);
        }
    };

    // 加载统计信息
    const loadStatistics = async () => {
        try {
            const response = await apiClient.get('/api/v1/sensitive-words/statistics');
            if (response.success && response.data) {
                setStatistics(response.data);
            }
        } catch (error: any) {
            console.error('Failed to load statistics:', error);
        }
    };

    useEffect(() => {
        loadWords();
        loadStatistics();
    }, [pagination.page, levelFilter, categoryFilter, statusFilter, keywordSearch]);

    // 添加敏感词
    const handleAdd = async () => {
        try {
            console.log('[DEBUG] Sending data:', {
                word: formData.word,
                level: formData.level,
                action: formData.action,
                replacement: formData.replacement || null,
                category: formData.category || null
            });

            const response = await apiClient.post('/api/v1/sensitive-words', {
                word: formData.word,
                level: formData.level,
                action: formData.action,
                replacement: formData.replacement || null,
                category: formData.category || null
            });

            console.log('[DEBUG] Response:', response);

            if (response.success) {
                loadWords();
                loadStatistics();
                setShowAddDialog(false);
                resetForm();
            }
        } catch (error: any) {
            console.error('Failed to add sensitive word:', error);
            console.error('Error response:', error.response);
            alert(error.response?.data?.error || error.response?.data?.detail || '添加失败');
        }
    };

    // 更新敏感词
    const handleUpdate = async () => {
        if (!currentWord) return;

        try {
            const response = await apiClient.put(`/api/v1/sensitive-words/${currentWord.id}`, {
                level: formData.level,
                action: formData.action,
                replacement: formData.replacement || null,
                category: formData.category || null,
                is_active: currentWord.is_active
            });

            if (response.success) {
                loadWords();
                setShowEditDialog(false);
                resetForm();
            }
        } catch (error: any) {
            console.error('Failed to update sensitive word:', error);
            alert(error.response?.data?.error || '更新失败');
        }
    };

    // 删除敏感词
    const handleDelete = async () => {
        if (!currentWord) return;

        try {
            const response = await apiClient.delete(`/api/v1/sensitive-words/${currentWord.id}`);

            if (response.success) {
                loadWords();
                loadStatistics();
                setShowDeleteDialog(false);
            }
        } catch (error: any) {
            console.error('Failed to delete sensitive word:', error);
            alert(error.response?.data?.error || '删除失败');
        }
    };

    // 批量导入
    const handleBatchImport = async () => {
        try {
            const lines = importText.trim().split('\n');
            const words = lines.map(line => {
                const parts = line.split(',').map(p => p.trim());
                return {
                    word: parts[0],
                    level: parseInt(parts[1]) || 1,
                    action: parts[2] || 'block',
                    category: parts[3] || null
                };
            }).filter(w => w.word);

            const response = await apiClient.post('/api/v1/sensitive-words/batch-import', {
                words
            });

            if (response.success) {
                loadWords();
                loadStatistics();
                setShowImportDialog(false);
                setImportText('');
                alert(`成功导入 ${response.data.success_count} 个敏感词`);
            }
        } catch (error: any) {
            console.error('Failed to batch import:', error);
            alert(error.response?.data?.error || '导入失败');
        }
    };

    // 刷新缓存
    const handleRefreshCache = async () => {
        try {
            const response = await apiClient.post('/api/v1/sensitive-words/refresh-cache');
            if (response.success) {
                alert('缓存刷新成功');
            }
        } catch (error: any) {
            console.error('Failed to refresh cache:', error);
            alert('缓存刷新失败');
        }
    };

    // 重置表单
    const resetForm = () => {
        setFormData({
            word: '',
            level: 1,
            action: 'block',
            replacement: '',
            category: ''
        });
        setCurrentWord(null);
    };

    // 打开编辑对话框
    const openEditDialog = (word: SensitiveWord) => {
        setCurrentWord(word);
        setFormData({
            word: word.word,
            level: word.level,
            action: word.action,
            replacement: word.replacement || '',
            category: word.category || ''
        });
        setShowEditDialog(true);
    };

    // 获取级别标签
    const getLevelBadge = (level: number) => {
        const colors = {
            1: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
            2: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
            3: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
        };
        const labels = {1: '低', 2: '中', 3: '高'};
        return (
            <Badge className={colors[level as keyof typeof colors]}>
                {labels[level as keyof typeof labels]}
            </Badge>
        );
    };

    // 获取操作标签
    const getActionBadge = (action: string) => {
        const colors = {
            block: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
            replace: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
            warn: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
        };
        const labels = {block: '拦截', replace: '替换', warn: '警告'};
        return (
            <Badge className={colors[action as keyof typeof colors]}>
                {labels[action as keyof typeof labels]}
            </Badge>
        );
    };

    // 格式化日期
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('zh-CN');
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 flex items-center">
                    <Shield className="w-8 h-8 mr-3 text-purple-600"/>
                    敏感词管理
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                    管理和配置内容审核的敏感词库
                </p>
            </div>

            {/* 统计卡片 */}
            {statistics && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                总数
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{statistics.total}</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                已激活
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-green-600">
                                {statistics.by_status?.active || 0}
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                拦截规则
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-red-600">
                                {statistics.by_action?.block || 0}
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                分类数
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-blue-600">
                                {Object.keys(statistics.by_category || {}).length}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* 操作栏 */}
            <Card className="mb-6">
                <CardContent className="pt-6">
                    <div className="flex flex-wrap gap-4 items-end">
                        <div className="flex-1 min-w-[200px]">
                            <Label>搜索关键词</Label>
                            <div className="relative mt-1">
                                <Search
                                    className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"/>
                                <Input
                                    placeholder="搜索敏感词..."
                                    value={keywordSearch}
                                    onChange={(e) => setKeywordSearch(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                        </div>

                        <div>
                            <Label>敏感级别</Label>
                            <Select value={levelFilter} onValueChange={setLevelFilter}>
                                <SelectTrigger className="w-[150px] mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">全部</SelectItem>
                                    <SelectItem value="1">低</SelectItem>
                                    <SelectItem value="2">中</SelectItem>
                                    <SelectItem value="3">高</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>处理方式</Label>
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger className="w-[150px] mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">全部</SelectItem>
                                    <SelectItem value="active">已激活</SelectItem>
                                    <SelectItem value="inactive">已停用</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex gap-2 ml-auto">
                            <Button onClick={() => setShowAddDialog(true)}>
                                <Plus className="w-4 h-4 mr-2"/>
                                添加
                            </Button>
                            <Button variant="outline" onClick={() => setShowImportDialog(true)}>
                                <Upload className="w-4 h-4 mr-2"/>
                                批量导入
                            </Button>
                            <Button variant="outline" onClick={handleRefreshCache}>
                                <RefreshCw className="w-4 h-4 mr-2"/>
                                刷新缓存
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 敏感词列表 */}
            <Card>
                <CardHeader>
                    <CardTitle>敏感词列表</CardTitle>
                    <CardDescription>
                        共 {pagination.total} 个敏感词
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8">加载中...</div>
                    ) : words.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            暂无敏感词
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                <tr className="border-b">
                                    <th className="text-left py-3 px-4 font-medium">敏感词</th>
                                    <th className="text-left py-3 px-4 font-medium">级别</th>
                                    <th className="text-left py-3 px-4 font-medium">处理方式</th>
                                    <th className="text-left py-3 px-4 font-medium">替换词</th>
                                    <th className="text-left py-3 px-4 font-medium">分类</th>
                                    <th className="text-left py-3 px-4 font-medium">状态</th>
                                    <th className="text-left py-3 px-4 font-medium">创建时间</th>
                                    <th className="text-left py-3 px-4 font-medium">操作</th>
                                </tr>
                                </thead>
                                <tbody>
                                {words.map((word) => (
                                    <tr key={word.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                                        <td className="py-3 px-4 font-mono">{word.word}</td>
                                        <td className="py-3 px-4">{getLevelBadge(word.level)}</td>
                                        <td className="py-3 px-4">{getActionBadge(word.action)}</td>
                                        <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                                            {word.replacement || '-'}
                                        </td>
                                        <td className="py-3 px-4">
                                            {word.category ? (
                                                <Badge variant="secondary">{word.category}</Badge>
                                            ) : '-'}
                                        </td>
                                        <td className="py-3 px-4">
                                            <Badge
                                                className={word.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                                                {word.is_active ? '激活' : '停用'}
                                            </Badge>
                                        </td>
                                        <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
                                            {formatDate(word.created_at)}
                                        </td>
                                        <td className="py-3 px-4">
                                            <div className="flex gap-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => openEditDialog(word)}
                                                >
                                                    <Edit className="w-4 h-4"/>
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    onClick={() => {
                                                        setCurrentWord(word);
                                                        setShowDeleteDialog(true);
                                                    }}
                                                >
                                                    <Trash2 className="w-4 h-4"/>
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* 分页 */}
                    {pagination.total_pages > 1 && (
                        <div className="flex justify-between items-center mt-6 pt-4 border-t">
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                第 {pagination.page} / {pagination.total_pages} 页，共 {pagination.total} 条
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={pagination.page === 1}
                                    onClick={() => setPagination({...pagination, page: pagination.page - 1})}
                                >
                                    上一页
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={pagination.page === pagination.total_pages}
                                    onClick={() => setPagination({...pagination, page: pagination.page + 1})}
                                >
                                    下一页
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 添加对话框 */}
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>添加敏感词</DialogTitle>
                        <DialogDescription>
                            添加新的敏感词到过滤库
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div>
                            <Label>敏感词内容 *</Label>
                            <Input
                                value={formData.word}
                                onChange={(e) => setFormData({...formData, word: e.target.value})}
                                placeholder="输入敏感词"
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <Label>敏感级别 *</Label>
                            <Select
                                value={String(formData.level)}
                                onValueChange={(v) => setFormData({...formData, level: parseInt(v)})}
                            >
                                <SelectTrigger className="mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="1">低 - 警告</SelectItem>
                                    <SelectItem value="2">中 - 替换</SelectItem>
                                    <SelectItem value="3">高 - 拦截</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>处理方式 *</Label>
                            <Select
                                value={formData.action}
                                onValueChange={(v) => setFormData({...formData, action: v})}
                            >
                                <SelectTrigger className="mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="block">拦截 - 直接拒绝</SelectItem>
                                    <SelectItem value="replace">替换 - 自动替换</SelectItem>
                                    <SelectItem value="warn">警告 - 标记待审</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {formData.action === 'replace' && (
                            <div>
                                <Label>替换词</Label>
                                <Input
                                    value={formData.replacement}
                                    onChange={(e) => setFormData({...formData, replacement: e.target.value})}
                                    placeholder="当检测到时的替换词"
                                    className="mt-1"
                                />
                            </div>
                        )}
                        <div>
                            <Label>分类</Label>
                            <Input
                                value={formData.category}
                                onChange={(e) => setFormData({...formData, category: e.target.value})}
                                placeholder="如：政治、色情、暴力等"
                                className="mt-1"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={handleAdd}>
                            添加
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 编辑对话框 */}
            <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>编辑敏感词</DialogTitle>
                        <DialogDescription>
                            修改敏感词配置
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div>
                            <Label>敏感词内容</Label>
                            <Input value={formData.word} disabled className="mt-1 bg-gray-100"/>
                        </div>
                        <div>
                            <Label>敏感级别</Label>
                            <Select
                                value={String(formData.level)}
                                onValueChange={(v) => setFormData({...formData, level: parseInt(v)})}
                            >
                                <SelectTrigger className="mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="1">低 - 警告</SelectItem>
                                    <SelectItem value="2">中 - 替换</SelectItem>
                                    <SelectItem value="3">高 - 拦截</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>处理方式</Label>
                            <Select
                                value={formData.action}
                                onValueChange={(v) => setFormData({...formData, action: v})}
                            >
                                <SelectTrigger className="mt-1">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="block">拦截 - 直接拒绝</SelectItem>
                                    <SelectItem value="replace">替换 - 自动替换</SelectItem>
                                    <SelectItem value="warn">警告 - 标记待审</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {formData.action === 'replace' && (
                            <div>
                                <Label>替换词</Label>
                                <Input
                                    value={formData.replacement}
                                    onChange={(e) => setFormData({...formData, replacement: e.target.value})}
                                    placeholder="当检测到时的替换词"
                                    className="mt-1"
                                />
                            </div>
                        )}
                        <div>
                            <Label>分类</Label>
                            <Input
                                value={formData.category}
                                onChange={(e) => setFormData({...formData, category: e.target.value})}
                                placeholder="如：政治、色情、暴力等"
                                className="mt-1"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowEditDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={handleUpdate}>
                            保存
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 删除确认对话框 */}
            <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center">
                            <AlertTriangle className="w-5 h-5 mr-2 text-red-600"/>
                            确认删除
                        </DialogTitle>
                        <DialogDescription>
                            确定要删除敏感词 "{currentWord?.word}" 吗？此操作不可恢复。
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                            取消
                        </Button>
                        <Button variant="destructive" onClick={handleDelete}>
                            删除
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 批量导入对话框 */}
            <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>批量导入敏感词</DialogTitle>
                        <DialogDescription>
                            每行一个敏感词，格式：敏感词,级别,处理方式,分类
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div>
                            <Label>导入数据</Label>
                            <Textarea
                                value={importText}
                                onChange={(e) => setImportText(e.target.value)}
                                placeholder={`示例：\n赌博,3,block,违法\n色情,3,block,低俗\n加微信,2,replace,广告`}
                                className="mt-1 font-mono"
                                rows={10}
                            />
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                            <p><strong>格式说明：</strong></p>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                                <li>敏感词：必填</li>
                                <li>级别：1(低), 2(中), 3(高)，默认1</li>
                                <li>处理方式：block(拦截), replace(替换), warn(警告)，默认block</li>
                                <li>分类：可选，如政治、色情、暴力等</li>
                            </ul>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowImportDialog(false)}>
                            取消
                        </Button>
                        <Button onClick={handleBatchImport}>
                            导入
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default SensitiveWordsManagement;
