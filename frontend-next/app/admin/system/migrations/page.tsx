'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Info, RefreshCw, ArrowLeft, FilePlus } from 'lucide-react';
import { toast } from 'sonner';

export default function MigrationsPage() {
  const [status, setStatus] = useState<any>(null);
  const [migrationName, setMigrationName] = useState('');
  const [rollbackVersion, setRollbackVersion] = useState('');
  const [loading, setLoading] = useState(false);

  // 加载迁移状态
  const loadStatus = async () => {
    try {
      const response = await fetch('/api/v1/migrations/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setStatus(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading status:', error);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  // 执行迁移
  const handleApplyMigrations = async () => {
    if (!confirm('确定要执行所有待处理的迁移吗?')) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/migrations/apply', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success(result.message || '迁移执行成功');
        loadStatus();
      } else {
        toast.error(result.error || '迁移失败');
      }
    } catch (error) {
      console.error('Error applying migrations:', error);
      toast.error('迁移失败');
    } finally {
      setLoading(false);
    }
  };

  // 创建迁移文件
  const handleCreateMigration = async () => {
    if (!migrationName) {
      toast.error('请填写迁移描述');
      return;
    }

    try {
      const response = await fetch('/api/v1/migrations/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          message: migrationName,
          autogenerate: false,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success(result.message || '迁移文件已创建');
        setMigrationName('');
        loadStatus();
      } else {
        toast.error(result.error || '创建失败');
      }
    } catch (error) {
      console.error('Error creating migration:', error);
      toast.error('创建失败');
    }
  };

  // 回滚迁移
  const handleRollback = async () => {
    if (!rollbackVersion) {
      toast.error('请输入回滚步数');
      return;
    }

    if (!confirm(`确定要回滚最近 ${rollbackVersion} 个迁移吗?`)) {
      return;
    }

    try {
      const response = await fetch('/api/v1/migrations/rollback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          steps: parseInt(rollbackVersion),
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success('回滚成功');
        setRollbackVersion('');
        loadStatus();
      } else {
        toast.error(result.error || '回滚失败');
      }
    } catch (error) {
      console.error('Error rolling back:', error);
      toast.error('回滚失败');
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">数据库迁移管理</h1>
        <p className="text-gray-600 mt-1">Database Migrations - 管理和执行数据库结构变更</p>
      </div>

      {/* 当前状态 */}
      {status && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center">
                <Info className="w-5 h-5 mr-2" />
                迁移状态
              </span>
              <Button onClick={loadStatus} variant="outline" size="sm">
                <RefreshCw className="w-4 h-4 mr-2" />
                刷新
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600">当前版本</p>
                <p className="text-2xl font-bold">{status.current_version}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">已应用迁移</p>
                <p className="text-2xl font-bold">{status.applied_count}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">待处理迁移</p>
                <Badge variant={status.pending_count > 0 ? 'default' : 'secondary'} className="text-lg">
                  {status.pending_count}
                </Badge>
              </div>
            </div>

            {status.pending_migrations.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-semibold mb-2">待处理迁移:</p>
                <div className="space-y-1">
                  {status.pending_migrations.map((m: any) => (
                    <div key={m.version} className="text-sm p-2 bg-yellow-50 rounded flex justify-between">
                      <span>版本 {m.version}: {m.name}</span>
                      <Badge variant="outline">Pending</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {status.applied_migrations.length > 0 && (
              <div>
                <p className="text-sm font-semibold mb-2">已应用迁移:</p>
                <div className="flex flex-wrap gap-2">
                  {status.applied_migrations.map((v: number) => (
                    <Badge key={v} variant="outline">v{v}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 执行迁移 */}
      <Card>
        <CardHeader>
          <CardTitle>执行迁移</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert className="mb-4">
            <Info className="h-4 w-4" />
            <AlertTitle>注意事项</AlertTitle>
            <AlertDescription>
              执行迁移将自动运行所有待处理的数据库变更脚本。请确保已备份数据库。
            </AlertDescription>
          </Alert>

          <Button onClick={handleApplyMigrations} disabled={loading || (status?.pending_count === 0)}>
            {loading ? '执行中...' : '执行所有待处理迁移'}
          </Button>
        </CardContent>
      </Card>

      {/* 创建迁移文件 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FilePlus className="w-5 h-5 mr-2" />
            创建 Alembic 迁移
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">迁移描述</label>
            <Input
              placeholder="例如: Add user avatar column"
              value={migrationName}
              onChange={(e) => setMigrationName(e.target.value)}
            />
          </div>

          <Button onClick={handleCreateMigration}>生成迁移文件</Button>
          
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertTitle>Alembic 说明</AlertTitle>
            <AlertDescription>
              使用 Alembic 自动生成迁移脚本。创建后需在 alembic_migrations/versions/ 目录编辑生成的文件。
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* 回滚迁移 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <ArrowLeft className="w-5 h-5 mr-2" />
            回滚迁移
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <Info className="h-4 w-4" />
            <AlertTitle>警告</AlertTitle>
            <AlertDescription>
              回滚操作不可逆,请谨慎使用。建议先备份数据库。
            </AlertDescription>
          </Alert>

          <div className="flex space-x-2">
            <Input
              type="number"
              placeholder="回滚步数 (1)"
              value={rollbackVersion}
              onChange={(e) => setRollbackVersion(e.target.value)}
              className="max-w-xs"
            />
            <Button onClick={handleRollback} variant="destructive">
              回滚
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>使用说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Alembic 工作流程:</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li><strong>创建迁移:</strong> 填写描述,生成 Alembic 迁移文件</li>
              <li><strong>编辑迁移:</strong> 在 alembic_migrations/versions/ 目录找到生成的文件,编写 upgrade/downgrade 函数</li>
              <li><strong>执行迁移:</strong> 点击“执行所有待处理迁移”按钮(alembic upgrade head)</li>
              <li><strong>验证结果:</strong> 检查数据库变更是否正确应用</li>
            </ol>
          </div>

          <div>
            <h3 className="font-semibold mb-2">迁移文件示例:</h3>
            <pre className="bg-gray-50 p-4 rounded-lg text-xs overflow-x-auto">
{`# alembic_migrations/versions/xxx_add_user_avatar.py

from alembic import op
import sqlalchemy as sa


def upgrade():
    # 添加新列
    op.add_column('users', sa.Column('avatar', sa.String(255), nullable=True))
    

def downgrade():
    # 回滚:删除列
    op.drop_column('users', 'avatar')`}
            </pre>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">最佳实践:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• 每个迁移只做一件事(添加表/修改列/插入数据)</li>
              <li>• 始终提供downgrade函数以支持回滚</li>
              <li>• 迁移文件名使用序号前缀(001_, 002_...)</li>
              <li>• 执行前务必备份数据库</li>
              <li>• 在生产环境执行前先测试</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
