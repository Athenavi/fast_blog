'use client';

import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import {AuthProtected} from '@/components/AuthProtected';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {ArrowLeft, FileText, Plus, Users} from 'lucide-react';
import {apiClient} from '@/lib/api/base-client';

interface Article {
    id: number;
    title: string;
    status: string;
}

export default function NewCollaborationPage() {
    return (
        <AuthProtected>
            <NewCollaborationContent/>
        </AuthProtected>
    );
}

function NewCollaborationContent() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [articles, setArticles] = useState<Article[]>([]);
    const [loadingArticles, setLoadingArticles] = useState(true);
    const [formData, setFormData] = useState({
        articleId: '',
        permission: 'edit',
        maxUsers: 5,
        expiresIn: 7 // days
    });

    // 加载用户的文章列表
    useEffect(() => {
        const fetchArticles = async () => {
            try {
                const response = await apiClient.get('/articles');
                if (response.success && response.data) {
                    // 只显示已发布或草稿状态的文章
                    const userArticles = response.data.articles || response.data;
                    setArticles(userArticles.filter((a: Article) =>
                        a.status === 'published' || a.status === 'draft'
                    ));
                }
            } catch (error) {
                console.error('Fetch articles error:', error);
            } finally {
                setLoadingArticles(false);
            }
        };

        fetchArticles();
    }, []);

    const handleCreateRoom = React.useCallback(async () => {
        if (!formData.articleId) {
            alert('请选择一篇文章');
            return;
        }

        setLoading(true);
        try {
            console.log('Creating invitation with data:', {
                article_id: parseInt(formData.articleId),
                permission: formData.permission,
                max_users: parseInt(formData.maxUsers.toString()),
                expire_hours: parseInt(formData.expiresIn.toString()) * 24
            });
            
            // 创建协作邀请
            const response = await apiClient.post('/collaboration/invites/create', {
                article_id: parseInt(formData.articleId),
                permission: formData.permission,
                max_users: parseInt(formData.maxUsers.toString()),
                expire_hours: parseInt(formData.expiresIn.toString()) * 24
            });

            if (response.success && response.data) {
                const inviteId = response.data.invite_id;
                // 跳转到协作房间
                router.push(`/collaboration/room?invite=${inviteId}`);
            } else {
                console.error('Create invitation failed:', response);
                alert(response.error || '创建协作房间失败');
            }
        } catch (error) {
            console.error('Create collaboration room error:', error);
            if (error instanceof Error) {
                alert(`创建协作房间失败: ${error.message}`);
            } else {
                alert('创建协作房间失败，请稍后重试');
            }
        } finally {
            setLoading(false);
        }
    }, [formData, router]);

    return (
        <div className="container mx-auto py-8 px-4">
            {/* 返回按钮 */}
            <div className="mb-6">
                <Button
                    variant="ghost"
                    onClick={() => router.back()}
                >
                    <ArrowLeft className="w-4 h-4 mr-2"/>
                    返回
                </Button>
            </div>

            <Card className="max-w-2xl mx-auto">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="w-6 h-6"/>
                        创建协作房间
                    </CardTitle>
                    <CardDescription>
                        创建一个新的协作文档房间，邀请其他人一起编辑
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* 文章选择 */}
                    <div className="space-y-2">
                        <Label htmlFor="articleId">选择文章</Label>
                        {loadingArticles ? (
                            <div className="text-sm text-gray-500">加载文章中...</div>
                        ) : articles.length === 0 ? (
                            <div className="text-sm text-red-500">
                                您还没有文章，请先创建一篇文章
                            </div>
                        ) : (
                            <Select
                                value={formData.articleId}
                                onValueChange={(value) => setFormData({...formData, articleId: value})}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="选择要协作的文章"/>
                                </SelectTrigger>
                                <SelectContent>
                                    {articles.map((article) => (
                                        <SelectItem key={article.id} value={article.id.toString()}>
                                            {article.title} ({article.status === 'published' ? '已发布' : '草稿'})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                        <p className="text-sm text-gray-500">
                            只能为您拥有编辑权限的文章创建协作邀请
                        </p>
                    </div>

                    {/* 权限设置 */}
                    <div className="space-y-2">
                        <Label>协作者权限</Label>
                        <Select
                            value={formData.permission}
                            onValueChange={(value) => setFormData({...formData, permission: value})}
                        >
                            <SelectTrigger>
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="edit">可编辑</SelectItem>
                                <SelectItem value="view">仅查看</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 人数限制 */}
                    <div className="space-y-2">
                        <Label htmlFor="maxUsers">最大协作人数</Label>
                        <Input
                            id="maxUsers"
                            type="number"
                            min="2"
                            max="20"
                            value={formData.maxUsers}
                            onChange={(e) => setFormData({...formData, maxUsers: parseInt(e.target.value)})}
                        />
                        <p className="text-sm text-gray-500">
                            同时在线的最大用户数（2-20人）
                        </p>
                    </div>

                    {/* 有效期 */}
                    <div className="space-y-2">
                        <Label htmlFor="expiresIn">邀请有效期</Label>
                        <Select
                            value={formData.expiresIn.toString()}
                            onValueChange={(value) => setFormData({...formData, expiresIn: parseInt(value)})}
                        >
                            <SelectTrigger>
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="1">1天</SelectItem>
                                <SelectItem value="3">3天</SelectItem>
                                <SelectItem value="7">7天</SelectItem>
                                <SelectItem value="30">30天</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-4 pt-4">
                        <Button
                            onClick={handleCreateRoom}
                            disabled={loading || loadingArticles || articles.length === 0}
                            className="flex-1"
                        >
                            {loading ? (
                                '创建中...'
                            ) : (
                                <>
                                    <Plus className="w-4 h-4 mr-2"/>
                                    创建协作房间
                                </>
                            )}
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => router.back()}
                            disabled={loading}
                        >
                            取消
                        </Button>
                    </div>

                    {/* 提示信息 */}
                    <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg">
                        <div className="flex items-start gap-3">
                            <Users className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"/>
                            <div className="text-sm text-blue-900 dark:text-blue-200">
                                <p className="font-medium mb-1">协作说明：</p>
                                <ul className="list-disc list-inside space-y-1 text-blue-800 dark:text-blue-300">
                                    <li>创建后会生成一个邀请链接</li>
                                    <li>分享链接给协作者即可加入</li>
                                    <li>所有协作者的修改会实时同步</li>
                                    <li>您可以随时撤销邀请</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
