'use client';

import React, {useEffect, useState} from 'react';
import {FullVersionData, VersionService, VersionSummary} from '@/lib/api/version-service';
import VersionDisplay from '@/components/VersionDisplay';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Skeleton} from '@/components/ui/skeleton';

const VersionPage = () => {
  const [versionData, setVersionData] = useState<FullVersionData | null>(null);
  const [summary, setSummary] = useState<VersionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadVersionInfo();
  }, []);

  const loadVersionInfo = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 并行获取详细版本信息和摘要
      const [detailResponse, summaryResponse] = await Promise.all([
        VersionService.getVersionInfo(),
        VersionService.getVersionSummary()
      ]);

      if (detailResponse.success && detailResponse.data) {
        setVersionData(detailResponse.data);
      }

      if (summaryResponse.success && summaryResponse.data) {
        setSummary(summaryResponse.data);
      }

      if (!detailResponse.success && !summaryResponse.success) {
        setError(detailResponse.error || summaryResponse.error || '获取版本信息失败');
      }
    } catch (err) {
      setError('网络请求失败');
      console.error('获取版本信息失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="space-y-6">
            <Skeleton className="h-8 w-64" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map(i => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-6 w-24" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-4 w-40" />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">加载失败</h2>
            <p className="text-red-600 dark:text-red-400">{error}</p>
            <Button 
              onClick={loadVersionInfo}
              className="mt-4 bg-red-600 hover:bg-red-700"
            >
              重新加载
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">版本信息</h1>
          <p className="text-gray-600 dark:text-gray-400">
            查看系统各组件的版本信息和构建详情
          </p>
        </div>

        {/* 快捷版本概览 */}
        {summary && (
          <div className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>版本概览</span>
                  <Badge variant="outline">实时</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {summary.frontend}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">前端版本</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {summary.backend}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">后端版本</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {summary.database}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">数据库版本</div>
                  </div>
                </div>
                {summary.build_time && (
                  <div className="mt-4 pt-4 border-t text-center text-sm text-gray-500 dark:text-gray-400">
                    最后构建时间: {formatDate(summary.build_time)}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* 详细版本信息 */}
        {versionData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* 前端版本详情 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <span className="mr-2">🌐</span>
                  前端版本详情
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="font-medium">版本号:</span>
                  <span className="ml-2 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    {versionData.versions.frontend.version}
                  </span>
                </div>
                <div>
                  <span className="font-medium">框架:</span>
                  <span className="ml-2">{versionData.versions.frontend.framework}</span>
                </div>
                <div>
                  <span className="font-medium">构建时间:</span>
                  <span className="ml-2 text-sm">
                    {formatDate(versionData.versions.frontend.build_time)}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Node.js:</span>
                  <span className="ml-2">{versionData.versions.frontend.node_version}</span>
                </div>
              </CardContent>
            </Card>

            {/* 后端版本详情 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <span className="mr-2">⚙️</span>
                  后端版本详情
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="font-medium">版本号:</span>
                  <span className="ml-2 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    {versionData.versions.backend.version}
                  </span>
                </div>
                <div>
                  <span className="font-medium">框架:</span>
                  <span className="ml-2">{versionData.versions.backend.framework}</span>
                </div>
                <div>
                  <span className="font-medium">构建时间:</span>
                  <span className="ml-2 text-sm">
                    {formatDate(versionData.versions.backend.build_time)}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Python:</span>
                  <span className="ml-2">{versionData.versions.backend.python_version}</span>
                </div>
              </CardContent>
            </Card>

            {/* 数据库版本详情 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <span className="mr-2">🗄️</span>
                  数据库版本详情
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="font-medium">版本号:</span>
                  <span className="ml-2 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    {versionData.versions.database.version}
                  </span>
                </div>
                <div>
                  <span className="font-medium">迁移状态:</span>
                  <span className="ml-2">
                    <Badge 
                      variant={versionData.versions.database.migration_status === 'up_to_date' ? 'default' : 'destructive'}
                    >
                      {versionData.versions.database.migration_status}
                    </Badge>
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* 项目信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <span className="mr-2">ℹ️</span>
                  项目信息
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="font-medium">维护者:</span>
                  <span className="ml-2">{versionData.versions.author.maintainer}</span>
                </div>
                <div>
                  <span className="font-medium">仓库:</span>
                  <span className="ml-2 break-all text-sm">
                    {versionData.versions.author.repository}
                  </span>
                </div>
                <div>
                  <span className="font-medium">查询时间:</span>
                  <span className="ml-2 text-sm">
                    {formatDate(versionData.timestamp)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 操作区域 */}
        <div className="flex justify-center space-x-4">
          <Button onClick={loadVersionInfo} variant="outline">
            🔄 刷新版本信息
          </Button>
          <Button variant="outline" asChild>
            <a href="/admin" className="no-underline">
              ⚙️ 管理后台
            </a>
          </Button>
        </div>

        {/* 前端内置版本显示 */}
        <div className="mt-12 text-center">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            前端内置版本信息
          </h3>
          <VersionDisplay showDetailed={true} className="inline-block" />
        </div>
      </div>
    </div>
  );
};

export default VersionPage;