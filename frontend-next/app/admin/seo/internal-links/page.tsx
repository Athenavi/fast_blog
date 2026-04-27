'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Info, Link as LinkIcon, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

export default function InternalLinksPage() {
  const [articleId, setArticleId] = useState('');
  const [suggestions, setSuggestions] = useState<any>(null);
  const [orphanArticles, setOrphanArticles] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // 获取链接建议
  const handleGetSuggestions = async () => {
    if (!articleId) {
      toast.error('请输入文章ID');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/internal-links/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          article_id: parseInt(articleId),
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        setSuggestions(result.data);
        toast.success('获取建议成功');
      } else {
        toast.error(result.error || '获取失败');
      }
    } catch (error) {
      console.error('Error getting suggestions:', error);
      toast.error('获取失败');
    } finally {
      setLoading(false);
    }
  };

  // 检测孤立文章
  const handleDetectOrphans = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/internal-links/orphan-articles', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      const result = await response.json();
      
      if (result.success) {
        setOrphanArticles(result.data);
        toast.success(`发现${result.data.orphan_count}篇孤立文章`);
      } else {
        toast.error(result.error || '检测失败');
      }
    } catch (error) {
      console.error('Error detecting orphans:', error);
      toast.error('检测失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取分析报告
  const handleGetAnalysis = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/internal-links/analysis', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      const result = await response.json();
      
      if (result.success) {
        setAnalysis(result.data);
        toast.success('分析完成');
      } else {
        toast.error(result.error || '分析失败');
      }
    } catch (error) {
      console.error('Error getting analysis:', error);
      toast.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">内部链接建议系统</h1>
        <p className="text-gray-600 mt-1">Internal Link Suggestions - 优化网站内链结构</p>
      </div>

      {/* 链接建议工具 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <LinkIcon className="w-5 h-5 mr-2" />
            获取内部链接建议
          </CardTitle>
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
            <Button onClick={handleGetSuggestions} disabled={loading}>
              {loading ? '分析中...' : '获取建议'}
            </Button>
          </div>

          {suggestions && (
            <div className="space-y-4">
              {/* 关键词 */}
              {suggestions.keywords && suggestions.keywords.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">提取的关键词:</h3>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.keywords.map((kw: any, index: number) => (
                      <Badge key={index} variant="outline">
                        {kw.keyword} ({kw.count})
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* 链接密度 */}
              <div>
                <p className="text-sm text-gray-600">链接密度: {suggestions.link_density}%</p>
                <p className="text-xs text-gray-500">建议保持在2-5%之间</p>
              </div>

              {/* 建议列表 */}
              {suggestions.suggestions && suggestions.suggestions.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">推荐链接:</h3>
                  <div className="space-y-2">
                    {suggestions.suggestions.map((item: any, index: number) => (
                      <div key={index} className="border rounded-lg p-3 bg-gray-50">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{item.title}</span>
                          <Badge variant="secondary">相关度: {item.score}</Badge>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {item.matched_keywords.map((kw: string, kwIndex: number) => (
                            <Badge key={kwIndex} variant="outline" className="text-xs">
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 孤立文章检测 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2" />
            孤立文章检测
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleDetectOrphans} disabled={loading} variant="outline">
            检测孤立文章
          </Button>

          {orphanArticles && (
            <div>
              <p className="text-sm text-gray-600 mb-2">
                发现 <strong>{orphanArticles.orphan_count}</strong> 篇孤立文章(没有被其他文章链接)
              </p>
              {orphanArticles.orphan_articles.length > 0 && (
                <div className="space-y-1 max-h-60 overflow-y-auto">
                  {orphanArticles.orphan_articles.map((article: any, index: number) => (
                    <div key={index} className="text-sm p-2 bg-yellow-50 rounded">
                      {article.title}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 内链分析 */}
      <Card>
        <CardHeader>
          <CardTitle>内链分布分析</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleGetAnalysis} disabled={loading} variant="outline">
            生成分析报告
          </Button>

          {analysis && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">总文章数</p>
                <p className="text-2xl font-bold">{analysis.total_articles}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">有出站链接的文章</p>
                <p className="text-2xl font-bold">{analysis.articles_with_outbound_links}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">有入站链接的文章</p>
                <p className="text-2xl font-bold">{analysis.articles_with_inbound_links}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">孤立文章</p>
                <p className="text-2xl font-bold text-red-600">{analysis.orphan_articles}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">平均每篇出站链接</p>
                <p className="text-2xl font-bold">{analysis.avg_outbound_per_article}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">平均每篇入站链接</p>
                <p className="text-2xl font-bold">{analysis.avg_inbound_per_article}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>使用说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>内部链接的重要性</AlertTitle>
            <AlertDescription>
              内部链接有助于搜索引擎理解网站结构,传递页面权重,提升用户体验和SEO排名。
            </AlertDescription>
          </Alert>

          <div>
            <h3 className="font-semibold mb-2">核心功能:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li><strong>关键词提取:</strong> 自动分析文章内容,提取核心关键词</li>
              <li><strong>相关文章推荐:</strong> 基于关键词匹配,推荐最相关的文章</li>
              <li><strong>孤立文章检测:</strong> 找出没有被链接的文章,优化内链结构</li>
              <li><strong>链接密度分析:</strong> 监控每篇文章的链接数量,避免过度优化</li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-2">最佳实践:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>每篇文章保持2-5个内部链接</li>
              <li>使用描述性锚文本(避免"点击这里")</li>
              <li>链接到相关内容,提升用户体验</li>
              <li>定期修复断裂链接</li>
              <li>避免循环链接(A→B→A)</li>
            </ul>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">SEO建议:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• 重要页面应获得更多内部链接</li>
              <li>• 新文章应及时添加相关链接</li>
              <li>• 定期审查孤立文章并添加链接</li>
              <li>• 保持链接密度在2-5%之间</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
