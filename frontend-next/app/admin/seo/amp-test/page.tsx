'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CheckCircle, XCircle, AlertTriangle, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  error_count: number;
  warning_count: number;
}

export default function AMPTestPage() {
  const [articleId, setArticleId] = useState('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [ampInfo, setAmpInfo] = useState<any>(null);

  // 加载AMP信息
  const loadAmpInfo = async () => {
    try {
      const response = await fetch('/api/v1/amp/info');
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setAmpInfo(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading AMP info:', error);
    }
  };

  // 验证文章AMP
  const validateArticle = async () => {
    if (!articleId) {
      toast.error('请输入文章ID');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/v1/amp/${articleId}/amp/validate`);
      
      if (!response.ok) {
        throw new Error('验证失败');
      }

      const result = await response.json();
      
      if (result.success) {
        setValidationResult(result.data.validation);
        toast.success('验证完成');
      } else {
        toast.error(result.error || '验证失败');
      }
    } catch (error) {
      console.error('Error validating AMP:', error);
      toast.error('验证失败');
    } finally {
      setLoading(false);
    }
  };

  // 查看AMP页面
  const viewAmpPage = () => {
    if (!articleId) {
      toast.error('请输入文章ID');
      return;
    }
    window.open(`/api/v1/amp/${articleId}/amp`, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">AMP支持测试</h1>
        <p className="text-gray-600 mt-1">Accelerated Mobile Pages - 加速移动页面</p>
      </div>

      {/* AMP信息 */}
      {ampInfo && (
        <Card>
          <CardHeader>
            <CardTitle>AMP配置信息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">状态</p>
                <Badge variant={ampInfo.enabled ? 'default' : 'secondary'}>
                  {ampInfo.enabled ? '已启用' : '未启用'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-600">CSS限制</p>
                <p className="font-medium">{ampInfo.css_limit_kb} KB</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">支持的组件</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {ampInfo.supported_components.map((comp: string) => (
                    <Badge key={comp} variant="outline">{comp}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600">文档</p>
                <a 
                  href={ampInfo.documentation} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline flex items-center"
                >
                  AMP.dev <ExternalLink className="w-3 h-3 ml-1" />
                </a>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 验证工具 */}
      <Card>
        <CardHeader>
          <CardTitle>AMP验证工具</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Input
              type="number"
              placeholder="输入文章ID"
              value={articleId}
              onChange={(e) => setArticleId(e.target.value)}
              className="max-w-xs"
            />
            <Button onClick={validateArticle} disabled={loading}>
              {loading ? '验证中...' : '验证AMP'}
            </Button>
            <Button onClick={viewAmpPage} variant="outline">
              查看AMP页面
            </Button>
          </div>

          {validationResult && (
            <div className="mt-4">
              <div className="flex items-center space-x-2 mb-4">
                {validationResult.valid ? (
                  <>
                    <CheckCircle className="w-6 h-6 text-green-600" />
                    <span className="text-lg font-semibold text-green-600">AMP验证通过</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-6 h-6 text-red-600" />
                    <span className="text-lg font-semibold text-red-600">AMP验证失败</span>
                  </>
                )}
              </div>

              {validationResult.errors.length > 0 && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>错误 ({validationResult.error_count})</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      {validationResult.errors.map((error, index) => (
                        <li key={index} className="text-sm">{error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {validationResult.warnings.length > 0 && (
                <Alert className="mb-4 border-yellow-200 bg-yellow-50">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <AlertTitle className="text-yellow-800">警告 ({validationResult.warning_count})</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      {validationResult.warnings.map((warning, index) => (
                        <li key={index} className="text-sm text-yellow-700">{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {validationResult.valid && validationResult.warnings.length === 0 && (
                <Alert className="border-green-200 bg-green-50">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertTitle className="text-green-800">完美!</AlertTitle>
                  <AlertDescription className="text-green-700">
                    AMP页面符合所有规范要求
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AMP说明 */}
      <Card>
        <CardHeader>
          <CardTitle>什么是AMP?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-700">
            <strong>AMP (Accelerated Mobile Pages)</strong> 是由Google主导的开源项目,旨在提升移动设备的网页加载速度。
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-2">核心特性</h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-blue-800">
                <li>极速加载(通常&lt;1秒)</li>
                <li>预渲染和缓存</li>
                <li>简化的HTML/CSS/JS</li>
                <li>移动端优化</li>
              </ul>
            </div>
            
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-900 mb-2">技术限制</h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-green-800">
                <li>CSS限制50KB以内</li>
                <li>禁止自定义JavaScript</li>
                <li>图片必须使用&lt;amp-img&gt;</li>
                <li>内联样式有限制</li>
              </ul>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-2">SEO优势</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Google搜索结果中的AMP标识⚡</li>
              <li>更快的加载速度提升用户体验</li>
              <li>降低跳出率,提高停留时间</li>
              <li>Top Stories轮播展示机会</li>
            </ul>
          </div>

          <div className="mt-4">
            <h3 className="font-semibold text-gray-900 mb-2">使用方法</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-2">
              <li>访问文章AMP版本: <code className="bg-gray-100 px-2 py-1 rounded">/api/v1/amp/&#123;article_id&#125;/amp</code></li>
              <li>在规范页面添加链接: <code className="bg-gray-100 px-2 py-1 rounded">&lt;link rel="amphtml" href="..."&gt;</code></li>
              <li>使用验证工具检查合规性</li>
              <li>提交到Google Search Console</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
