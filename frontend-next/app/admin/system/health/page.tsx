'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Download } from 'lucide-react';
import { toast } from 'sonner';

interface HealthCheckItem {
  name: string;
  value: string;
  status: 'pass' | 'fail' | 'warning' | 'info';
  score: number;
  recommendation?: string;
  error?: string;
}

interface HealthCheckCategory {
  [key: string]: HealthCheckItem[];
}

interface HealthData {
  overall_score: number;
  status: 'good' | 'warning' | 'critical';
  checks: HealthCheckCategory;
  timestamp: string;
}

export default function SiteHealthPage() {
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/system/health', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('获取健康检查数据失败');
      }

      const result = await response.json();
      if (result.success) {
        setHealthData(result.data);
      } else {
        toast.error(result.error || '获取数据失败');
      }
    } catch (error) {
      console.error('Error fetching health data:', error);
      toast.error('获取健康检查数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  const handleDownloadReport = async () => {
    try {
      const response = await fetch('/api/v1/system/health?format=text', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('下载报告失败');
      }

      const text = await response.text();
      const blob = new Blob([text], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `health_report_${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('报告已下载');
    } catch (error) {
      console.error('Error downloading report:', error);
      toast.error('下载报告失败');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'fail':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      pass: 'bg-green-100 text-green-800',
      fail: 'bg-red-100 text-red-800',
      warning: 'bg-yellow-100 text-yellow-800',
      info: 'bg-blue-100 text-blue-800',
    };
    const labels = {
      pass: '通过',
      fail: '失败',
      warning: '警告',
      info: '信息',
    };
    
    return (
      <Badge className={variants[status as keyof typeof variants]}>
        {labels[status as keyof typeof labels]}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!healthData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">无法加载健康检查数据</p>
        <Button onClick={fetchHealthData} className="mt-4">
          <RefreshCw className="w-4 h-4 mr-2" />
          重试
        </Button>
      </div>
    );
  }

  const scoreColor = healthData.overall_score >= 80 ? 'text-green-600' : 
                     healthData.overall_score >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="space-y-6">
      {/* 标题和操作 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">站点健康检查</h1>
          <p className="text-gray-600 mt-1">检查系统配置、安全性和性能</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={handleDownloadReport} variant="outline">
            <Download className="w-4 h-4 mr-2" />
            下载报告
          </Button>
          <Button onClick={fetchHealthData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            重新检查
          </Button>
        </div>
      </div>

      {/* 总体评分 */}
      <Card>
        <CardHeader>
          <CardTitle>总体评分</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className={`text-4xl font-bold ${scoreColor}`}>
                {healthData.overall_score}/100
              </span>
              <Badge 
                className={
                  healthData.status === 'good' ? 'bg-green-100 text-green-800' :
                  healthData.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }
              >
                {healthData.status === 'good' ? '良好' : 
                 healthData.status === 'warning' ? '需要关注' : '严重问题'}
              </Badge>
            </div>
            <Progress value={healthData.overall_score} className="h-3" />
            <p className="text-sm text-gray-600">
              检查时间: {new Date(healthData.timestamp).toLocaleString('zh-CN')}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 详细检查项 */}
      {Object.entries(healthData.checks).map(([category, items]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle className="capitalize">
              {category === 'system' ? '系统信息' :
               category === 'database' ? '数据库' :
               category === 'storage' ? '存储' :
               category === 'security' ? '安全' :
               category === 'performance' ? '性能' : category}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {items.map((item, index) => (
                <div key={index} className="border-b pb-4 last:border-0 last:pb-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(item.status)}
                      <span className="font-medium">{item.name}</span>
                    </div>
                    {getStatusBadge(item.status)}
                  </div>
                  <p className="text-sm text-gray-600 ml-7 mb-1">{item.value}</p>
                  {item.recommendation && (
                    <p className="text-sm text-yellow-700 ml-7 bg-yellow-50 p-2 rounded">
                      💡 {item.recommendation}
                    </p>
                  )}
                  {item.error && (
                    <p className="text-sm text-red-600 ml-7 bg-red-50 p-2 rounded">
                      错误: {item.error}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
