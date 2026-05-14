'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from '@/components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import {Checkbox} from '@/components/ui/checkbox';
import {Label} from '@/components/ui/label';
import {Input} from '@/components/ui/input';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Switch} from '@/components/ui/switch';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {useToast} from '@/hooks/use-toast';
import {Calendar, Cloud, Database, Download, RotateCcw, Save, Trash2} from 'lucide-react';

interface Backup {
    filename: string;
    size_mb: number;
  created_at: string;
    backup_type: string;
    stats: {
        articles: number;
        categories: number;
        pages: number;
        menus?: number;
        users?: number;
    };
}

interface BackupSchedule {
    enabled: boolean;
    frequency: 'daily' | 'weekly' | 'monthly';
    time: string;
    day_of_week?: number;
    day_of_month?: number;
    retention_days: number;
}

interface RemoteBackupConfig {
    enabled: boolean;
    storage_type: 's3' | 'ftp' | 'scp';
    endpoint?: string;
    bucket?: string;
    access_key?: string;
    secret_key?: string;
    ftp_host?: string;
    ftp_user?: string;
    ftp_password?: string;
    encrypt: boolean;
}

export default function BackupManagement() {
    const [backups, setBackups] = useState<Backup[]>([]);
    const [stats, setStats] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('backups');
    const {toast} = useToast();

    const [schedule, setSchedule] = useState<BackupSchedule>({
        enabled: false,
        frequency: 'daily',
        time: '02:00',
        retention_days: 30,
    });

    const [remoteConfig, setRemoteConfig] = useState<RemoteBackupConfig>({
        enabled: false,
        storage_type: 's3',
        encrypt: true,
    });

    // 恢复对话框状
    const [showRestoreDialog, setShowRestoreDialog] = useState(false);
    const [selectedBackup, setSelectedBackup] = useState<string>('');
    const [restoreOptions, setRestoreOptions] = useState({
        articles: true,
        categories: true,
        pages: true,
        menus: true,
        users: false
    });
    const [restoring, setRestoring] = useState(false);

  useEffect(() => {
      fetchData();
      loadSchedule();
      loadRemoteConfig();
  }, []);

    const fetchData = async () => {
    try {
      setLoading(true);
        const [backupsRes, statsRes] = await Promise.all([
            fetch('/api/v2/backup/list'),
            fetch('/api/v2/backup/stats')
        ]);

        const backupsData = await backupsRes.json();
        const statsData = await statsRes.json();

        if (backupsData.success) {
            setBackups(backupsData.data.backups || []);
      }
        if (statsData.success) {
            setStats(statsData.data);
        }
    } catch (error) {
        toast({
            title: '网络错误',
            variant: 'destructive'
        });
    } finally {
      setLoading(false);
    }
  };

    const loadSchedule = async () => {
        try {
            const token = getAccessToken();
            const response = await fetch('/api/v2/backup/schedule', {
                headers: {'Authorization': `Bearer ${token}`},
            });
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setSchedule(data.data);
                }
            }
        } catch (error) {
            console.error('Failed to load schedule:', error);
        }
    };

    const loadRemoteConfig = async () => {
        try {
            const token = getAccessToken();
            const response = await fetch('/api/v2/backup/remote-config', {
                headers: {'Authorization': `Bearer ${token}`},
            });
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setRemoteConfig(data.data);
                }
            }
        } catch (error) {
            console.error('Failed to load remote config:', error);
        }
    };

    const saveSchedule = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();
            const response = await fetch('/api/v2/backup/schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(schedule),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: '备份调度配置已更新',
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save schedule:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const saveRemoteConfig = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();
            const response = await fetch('/api/v2/backup/remote-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(remoteConfig),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: '异地备份配置已更新',
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save remote config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const testRemoteConnection = async () => {
        try {
            const token = getAccessToken();
            const response = await fetch('/api/v2/backup/test-remote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(remoteConfig),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '测试成功',
                    description: data.message || '远程存储连接正常',
                });
            } else {
                throw new Error(data.error || '连接测试失败');
            }
        } catch (error) {
            console.error('Remote connection test failed:', error);
            toast({
                title: '测试失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        }
    };

    const getAccessToken = async () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    const handleCreateBackup = async () => {
    try {
        const response = await fetch('/api/v2/backup/create', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            toast({
                title: '备份创建成功',
                description: `文件大小: ${data.data.file_size_mb} MB`
            });
            fetchData();
      } else {
            toast({
                title: '备份失败',
                description: data.error,
                variant: 'destructive'
            });
      }
    } catch (error) {
        toast({
            title: '网络错误',
            variant: 'destructive'
        });
    }
  };

    const handleDelete = async (filename: string) => {
        if (!confirm('确定要删除这个备份吗')) return;

    try {
        const response = await fetch(`/api/v2/backup/${filename}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            toast({
                title: '删除成功',
                description: data.data.message
            });
            fetchData();
        }
    } catch (error) {
        toast({
            title: '网络错误',
            variant: 'destructive'
        });
    }
  };

    // 打开恢复对话框
    const openRestoreDialog = (filename: string) => {
        setSelectedBackup(filename);
        setShowRestoreDialog(true);
    };

    // 执行恢复
    const handleRestore = async () => {
        if (!selectedBackup) {
            toast({
                title: '错误',
                description: '请选择要恢复的备份文件',
                variant: 'destructive'
            });
            return;
        }

        if (!confirm('警告：恢复操作将覆盖现有数据！确定要继续吗？')) {
            return;
        }

        try {
            setRestoring(true);
            const response = await fetch('/api/v2/backup/restore', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    backup_file: selectedBackup,
                    restore_options: restoreOptions
                })
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '恢复成功',
                    description: data.data.message
                });
                setShowRestoreDialog(false);
                fetchData();
            } else {
                toast({
                    title: '恢复失败',
                    description: data.error,
                    variant: 'destructive'
                });
            }
        } catch (error) {
            toast({
                title: '网络错误',
                variant: 'destructive'
            });
        } finally {
            setRestoring(false);
        }
    };

  return (
    <div className="space-y-6">
        <div>
            <h1 className="text-3xl font-bold">备份管理</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
                管理系统备份、定时调度和异地备份配置
            </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="backups" className="flex items-center gap-2">
                    <Database className="w-4 h-4"/>
                    备份列表
                </TabsTrigger>
                <TabsTrigger value="schedule" className="flex items-center gap-2">
                    <Calendar className="w-4 h-4"/>
                    定时调度
                </TabsTrigger>
                <TabsTrigger value="remote" className="flex items-center gap-2">
                    <Cloud className="w-4 h-4"/>
                    异地备份
                </TabsTrigger>
            </TabsList>

            <TabsContent value="backups" className="space-y-6 mt-6">
                <div className="flex justify-between items-center">
                    <p className="text-muted-foreground">
                        管理数据库备份和恢复
                    </p>
                    <Button onClick={handleCreateBackup}>
                        <Download className="w-4 h-4 mr-2"/>
                        创建备份
                    </Button>
                </div>

        {/* 统计信息 */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
                <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{stats.articles || 0}</div>
                    <div className="text-sm text-muted-foreground">文章</div>
                </CardContent>
            </Card>
            <Card>
                <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{stats.categories || 0}</div>
                    <div className="text-sm text-muted-foreground">分类</div>
                </CardContent>
            </Card>
            <Card>
                <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{stats.pages || 0}</div>
                    <div className="text-sm text-muted-foreground">页面</div>
                </CardContent>
            </Card>
            <Card>
                <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{stats.menus || 0}</div>
                    <div className="text-sm text-muted-foreground">菜单</div>
                </CardContent>
            </Card>
            <Card>
                <CardContent className="pt-6">
                    <div className="text-2xl font-bold">{stats.users || 0}</div>
                    <div className="text-sm text-muted-foreground">用户</div>
                </CardContent>
            </Card>
      </div>

        {/* 备份列表 */}
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center">
                    <Database className="w-5 h-5 mr-2"/>
                    备份文件列表
                </CardTitle>
            </CardHeader>
            <CardContent>
          {loading ? (
              <div className="text-center py-8">加载中...</div>
          ) : backups.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                  暂无备份文件
            </div>
          ) : (
              <Table>
                  <TableHeader>
                      <TableRow>
                          <TableHead>文件</TableHead>
                          <TableHead>大小</TableHead>
                          <TableHead>类型</TableHead>
                          <TableHead>文章</TableHead>
                          <TableHead>创建时间</TableHead>
                          <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                  </TableHeader>
                  <TableBody>
                      {backups.map((backup) => (
                          <TableRow key={backup.filename}>
                              <TableCell className="font-mono text-sm">
                                  {backup.filename}
                              </TableCell>
                              <TableCell>{backup.size_mb} MB</TableCell>
                              <TableCell>
                                  <Badge variant="outline">{backup.backup_type}</Badge>
                              </TableCell>
                              <TableCell>{backup.stats.articles}</TableCell>
                              <TableCell>
                                  {new Date(backup.created_at).toLocaleString('zh-CN')}
                              </TableCell>
                              <TableCell className="text-right space-x-2">
                                  <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => openRestoreDialog(backup.filename)}
                                      title="恢复备份"
                                  >
                                      <RotateCcw className="w-4 h-4"/>
                                  </Button>
                                  <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleDelete(backup.filename)}
                                      className="text-destructive hover:text-destructive"
                                      title="删除备份"
                                  >
                                      <Trash2 className="w-4 h-4"/>
                                  </Button>
                              </TableCell>
                          </TableRow>
                      ))}
                  </TableBody>
              </Table>
          )}
            </CardContent>
        </Card>
            </TabsContent>

            <TabsContent value="schedule" className="space-y-6 mt-6">
                <Card>
                    <CardHeader>
                        <CardTitle>定时备份调度</CardTitle>
                        <CardDescription>配置自动备份计划</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="schedule-enabled">启用定时备份</Label>
                            <Switch
                                id="schedule-enabled"
                                checked={schedule.enabled}
                                onCheckedChange={(checked) =>
                                    setSchedule({...schedule, enabled: checked})
                                }
                            />
                        </div>

                        {schedule.enabled && (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>备份频率</Label>
                                        <Select
                                            value={schedule.frequency}
                                            onValueChange={(value: any) =>
                                                setSchedule({...schedule, frequency: value})
                                            }
                                        >
                                            <SelectTrigger>
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="daily">每日</SelectItem>
                                                <SelectItem value="weekly">每周</SelectItem>
                                                <SelectItem value="monthly">每月</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="space-y-2">
                                        <Label>备份时间</Label>
                                        <Input
                                            type="time"
                                            value={schedule.time}
                                            onChange={(e) =>
                                                setSchedule({...schedule, time: e.target.value})
                                            }
                                        />
                                    </div>
                                </div>

                                {schedule.frequency === 'weekly' && (
                                    <div className="space-y-2">
                                        <Label>选择星期</Label>
                                        <Select
                                            value={String(schedule.day_of_week || 1)}
                                            onValueChange={(value) =>
                                                setSchedule({...schedule, day_of_week: parseInt(value)})
                                            }
                                        >
                                            <SelectTrigger>
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="1">星期一</SelectItem>
                                                <SelectItem value="2">星期二</SelectItem>
                                                <SelectItem value="3">星期三</SelectItem>
                                                <SelectItem value="4">星期四</SelectItem>
                                                <SelectItem value="5">星期五</SelectItem>
                                                <SelectItem value="6">星期六</SelectItem>
                                                <SelectItem value="0">星期日</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}

                                {schedule.frequency === 'monthly' && (
                                    <div className="space-y-2">
                                        <Label>选择日期(1-31)</Label>
                                        <Input
                                            type="number"
                                            min="1"
                                            max="31"
                                            value={schedule.day_of_month || 1}
                                            onChange={(e) =>
                                                setSchedule({...schedule, day_of_month: parseInt(e.target.value)})
                                            }
                                        />
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <Label>保留天数</Label>
                                    <Input
                                        type="number"
                                        min="1"
                                        value={schedule.retention_days}
                                        onChange={(e) =>
                                            setSchedule({...schedule, retention_days: parseInt(e.target.value)})
                                        }
                                    />
                                    <p className="text-sm text-gray-500">
                                        超过保留天数的备份将自动删除
                                    </p>
                                </div>

                                <Button onClick={saveSchedule} disabled={saving}>
                                    <Save className="w-4 h-4 mr-2"/>
                                    {saving ? '保存' : '保存配置'}
                                </Button>
                            </>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>

            <TabsContent value="remote" className="space-y-6 mt-6">
                <Card>
                    <CardHeader>
                        <CardTitle>异地备份配置</CardTitle>
                        <CardDescription>配置远程存储进行异地备份</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="remote-enabled">启用异地备份</Label>
                            <Switch
                                id="remote-enabled"
                                checked={remoteConfig.enabled}
                                onCheckedChange={(checked) =>
                                    setRemoteConfig({...remoteConfig, enabled: checked})
                                }
                            />
                        </div>

                        {remoteConfig.enabled && (
                            <>
                                <div className="space-y-2">
                                    <Label>存储类型</Label>
                                    <Select
                                        value={remoteConfig.storage_type}
                                        onValueChange={(value: any) =>
                                            setRemoteConfig({...remoteConfig, storage_type: value})
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue/>
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="s3">Amazon S3 / 兼容服务</SelectItem>
                                            <SelectItem value="ftp">FTP</SelectItem>
                                            <SelectItem value="scp">SCP/SFTP</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {remoteConfig.storage_type === 's3' && (
                                    <>
                                        <div className="space-y-2">
                                            <Label>Endpoint URL</Label>
                                            <Input
                                                placeholder="https://s3.amazonaws.com"
                                                value={remoteConfig.endpoint || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, endpoint: e.target.value})
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Bucket名称</Label>
                                            <Input
                                                placeholder="my-backup-bucket"
                                                value={remoteConfig.bucket || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, bucket: e.target.value})
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Access Key</Label>
                                            <Input
                                                type="password"
                                                placeholder="AKIAIOSFODNN7EXAMPLE"
                                                value={remoteConfig.access_key || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, access_key: e.target.value})
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Secret Key</Label>
                                            <Input
                                                type="password"
                                                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                                                value={remoteConfig.secret_key || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, secret_key: e.target.value})
                                                }
                                            />
                                        </div>
                                    </>
                                )}

                                {remoteConfig.storage_type === 'ftp' && (
                                    <>
                                        <div className="space-y-2">
                                            <Label>FTP主机</Label>
                                            <Input
                                                placeholder="ftp.example.com"
                                                value={remoteConfig.ftp_host || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, ftp_host: e.target.value})
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>用户</Label>
                                            <Input
                                                placeholder="ftpuser"
                                                value={remoteConfig.ftp_user || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, ftp_user: e.target.value})
                                                }
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>密码</Label>
                                            <Input
                                                type="password"
                                                placeholder="********"
                                                value={remoteConfig.ftp_password || ''}
                                                onChange={(e) =>
                                                    setRemoteConfig({...remoteConfig, ftp_password: e.target.value})
                                                }
                                            />
                                        </div>
                                    </>
                                )}

                                <div className="flex items-center justify-between">
                                    <Label htmlFor="encrypt">加密备份文件</Label>
                                    <Switch
                                        id="encrypt"
                                        checked={remoteConfig.encrypt}
                                        onCheckedChange={(checked) =>
                                            setRemoteConfig({...remoteConfig, encrypt: checked})
                                        }
                                    />
                                </div>

                                <div className="flex gap-2">
                                    <Button onClick={saveRemoteConfig} disabled={saving}>
                                        <Save className="w-4 h-4 mr-2"/>
                                        {saving ? '保存' : '保存配置'}
                                    </Button>
                                    <Button variant="outline" onClick={testRemoteConnection}>
                                        测试连接
                                    </Button>
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>
        </Tabs>

        {/* 恢复备份对话'*/}
        <Dialog open={showRestoreDialog} onOpenChange={setShowRestoreDialog}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>恢复备份</DialogTitle>
                    <DialogDescription>
                        从备份文'{selectedBackup} 恢复数据
                    </DialogDescription>
                </DialogHeader>

                <div className="py-4 space-y-4">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <p className="text-sm text-yellow-800">
                            ⚠️ 警告：恢复操作将覆盖现有数据，请谨慎操作' </p>
                    </div>

                    <div className="space-y-3">
                        <Label>选择要恢复的数据类型</Label>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="restore-articles"
                                checked={restoreOptions.articles}
                                onCheckedChange={(checked) =>
                                    setRestoreOptions({...restoreOptions, articles: checked as boolean})
                                }
                            />
                            <Label htmlFor="restore-articles" className="cursor-pointer">文章</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="restore-categories"
                                checked={restoreOptions.categories}
                                onCheckedChange={(checked) =>
                                    setRestoreOptions({...restoreOptions, categories: checked as boolean})
                                }
                            />
                            <Label htmlFor="restore-categories" className="cursor-pointer">分类</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="restore-pages"
                                checked={restoreOptions.pages}
                                onCheckedChange={(checked) =>
                                    setRestoreOptions({...restoreOptions, pages: checked as boolean})
                                }
                            />
                            <Label htmlFor="restore-pages" className="cursor-pointer">页面</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="restore-menus"
                                checked={restoreOptions.menus}
                                onCheckedChange={(checked) =>
                                    setRestoreOptions({...restoreOptions, menus: checked as boolean})
                                }
                            />
                            <Label htmlFor="restore-menus" className="cursor-pointer">菜单</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="restore-users"
                                checked={restoreOptions.users}
                                onCheckedChange={(checked) =>
                                    setRestoreOptions({...restoreOptions, users: checked as boolean})
                                }
                            />
                            <Label htmlFor="restore-users" className="cursor-pointer">用户（谨慎）</Label>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setShowRestoreDialog(false)}>
                        取消
                    </Button>
                    <Button onClick={handleRestore} disabled={restoring}>
                        {restoring ? '恢复' : '确认恢复'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    </div>
  );
}
