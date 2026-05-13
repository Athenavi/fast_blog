/**
 * 备份管理页面
 */

'use client';

import {useEffect, useState} from 'react';

interface Backup {
    name: string;
    created_at: string;
    size: number;
    type: string;
}

export default function BackupPage() {
    const [backups, setBackups] = useState<Backup[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);

    useEffect(() => {
        loadBackups();
    }, []);

    const loadBackups = async () => {
        try {
            const response = await fetch('/api/v2/system/backup/list');
            const result = await response.json();

            if (result.success && result.data) {
                setBackups((result.data as any).backups);
            }
        } catch (error) {
            console.error('加载备份失败:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateBackup = async () => {
        if (!confirm('确定要创建备份吗?')) return;

        setIsCreating(true);
        try {
            const response = await fetch('/api/v2/system/backup/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({include_files: true}),
            });

            const result = await response.json();

            if (result.success) {
                alert('备份创建成功');
                loadBackups();
            } else {
                alert(`备份失败: ${result.error}`);
            }
        } catch (error) {
            console.error('创建备份失败:', error);
            alert('创建备份失败');
        } finally {
            setIsCreating(false);
        }
    };

    const handleRestore = async (backupName: string) => {
        if (!confirm(`确定要恢复备�?"${backupName}" �?此操作不可�?`)) return;

        try {
            const response = await fetch('/api/v2/system/backup/restore', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({backup_name: backupName}),
            });

            const result = await response.json();

            if (result.success) {
                alert('恢复成功');
            } else {
                alert(`恢复失败: ${result.error}`);
            }
        } catch (error) {
            console.error('恢复失败:', error);
            alert('恢复失败');
        }
    };

    const handleDelete = async (backupName: string) => {
        if (!confirm(`确定要删除备�?"${backupName}" �?`)) return;

        try {
            const response = await fetch(`/api/v2/system/backup/${backupName}`, {
                method: 'DELETE',
            });

            const result = await response.json();

            if (result.success) {
                alert('删除成功');
                loadBackups();
            } else {
                alert(`删除失败: ${result.error}`);
            }
        } catch (error) {
            console.error('删除失败:', error);
            alert('删除失败');
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* 头部 */}
                <div className="mb-8 flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">备份管理</h1>
                        <p className="mt-2 text-gray-600">管理和恢复系统备�?/p>
                    </div>

                    <button
                        onClick={handleCreateBackup}
                        disabled={isCreating}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isCreating ? '创建�?..' : '创建备份'}
                    </button>
                </div>

                {/* 备份列表 */}
                {isLoading ? (
                    <div className="text-center py-12">加载�?..</div>
                ) : backups.length > 0 ? (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">备份名称</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                            </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                            {backups.map((backup) => (
                                <tr key={backup.name} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">{backup.name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {new Date(backup.created_at).toLocaleString('zh-CN')}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">{formatSize(backup.size)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded ${
                          backup.type === 'full' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {backup.type === 'full' ? '完整备份' : '数据库备�?}
                      </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap space-x-2">
                                        <button
                                            onClick={() => handleRestore(backup.name)}
                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                        >
                                            恢复
                                        </button>
                                        <button
                                            onClick={() => handleDelete(backup.name)}
                                            className="text-red-600 hover:text-red-800 text-sm"
                                        >
                                            删除
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center py-12 bg-white rounded-lg">
                        <div className="text-6xl mb-4">💾</div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">暂无备份</h3>
                        <p className="text-gray-600 mb-4">创建您的第一个备份以保护数据</p>
                        <button
                            onClick={handleCreateBackup}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                            创建备份
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
