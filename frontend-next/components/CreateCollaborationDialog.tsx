'use client';

import React, {useState} from 'react';
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,} from '@/components/ui/dialog';
import {Button} from '@/components/ui/button';
import {Label} from '@/components/ui/label';
import {Input} from '@/components/ui/input';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {CheckCircle, Copy, Link as LinkIcon, Users} from 'lucide-react';

interface CreateCollaborationDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    documentId: string;
    articleId?: number;
    articleTitle?: string;
}

interface Invitation {
    invite_id: string;
    document_id: string;
    invite_url: string;
    permission: string;
    expires_at: string;
    max_users: number;
    current_users: number;
}

export function CreateCollaborationDialog({
                                              open,
                                              onOpenChange,
                                              documentId,
                                              articleId,
                                              articleTitle,
                                          }: CreateCollaborationDialogProps) {
    const [maxUsers, setMaxUsers] = useState(3);
    const [expireHours, setExpireHours] = useState(24);
    const [permission, setPermission] = useState('edit');
    const [loading, setLoading] = useState(false);
    const [invitation, setInvitation] = useState<Invitation | null>(null);
    const [copied, setCopied] = useState(false);

    // 创建邀请
    const handleCreateInvitation = React.useCallback(async () => {
        setLoading(true);
        try {
            // 直接使用完整 URL，避免 apiFetch 重复添加前缀
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9421';
            const url = `${baseUrl}/api/v1/collaboration/invites/create`;

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    article_id: articleId || parseInt(documentId.replace('article-', '')),
                    permission,
                    expire_hours: expireHours,
                    max_users: maxUsers,
                }),
            });

            if (!response.ok) {
                console.error('Response status:', response.status);
                console.error('Response headers:', response.headers);

                const errorText = await response.text().catch(() => '');
                console.error('Response text:', errorText);

                let errorData = {};
                try {
                    errorData = JSON.parse(errorText);
                } catch (e) {
                    console.error('Failed to parse error as JSON');
                }

                console.error('API Error Response:', errorData);

                // 处理不同类型的错误响应
                let errorMessage = `创建邀请失败 (HTTP ${response.status})`;
                if (errorData.detail) {
                    if (typeof errorData.detail === 'string') {
                        errorMessage = errorData.detail;
                    } else if (Array.isArray(errorData.detail)) {
                        // Pydantic 验证错误
                        errorMessage = errorData.detail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
                    } else {
                        errorMessage = JSON.stringify(errorData.detail);
                    }
                } else if (errorText) {
                    errorMessage = errorText.substring(0, 200);
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            setInvitation(data);
        } catch (error) {
            console.error('Create invitation error:', error);
            alert(`创建邀请失败: ${error instanceof Error ? error.message : '未知错误'}`);
        } finally {
            setLoading(false);
        }
    }, [articleId, documentId, permission, expireHours, maxUsers]);

    // 复制链接
    const handleCopyLink = async () => {
        if (!invitation) return;

        try {
            await navigator.clipboard.writeText(invitation.invite_url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error('Copy failed:', error);
        }
    };

    // 重置状态
    const handleReset = () => {
        setInvitation(null);
        setCopied(false);
    };

    // 格式化过期时间
    const formatExpiry = (expiresAt: string) => {
        const date = new Date(expiresAt);
        const now = new Date();
        const diffHours = Math.round((date.getTime() - now.getTime()) / (1000 * 60 * 60));

        if (diffHours < 0) return '已过期';
        if (diffHours < 24) return `${diffHours}小时后过期`;
        return `${Math.round(diffHours / 24)}天后过期`;
    };

    return (
        <Dialog open={open} onOpenChange={(newOpen) => {
            onOpenChange(newOpen);
            if (!newOpen) handleReset();
        }}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Users className="w-5 h-5"/>
                        创建协作文档
                    </DialogTitle>
                    <DialogDescription>
                        {articleTitle ? `为文章"${articleTitle}"创建协作会话` : '创建一个新的协作文档'}
                    </DialogDescription>
                </DialogHeader>

                {!invitation ? (
                    // 创建邀请表单
                    <div className="space-y-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="maxUsers">最大协作人数</Label>
                                <Select
                                    value={maxUsers.toString()}
                                    onValueChange={(v) => setMaxUsers(parseInt(v))}
                                >
                                    <SelectTrigger>
                                        <SelectValue/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="2">2人</SelectItem>
                                        <SelectItem value="3">3人</SelectItem>
                                        <SelectItem value="5">5人</SelectItem>
                                        <SelectItem value="10">10人</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="expireHours">链接有效期</Label>
                                <Select
                                    value={expireHours.toString()}
                                    onValueChange={(v) => setExpireHours(parseInt(v))}
                                >
                                    <SelectTrigger>
                                        <SelectValue/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="1">1小时</SelectItem>
                                        <SelectItem value="24">24小时</SelectItem>
                                        <SelectItem value="72">3天</SelectItem>
                                        <SelectItem value="168">7天</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="permission">协作权限</Label>
                            <Select value={permission} onValueChange={setPermission}>
                                <SelectTrigger>
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="edit">可编辑</SelectItem>
                                    <SelectItem value="view">仅查看</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <Button
                            onClick={handleCreateInvitation}
                            disabled={loading}
                            className="w-full"
                        >
                            {loading ? '创建中...' : '生成邀请链接'}
                        </Button>
                    </div>
                ) : (
                    // 显示邀请链接
                    <div className="space-y-4 py-4">
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                            <div className="flex items-start gap-3">
                                <CheckCircle className="w-5 h-5 text-green-600 mt-0.5"/>
                                <div className="flex-1">
                                    <h4 className="font-semibold text-green-800 mb-1">邀请链接已生成</h4>
                                    <p className="text-sm text-green-700 mb-3">
                                        将此链接分享给协作者，最多 {invitation.max_users} 人可同时参与
                                    </p>

                                    <div className="flex items-center gap-2">
                                        <Input
                                            value={invitation.invite_url}
                                            readOnly
                                            className="flex-1 text-sm"
                                        />
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={handleCopyLink}
                                        >
                                            {copied ? (
                                                <CheckCircle className="w-4 h-4 text-green-500"/>
                                            ) : (
                                                <Copy className="w-4 h-4"/>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-sm">
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <span className="text-gray-500">权限：</span>
                                <span className="font-medium">
                                    {invitation.permission === 'edit' ? '可编辑' : '仅查看'}
                                </span>
                            </div>
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <span className="text-gray-500">有效期：</span>
                                <span className="font-medium">{formatExpiry(invitation.expires_at)}</span>
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                onClick={handleReset}
                                className="flex-1"
                            >
                                重新创建
                            </Button>
                            <Button
                                onClick={() => {
                                    window.open(invitation.invite_url, '_blank');
                                }}
                                className="flex-1"
                            >
                                <LinkIcon className="w-4 h-4 mr-2"/>
                                在新窗口打开
                            </Button>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
