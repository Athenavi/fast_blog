'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Switch} from '@/components/ui/switch';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Progress} from '@/components/ui/progress';
import {useToast} from '@/hooks/use-toast';
import {CheckCircle2, Clock, Film, Play, RefreshCw, Save, Settings, Trash2} from 'lucide-react';

interface TranscodeTask {
    id: number;
    video_id: number;
    filename: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    output_resolutions: string[];
    error_message?: string;
    created_at: string;
    completed_at?: string;
}

interface TranscodeConfig {
    enabled: boolean;
    auto_transcode: boolean;
    resolutions: string[];
    format: string;
    quality: 'low' | 'medium' | 'high';
    max_file_size_mb: number;
    generate_thumbnail: boolean;
    thumbnail_time: number;
}

export default function VideoTranscodePage() {
    const {toast} = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [tasks, setTasks] = useState<TranscodeTask[]>([]);

    const [config, setConfig] = useState<TranscodeConfig>({
        enabled: true,
        auto_transcode: true,
        resolutions: ['480p', '720p', '1080p'],
        format: 'mp4',
        quality: 'medium',
        max_file_size_mb: 500,
        generate_thumbnail: true,
        thumbnail_time: 5,
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const token = getAccessToken();

            const [configRes, tasksRes] = await Promise.all([
                fetch('/api/v1/media/video-transcode/config', {
                    headers: {'Authorization': `Bearer ${token}`},
                }),
                fetch('/api/v1/media/video-transcode/tasks', {
                    headers: {'Authorization': `Bearer ${token}`},
                }),
            ]);

            if (configRes.ok) {
                const configData = await configRes.json();
                if (configData.success) {
                    setConfig(configData.data);
                }
            }

            if (tasksRes.ok) {
                const tasksData = await tasksRes.json();
                if (tasksData.success) {
                    setTasks(tasksData.data.tasks || []);
                }
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            toast({
                title: '加载失败',
                description: '无法加载视频转码数据',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();
            const response = await fetch('/api/v1/media/video-transcode/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(config),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: '视频转码配置已更新',
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const startTranscode = async (videoId: number) => {
        try {
            const token = getAccessToken();
            const response = await fetch('/api/v1/media/video-transcode/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({video_id: videoId}),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '转码任务已启动',
                    description: '视频转码正在进行中',
                });
                loadData();
            } else {
                throw new Error(data.error || '启动失败');
            }
        } catch (error) {
            console.error('Failed to start transcode:', error);
            toast({
                title: '启动失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        }
    };

    const deleteTask = async (taskId: number) => {
        if (!confirm('确定要删除这个转码任务吗？')) return;

        try {
            const token = getAccessToken();
            const response = await fetch(`/api/v1/media/video-transcode/tasks/${taskId}`, {
                method: 'DELETE',
                headers: {'Authorization': `Bearer ${token}`},
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '删除成功',
                    description: '转码任务已删除',
                });
                loadData();
            }
        } catch (error) {
            console.error('Failed to delete task:', error);
            toast({
                title: '删除失败',
                variant: 'destructive',
            });
        }
    };

    const toggleResolution = (resolution: string) => {
        if (config.resolutions.includes(resolution)) {
            setConfig({
                ...config,
                resolutions: config.resolutions.filter(r => r !== resolution),
            });
        } else {
            setConfig({
                ...config,
                resolutions: [...config.resolutions, resolution],
            });
        }
    };

    const getAccessToken = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('zh-CN');
    };

    const getStatusBadge = (status: string) => {
        const badges = {
            pending: <Badge variant="secondary"><Clock className="w-3 h-3 mr-1"/>等待中</Badge>,
            processing: <Badge className="bg-blue-600"><RefreshCw className="w-3 h-3 mr-1 animate-spin"/>处理中</Badge>,
            completed: <Badge className="bg-green-600"><CheckCircle2 className="w-3 h-3 mr-1"/>已完成</Badge>,
            failed: <Badge variant="destructive">失败</Badge>,
        };
        return badges[status as keyof typeof badges];
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载中...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">视频转码管理</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置视频转码参数、管理转码任务和查看转码历史
                </p>
            </div>

            {/* 转码配置 */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <Settings className="w-6 h-6 text-blue-600"/>
                        <div>
                            <CardTitle>转码配置</CardTitle>
                            <CardDescription>设置视频转码的默认参数</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="transcode-enabled">启用视频转码</Label>
                        <Switch
                            id="transcode-enabled"
                            checked={config.enabled}
                            onCheckedChange={(checked) =>
                                setConfig({...config, enabled: checked})
                            }
                        />
                    </div>

                    {config.enabled && (
                        <>
                            <div className="flex items-center justify-between">
                                <Label htmlFor="auto-transcode">上传后自动转码</Label>
                                <Switch
                                    id="auto-transcode"
                                    checked={config.auto_transcode}
                                    onCheckedChange={(checked) =>
                                        setConfig({...config, auto_transcode: checked})
                                    }
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>输出分辨率</Label>
                                <div className="flex flex-wrap gap-2">
                                    {['360p', '480p', '720p', '1080p', '4k'].map((res) => (
                                        <Badge
                                            key={res}
                                            variant={config.resolutions.includes(res) ? 'default' : 'outline'}
                                            className="cursor-pointer"
                                            onClick={() => toggleResolution(res)}
                                        >
                                            {res}
                                        </Badge>
                                    ))}
                                </div>
                                <p className="text-sm text-gray-500">
                                    点击切换分辨率选项
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="space-y-2">
                                    <Label>输出格式</Label>
                                    <Select
                                        value={config.format}
                                        onValueChange={(value) =>
                                            setConfig({...config, format: value})
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue/>
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="mp4">MP4</SelectItem>
                                            <SelectItem value="webm">WebM</SelectItem>
                                            <SelectItem value="avi">AVI</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label>视频质量</Label>
                                    <Select
                                        value={config.quality}
                                        onValueChange={(value: any) =>
                                            setConfig({...config, quality: value})
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue/>
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="low">低（文件小）</SelectItem>
                                            <SelectItem value="medium">中（平衡）</SelectItem>
                                            <SelectItem value="high">高（文件大）</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label>最大文件大小（MB）</Label>
                                    <Input
                                        type="number"
                                        value={config.max_file_size_mb}
                                        onChange={(e) =>
                                            setConfig({
                                                ...config,
                                                max_file_size_mb: parseInt(e.target.value) || 0,
                                            })
                                        }
                                    />
                                </div>
                            </div>

                            <div className="flex items-center justify-between">
                                <Label htmlFor="generate-thumbnail">生成缩略图</Label>
                                <Switch
                                    id="generate-thumbnail"
                                    checked={config.generate_thumbnail}
                                    onCheckedChange={(checked) =>
                                        setConfig({...config, generate_thumbnail: checked})
                                    }
                                />
                            </div>

                            {config.generate_thumbnail && (
                                <div className="space-y-2">
                                    <Label>缩略图时间点（秒）</Label>
                                    <Input
                                        type="number"
                                        min="0"
                                        value={config.thumbnail_time}
                                        onChange={(e) =>
                                            setConfig({
                                                ...config,
                                                thumbnail_time: parseInt(e.target.value) || 0,
                                            })
                                        }
                                    />
                                </div>
                            )}

                            <Button onClick={saveConfig} disabled={saving}>
                                <Save className="w-4 h-4 mr-2"/>
                                {saving ? '保存中...' : '保存配置'}
                            </Button>
                        </>
                    )}
                </CardContent>
            </Card>

            {/* 转码任务列表 */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Film className="w-6 h-6 text-purple-600"/>
                            <div>
                                <CardTitle>转码任务</CardTitle>
                                <CardDescription>查看和管理视频转码任务</CardDescription>
                            </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={loadData}>
                            <RefreshCw className="w-4 h-4 mr-2"/>
                            刷新
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="border rounded-lg">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>文件名</TableHead>
                                    <TableHead>状态</TableHead>
                                    <TableHead>进度</TableHead>
                                    <TableHead>输出分辨率</TableHead>
                                    <TableHead>创建时间</TableHead>
                                    <TableHead>操作</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {tasks.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                                            暂无转码任务
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    tasks.map((task) => (
                                        <TableRow key={task.id}>
                                            <TableCell className="font-mono text-sm max-w-xs truncate">
                                                {task.filename}
                                            </TableCell>
                                            <TableCell>{getStatusBadge(task.status)}</TableCell>
                                            <TableCell>
                                                {task.status === 'processing' && (
                                                    <div className="flex items-center gap-2">
                                                        <Progress value={task.progress} className="w-24"/>
                                                        <span className="text-sm">{task.progress}%</span>
                                                    </div>
                                                )}
                                                {task.status === 'completed' && (
                                                    <span className="text-green-600">100%</span>
                                                )}
                                                {task.status === 'pending' && (
                                                    <span className="text-gray-500">-</span>
                                                )}
                                                {task.status === 'failed' && (
                                                    <span className="text-red-600">失败</span>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-wrap gap-1">
                                                    {task.output_resolutions.map((res) => (
                                                        <Badge key={res} variant="outline" className="text-xs">
                                                            {res}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </TableCell>
                                            <TableCell className="whitespace-nowrap">
                                                {formatDate(task.created_at)}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex gap-2">
                                                    {task.status === 'failed' && (
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => startTranscode(task.video_id)}
                                                        >
                                                            <Play className="w-4 h-4 mr-1"/>
                                                            重试
                                                        </Button>
                                                    )}
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => deleteTask(task.id)}
                                                        className="text-destructive hover:text-destructive"
                                                    >
                                                        <Trash2 className="w-4 h-4"/>
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
