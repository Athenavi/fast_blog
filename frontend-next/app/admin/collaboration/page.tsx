'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Clock, ExternalLink, FileText, RefreshCw, Trash2, Users} from 'lucide-react';
import apiClient from '@/lib/api-client';
import {toast} from '@/hooks/use-toast';

interface CollaborationSession {
    document_id: string;
    article_id?: number;
    active_users: number;
    version: number;
    last_modified: string;
}

export default function CollaborationManager() {
    const [sessions, setSessions] = useState<CollaborationSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [closing, setClosing] = useState<string | null>(null);

    // 获取活跃会话
    const fetchSessions = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/collaboration/active-sessions');

            if (response.data?.success) {
                setSessions(response.data.data.sessions || []);
            } else {
                toast({
                    title: '加载失败',
                    description: response.data?.error || '无法获取协作会话',
                    variant: 'destructive'
                });
            }
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
            toast({
                title: '网络错误',
                description: '无法连接到服务器',
                variant: 'destructive'
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();

        // 每30秒刷新一次
        const interval = setInterval(fetchSessions, 30000);
        return () => clearInterval(interval);
    }, []);

    // 关闭会话
    const handleCloseSession = async (documentId: string) => {
        if (!confirm('确定要关闭这个协作会话吗？所有连接的用户将被断开。')) {
            return;
        }

        try {
            setClosing(documentId);
            const response = await apiClient.delete(`/collaboration/documents/${documentId}`);

            if (response.data?.success) {
                toast({
                    title: '会话已关闭',
                    description: '协作文档已成功关闭'
                });
                fetchSessions(); // 刷新列表
            } else {
                toast({
                    title: '关闭失败',
                    description: response.data?.error || '无法关闭会话',
                    variant: 'destructive'
                });
            }
        } catch (error) {
            console.error('Failed to close session:', error);
            toast({
                title: '操作失败',
                description: '网络错误或服务器异常',
                variant: 'destructive'
            });
        } finally {
            setClosing(null);
        }
    };

    // 格式化时间
    const formatTimeAgo = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / (1000 * 60));

        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}小时前`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}天前`;
    };

    // 打开文档
    const handleOpenDocument = (documentId: string) => {
        window.open(`/my/posts/edit?collab=${documentId}`, '_blank');
    };

    if (loading && sessions.length === 0) {
        return (
            <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400"/>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold">协作会话管理</h2>
                    <p className="text-sm text-gray-500 mt-1">
                        查看和管理当前活跃的实时协作文档
                    </p>
                </div>
                <Button onClick={fetchSessions} variant="outline" size="sm">
                    <RefreshCw className="w-4 h-4 mr-2"/>
                    刷新
                </Button>
            </div>

            {sessions.length === 0 ? (
                <Card>
                    <CardContent className="py-12">
                        <div className="text-center text-gray-500">
                            <Users className="w-12 h-12 mx-auto mb-4 opacity-50"/>
                            <p className="text-lg font-medium mb-2">暂无活跃会话</p>
                            <p className="text-sm">当前没有正在进行的协作文档</p>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {sessions.map((session) => (
                        <Card key={session.document_id} className="hover:shadow-md transition-shadow">
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <FileText className="w-4 h-4"/>
                                            文档 {session.document_id.slice(0, 8)}...
                                        </CardTitle>
                                        <CardDescription className="mt-1">
                                            版本 {session.version}
                                        </CardDescription>
                                    </div>
                                    <Badge variant={session.active_users > 1 ? 'default' : 'secondary'}>
                                        <Users className="w-3 h-3 mr-1"/>
                                        {session.active_users} 人在线
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="flex items-center text-sm text-gray-500">
                                    <Clock className="w-4 h-4 mr-2"/>
                                    最后活动: {formatTimeAgo(session.last_modified)}
                                </div>

                                {session.article_id && (
                                    <div className="text-xs text-gray-400">
                                        关联文章 ID: {session.article_id}
                                    </div>
                                )}

                                <div className="flex gap-2 pt-2">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleOpenDocument(session.document_id)}
                                        className="flex-1"
                                    >
                                        <ExternalLink className="w-4 h-4 mr-2"/>
                                        打开
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => handleCloseSession(session.document_id)}
                                        disabled={closing === session.document_id}
                                    >
                                        <Trash2 className="w-4 h-4"/>
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            <div className="text-sm text-gray-500 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="font-medium text-blue-900 mb-2">💡 提示</p>
                <ul className="list-disc list-inside space-y-1 text-blue-800">
                    <li>协作会话会自动保存，无需手动保存</li>
                    <li>关闭会话会断开所有用户的连接</li>
                    <li>会话列表每30秒自动刷新</li>
                    <li>建议定期清理不需要的会话以释放资源</li>
                </ul>
            </div>
        </div>
    );
}
