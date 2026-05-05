/**
 * 待办事项提醒组件 - 显示需要处理的任务
 */
'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {ScrollArea} from '@/components/ui/scroll-area';
import {CheckCircle2, Download, ExternalLink, MessageSquare, Search} from 'lucide-react';
import apiClient from '@/lib/api-client';
import Link from 'next/link';

interface TodoItem {
    id: string;
    type: 'comment' | 'backup' | 'seo' | 'update';
    title: string;
    description: string;
    priority: 'high' | 'medium' | 'low';
    count?: number;
    actionUrl?: string;
    actionText?: string;
    icon: React.ReactNode;
}

export default function TodoReminders() {
    const [todos, setTodos] = useState<TodoItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchTodos();
    }, []);

    const fetchTodos = async () => {
        try {
            setLoading(true);
            const todoList: TodoItem[] = [];

            // 1. 检查待审核评论
            try {
                const commentsRes = await apiClient.get('/comments/admin/pending?page=1&per_page=1');
                if (commentsRes.data?.success && commentsRes.data.data?.total > 0) {
                    todoList.push({
                        id: 'pending-comments',
                        type: 'comment',
                        title: '待审核评论',
                        description: `${commentsRes.data.data.total} 条评论等待审核`,
                        priority: 'high',
                        count: commentsRes.data.data.total,
                        actionUrl: '/admin/comments',
                        actionText: '去审核',
                        icon: <MessageSquare className="h-4 w-4 text-yellow-500"/>
                    });
                }
            } catch (error) {
                console.error('Failed to check pending comments:', error);
            }

            // 2. 检查备份状态
            try {
                const backupRes = await apiClient.get('/backup/status').catch(() => ({data: {success: false}}));
                if (backupRes.data?.success) {
                    const lastBackup = backupRes.data.data.last_backup;
                    if (lastBackup) {
                        const daysSinceBackup = Math.floor(
                            (Date.now() - new Date(lastBackup).getTime()) / (1000 * 60 * 60 * 24)
                        );

                        if (daysSinceBackup > 7) {
                            todoList.push({
                                id: 'backup-needed',
                                type: 'backup',
                                title: '需要备份',
                                description: `距离上次备份已 ${daysSinceBackup} 天`,
                                priority: 'high',
                                actionUrl: '/admin/backup',
                                actionText: '立即备份',
                                icon: <Download className="h-4 w-4 text-red-500"/>
                            });
                        } else if (daysSinceBackup > 3) {
                            todoList.push({
                                id: 'backup-soon',
                                type: 'backup',
                                title: '建议备份',
                                description: `距离上次备份已 ${daysSinceBackup} 天`,
                                priority: 'medium',
                                actionUrl: '/admin/backup',
                                actionText: '去备份',
                                icon: <Download className="h-4 w-4 text-yellow-500"/>
                            });
                        }
                    } else {
                        todoList.push({
                            id: 'no-backup',
                            type: 'backup',
                            title: '从未备份',
                            description: '建议立即进行首次备份',
                            priority: 'high',
                            actionUrl: '/admin/backup',
                            actionText: '开始备份',
                            icon: <Download className="h-4 w-4 text-red-500"/>
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to check backup status:', error);
            }

            // 3. SEO优化建议
            try {
                const seoRes = await apiClient.get('/seo/audit/summary').catch(() => ({data: {success: false}}));
                if (seoRes.data?.success && seoRes.data.data) {
                    const issues = seoRes.data.data.issues || [];
                    if (issues.length > 0) {
                        todoList.push({
                            id: 'seo-issues',
                            type: 'seo',
                            title: 'SEO优化建议',
                            description: `${issues.length} 个SEO问题需要修复`,
                            priority: 'medium',
                            count: issues.length,
                            actionUrl: '/admin/seo',
                            actionText: '查看详情',
                            icon: <Search className="h-4 w-4 text-blue-500"/>
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to check SEO issues:', error);
            }

            // 4. 系统更新检查
            try {
                const updateRes = await apiClient.get('/system/updates').catch(() => ({data: {success: false}}));
                if (updateRes.data?.success && updateRes.data.data?.available_updates > 0) {
                    todoList.push({
                        id: 'system-updates',
                        type: 'update',
                        title: '系统更新可用',
                        description: `${updateRes.data.data.available_updates} 个更新可用`,
                        priority: 'medium',
                        count: updateRes.data.data.available_updates,
                        actionUrl: '/admin/updates',
                        actionText: '查看更新',
                        icon: <ExternalLink className="h-4 w-4 text-purple-500"/>
                    });
                }
            } catch (error) {
                console.error('Failed to check updates:', error);
            }

            // 按优先级排序
            const priorityOrder = {high: 0, medium: 1, low: 2};
            todoList.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

            setTodos(todoList);
        } catch (error) {
            console.error('Failed to fetch todos:', error);
        } finally {
            setLoading(false);
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'high':
                return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 border-red-300';
            case 'medium':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 border-yellow-300';
            case 'low':
                return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border-blue-300';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityLabel = (priority: string) => {
        switch (priority) {
            case 'high':
                return '高优先级';
            case 'medium':
                return '中优先级';
            case 'low':
                return '低优先级';
            default:
                return priority;
        }
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>待办事项</CardTitle>
                    <CardDescription>加载任务...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (todos.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>待办事项</CardTitle>
                    <CardDescription>需要处理的任务</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="text-center py-8">
                        <CheckCircle2 className="h-12 w-12 mx-auto mb-2 text-green-500 opacity-50"/>
                        <p className="text-muted-foreground">太棒了！所有任务都已完成</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>待办事项</CardTitle>
                <CardDescription>需要处理的任务 ({todos.length})</CardDescription>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[400px] pr-4">
                    <div className="space-y-3">
                        {todos.map((todo) => (
                            <div
                                key={todo.id}
                                className="p-4 rounded-lg border bg-card hover:shadow-md transition-shadow"
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start space-x-3 flex-1">
                                        <div className="flex-shrink-0 mt-1">
                                            {todo.icon}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h4 className="text-sm font-medium">{todo.title}</h4>
                                                <Badge
                                                    variant="outline"
                                                    className={`text-xs ${getPriorityColor(todo.priority)}`}
                                                >
                                                    {getPriorityLabel(todo.priority)}
                                                </Badge>
                                                {todo.count !== undefined && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        {todo.count}
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                {todo.description}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {todo.actionUrl && (
                                    <div className="mt-3 pt-3 border-t">
                                        <Link href={todo.actionUrl}>
                                            <Button size="sm" variant="outline" className="w-full">
                                                {todo.actionText || '查看详情'}
                                                <ExternalLink className="ml-2 h-3 w-3"/>
                                            </Button>
                                        </Link>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
