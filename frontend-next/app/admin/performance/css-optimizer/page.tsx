'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Info, Trash2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export default function CSSOptimizerPage() {
  const [htmlContent, setHtmlContent] = useState('');
  const [result, setResult] = useState<any>(null);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // 加载缓存统计
  const loadCacheStats = async () => {
    try {
      const response = await fetch('/api/v1/css-optimizer/cache/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setCacheStats(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading cache stats:', error);
    }
  };

  useEffect(() => {
    loadCacheStats();
  }, []);

  // 提取关键CSS
  const handleExtract = async () => {
    if (!htmlContent.trim()) {
      toast.error('请输入HTML内容');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/css-optimizer/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          html_content: htmlContent,
          css_files: [],
          page_type: 'article',
        }),
      });

      if (!response.ok) {
        throw new Error('提取失败');
      }

      const result = await response.json();
      
      if (result.success) {
        setResult(result.data);
        toast.success('提取完成');
        // 刷新缓存统计
        loadCacheStats();
      } else {
        toast.error(result.error || '提取失败');
      }
    } catch (error) {
      console.error('Error extracting CSS:', error);
      toast.error('提取失败');
    } finally {
      setLoading(false);
    }
  };

  // 清除缓存
  const handleClearCache = async () => {
    try {
      const response = await fetch('/api/v1/css-optimizer/cache/clear', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('清除失败');
      }

      const result = await response.json();
      
      if (result.success) {
        toast.success('缓存已清除');
        setResult(null);
        loadCacheStats();
      } else {
        toast.error(result.error || '清除失败');
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
      toast.error('清除失败');
    }
  };

  // 加载示例HTML
  const loadSampleHTML = () => {
    setHtmlContent(`<!DOCTYPE html>
<html>
<head>
  <title>Sample Article</title>
</head>
<body>
  <header>
    <nav>
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/blog">Blog</a></li>
      </ul>
    </nav>
  </header>
  
  <main>
    <article>
      <header class="article-header">
        <h1 class="article-title">Sample Article Title</h1>
        <div class="article-meta">
          <span>By John Doe</span> | 
          <span>Published on 2024-01-01</span>
        </div>
      </header>
      
      <img src="/featured.jpg" alt="Featured" class="featured-image" />
      
      <div class="article-content">
        <p>This is the article content...</p>
      </div>
    </article>
  </main>
</body>
</html>`);
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">CSS优化工具</h1>
          <p className="text-gray-600 mt-1">关键CSS提取和异步加载优化</p>
        </div>
        <Button onClick={handleClearCache} variant="outline">
          <Trash2 className="w-4 h-4 mr-2" />
          清除缓存
        </Button>
      </div>

      {/* 缓存统计 */}
      {cacheStats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="w-5 h-5 mr-2" />
              缓存统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">缓存文件数</p>
                <p className="text-2xl font-bold">{cacheStats.file_count}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">总大小</p>
                <p className="text-2xl font-bold">{cacheStats.total_size_kb} KB</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">缓存目录</p>
                <code className="text-xs bg-gray-100 px-2 py-1 rounded block mt-1">
                  {cacheStats.cache_dir?.split('/').slice(-2).join('/')}
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* HTML输入 */}
      <Card>
        <CardHeader>
          <CardTitle>HTML内容</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="粘贴HTML内容..."
            value={htmlContent}
            onChange={(e) => setHtmlContent(e.target.value)}
            rows={10}
            className="font-mono text-sm"
          />
          
          <div className="flex space-x-2">
            <Button onClick={loadSampleHTML} variant="outline" size="sm">
              加载示例
            </Button>
            <Button onClick={handleExtract} disabled={loading}>
              {loading ? '提取中...' : '提取关键CSS'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 提取结果 */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>提取结果</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Badge variant={result.cached ? 'secondary' : 'default'}>
                {result.cached ? '来自缓存' : '新生成'}
              </Badge>
              <span className="text-sm text-gray-600">
                Cache Key: {result.cache_key}
              </span>
            </div>

            <div>
              <h3 className="font-semibold mb-2">关键CSS:</h3>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                <code>{result.critical_css}</code>
              </pre>
            </div>

            <div>
              <h3 className="font-semibold mb-2">内联标签:</h3>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                <code>{result.inline_tag}</code>
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>使用说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>什么是关键CSS?</AlertTitle>
            <AlertDescription>
              关键CSS(Critical CSS)是指首屏(Above-the-fold)渲染所必需的CSS样式。
              将其内联到&lt;head&gt;中可以避免FOUC(无样式内容闪烁),提升感知加载速度。
            </AlertDescription>
          </Alert>

          <div>
            <h3 className="font-semibold mb-2">优化步骤:</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>提取首屏必需的关键CSS</li>
              <li>将关键CSS内联到&lt;style&gt;标签</li>
              <li>使用preload异步加载完整CSS文件</li>
              <li>缓存结果以提升性能</li>
            </ol>
          </div>

          <div>
            <h3 className="font-semibold mb-2">最佳实践:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>保持内联CSS在14KB以内(TCP初始拥塞窗口)</li>
              <li>使用工具自动化提取(如critical, penthouse)</li>
              <li>按页面类型分别生成(article/home/category)</li>
              <li>定期清理过期缓存</li>
            </ul>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">示例代码:</h3>
            <pre className="text-xs text-blue-800 overflow-x-auto">
{`<!-- 内联关键CSS -->
<style>
  /* Critical CSS here */
</style>

<!-- 异步加载完整CSS -->
<link rel="preload" href="/styles.css" as="style" 
      onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="/styles.css"></noscript>`}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
