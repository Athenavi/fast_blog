'use client';

import React, {useState, useEffect} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Badge} from '@/components/ui/badge';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Copy, Users, Link as LinkIcon, Trash2, CheckCircle} from 'lucide-react';
import {apiFetch} from '@/lib/api';

interface Invitation {
    invite_id: string;
    document_id: string;
    permission: string;
    expires_at: string;
    max_users: number;
    current_users: number;
    invite_url: string;
}

interface InvitationManagerProps {
    documentId: string;
}

export function InvitationManager({documentId}: InvitationManagerProps) {
    const [invitations, setInvitations] = useState<Invitation[]>([]);
    const [maxUsers, setMaxUsers] = useState(3);
    const [expireHours, setExpireHours] = useState(24);
    const [permission, setPermission] = useState('edit');
    const [loading, setLoading] = useState(false);
    const [copiedId, setCopiedId] = useState<string | null>(null);

    // 加载现有邀请
    useEffect(() => {
        loadInvitations();
    }, [documentId]);

    const loadInvitations = async () => {
        try {
            const response = await apiFetch(`/api/v1/collaboration/invites/document/${documentId}/active`);
            const data = await response.json();
            if (data.success) {
                setInvitations(data.data.invitations);
            }
        } catch (error) {
            console.error('Failed to load invitations:', error);
        }
    };

    // 创建新邀请
    const handleCreateInvite = async () => {
        setLoading(true);
        try {
            console.log('Creating invitation with data:', {
                document_id: documentId,
                permission,
                expire_hours: expireHours,
                max_users: maxUsers,
            });

            const response = await apiFetch('/api/v1/collaboration/invites/create', {
                method: 'POST',
                body: JSON.stringify({
                    document_id: documentId,
                    permission,
                    expire_hours: expireHours,
                    max_users: maxUsers,
                }),
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Error response:', errorData);
                throw new Error(errorData.detail || 'Failed to create invitation');
            }

            const data = await response.json();
            console.log('Invitation created successfully:', data);
            await loadInvitations();
        } catch (error) {
            console.error('Create invitation error:', error);
            alert(`创建邀请失败: ${error instanceof Error ? error.message : '未知错误'}`);
        } finally {
            setLoading(false);
        }
    };

    // 复制邀请链接
    const handleCopyLink = async (invite: Invitation) => {
        try {
            await navigator.clipboard.writeText(invite.invite_url);
            setCopiedId(invite.invite_id);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (error) {
            console.error('Copy failed:', error);
        }
    };

    // 撤销邀请
    const handleRevoke = async (inviteId: string) => {
        if (!confirm('确定要撤销此邀请吗?')) return;

        try {
            const response = await apiFetch(`/api/v1/collaboration/invites/${inviteId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Failed to revoke invitation');
            }

            await loadInvitations();
        } catch (error) {
            console.error('Revoke error:', error);
            alert('撤销邀请失败');
        }
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
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5"/>
                    邀请协作
                </CardTitle>
                <CardDescription>
                    创建邀请链接,最多支持{maxUsers}人同时编辑
                </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
                {/* 创建邀请表单 */}
                <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
                    <h3 className="font-semibold">创建新邀请</h3>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="maxUsers">最大人数</Label>
                            <Select value={maxUsers.toString()} onValueChange={(v) => setMaxUsers(parseInt(v))}>
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
                            <Label htmlFor="expireHours">有效期</Label>
                            <Select value={expireHours.toString()} onValueChange={(v) => setExpireHours(parseInt(v))}>
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
                        <Label htmlFor="permission">权限</Label>
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

                    <Button onClick={handleCreateInvite} disabled={loading} className="w-full">
                        {loading ? '创建中...' : '生成邀请链接'}
                    </Button>
                </div>

                {/* 邀请列表 */}
                {invitations.length > 0 && (
                    <div className="space-y-3">
                        <h3 className="font-semibold">活跃邀请 ({invitations.length})</h3>

                        {invitations.map((invite) => (
                            <div key={invite.invite_id} className="p-3 border rounded-lg space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Badge
                                            variant={invite.current_users >= invite.max_users ? 'destructive' : 'default'}>
                                            {invite.current_users}/{invite.max_users} 人
                                        </Badge>
                                        <Badge
                                            variant="secondary">{invite.permission === 'edit' ? '可编辑' : '仅查看'}</Badge>
                                    </div>
                                    <span className="text-xs text-gray-500">
                    {formatExpiry(invite.expires_at)}
                  </span>
                                </div>

                                <div className="flex items-center gap-2">
                                    <Input
                                        value={invite.invite_url}
                                        readOnly
                                        className="text-xs flex-1"
                                    />
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleCopyLink(invite)}
                                    >
                                        {copiedId === invite.invite_id ? (
                                            <CheckCircle className="w-4 h-4 text-green-500"/>
                                        ) : (
                                            <Copy className="w-4 h-4"/>
                                        )}
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => handleRevoke(invite.invite_id)}
                                    >
                                        <Trash2 className="w-4 h-4"/>
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {invitations.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                        <LinkIcon className="w-12 h-12 mx-auto mb-2 opacity-20"/>
                        <p>暂无活跃邀请</p>
                        <p className="text-sm">创建邀请链接后,分享给协作者即可开始协作</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
