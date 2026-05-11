'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
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
import {Database, Download, RotateCcw, Trash2} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

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

export default function BackupManagement() {
    const [backups, setBackups] = useState<Backup[]>([]);
    const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);
    const {toast} = useToast();

    // 恢复对话框状态
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
  }, []);

    const fetchData = async () => {
    try {
      setLoading(true);
        const [backupsRes, statsRes] = await Promise.all([
            fetch('/api/v1/backup/list'),
            fetch('/api/v1/backup/stats')
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

    const handleCreateBackup = async () => {
    try {
        const response = await fetch('/api/v1/backup/create', {
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
        if (!confirm('确定要删除这个备份吗？')) return;

    try {
        const response = await fetch(`/api/v1/backup/${filename}`, {
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
            const response = await fetch('/api/v1/backup/restore', {
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
        <div className="flex justify-between items-center">
            <div>
                <h1 className="text-3xl font-bold">备份管理</h1>
                <p className="text-muted-foreground mt-1">
                    管理数据库备份和恢复
                </p>
            </div>

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
                          <TableHead>文件名</TableHead>
                          <TableHead>大小</TableHead>
                          <TableHead>类型</TableHead>
                          <TableHead>文章数</TableHead>
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

        {/* 恢复备份对话框 */}
        <Dialog open={showRestoreDialog} onOpenChange={setShowRestoreDialog}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>恢复备份</DialogTitle>
                    <DialogDescription>
                        从备份文件 {selectedBackup} 恢复数据
                    </DialogDescription>
                </DialogHeader>

                <div className="py-4 space-y-4">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <p className="text-sm text-yellow-800">
                            ⚠️ 警告：恢复操作将覆盖现有数据，请谨慎操作！
                        </p>
                    </div>

                    <div className="space-y-3">
                        <Label>选择要恢复的数据类型：</Label>

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
                        {restoring ? '恢复中...' : '确认恢复'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    </div>
  );
}
