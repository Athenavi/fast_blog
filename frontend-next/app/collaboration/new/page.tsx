'use client';

import React, {useState} from 'react';
import {useRouter} from 'next/navigation';
import {AuthProtected} from '@/components/AuthProtected';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {ArrowLeft, FileText, Plus, Users} from 'lucide-react';
import {apiClient} from '@/lib/api/base-client';

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
    const [formData, setFormData] = useState({
        documentId: '',
        permission: 'edit',
        maxUsers: 5,
        expiresIn: 7 // days
    });

    const handleCreateRoom = async () => {
        if (!formData.documentId) {
            alert('请输入文档ID');
            return;
        }

        setLoading(true);
        try {
            // 创建协作邀请
            const response = await apiClient.post('/collaboration/invites', {
                document_id: formData.documentId,
                permission: formData.permission,
                max_users: parseInt(formData.maxUsers.toString()),
                expires_in_days: parseInt(formData.expiresIn.toString())
            });

            if (response.success && response.data) {
                const inviteId = response.data.invite_id;
                // 跳转到协作房间
                router.push(`/collaboration/room?invite=${inviteId}`);
            } else {
                alert(response.error || '创建协作房间失败');
            }
        } catch (error) {
            console.error('Create collaboration room error:', error);
            alert('创建协作房间失败，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

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
                    {/* 文档ID */}
                    <div className="space-y-2">
                        <Label htmlFor="documentId">文档ID</Label>
                        <Input
                            id="documentId"
                            placeholder="例如: article-123"
                            value={formData.documentId}
                            onChange={(e) => setFormData({...formData, documentId: e.target.value})}
                        />
                        <p className="text-sm text-gray-500">
                            要协作文档的唯一标识符
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
                            disabled={loading}
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
