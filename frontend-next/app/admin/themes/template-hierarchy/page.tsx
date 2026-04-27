'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Info } from 'lucide-react';
import { toast } from 'sonner';

export default function TemplateHierarchyPage() {
  const [hierarchy, setHierarchy] = useState<any>(null);
  const [templates, setTemplates] = useState<any>(null);
  const [theme, setTheme] = useState('default');
  const [articleData, setArticleData] = useState({ id: '', slug: '', post_type: 'post' });
  const [resolvedTemplate, setResolvedTemplate] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // 加载层级说明
  const loadHierarchy = async () => {
    try {
      const response = await fetch('/api/v1/template-hierarchy/hierarchy');
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setHierarchy(result.data.hierarchy);
        }
      }
    } catch (error) {
      console.error('Error loading hierarchy:', error);
    }
  };

  // 加载可用模板
  const loadTemplates = async () => {
    try {
      const response = await fetch(`/api/v1/template-hierarchy/templates/${theme}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setTemplates(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading templates:', error);
    }
  };

  useEffect(() => {
    loadHierarchy();
    loadTemplates();
  }, [theme]);

  // 解析文章模板
  const handleResolveArticle = async () => {
    if (!articleData.id && !articleData.slug) {
      toast.error('请输入文章ID或Slug');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/template-hierarchy/resolve/article', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          article: {
            id: parseInt(articleData.id) || 0,
            slug: articleData.slug,
            post_type: articleData.post_type,
          },
          theme: theme,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        setResolvedTemplate(result.data);
        toast.success('模板解析成功');
      } else {
        toast.error(result.error || '解析失败');
      }
    } catch (error) {
      console.error('Error resolving template:', error);
      toast.error('解析失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">主题模板层级系统</h1>
        <p className="text-gray-600 mt-1">Template Hierarchy - WordPress风格的智能模板查找</p>
      </div>

      {/* 模板层级说明 */}
      {hierarchy && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="w-5 h-5 mr-2" />
              模板层级规则
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(hierarchy).map(([type, levels]: [string, any]) => (
                <div key={type} className="border rounded-lg p-3">
                  <h3 className="font-semibold mb-2 capitalize">{type.replace('_', ' ')}</h3>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-gray-700">
                    {levels.map((level: string, index: number) => (
                      <li key={index}>
                        <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">{level}</code>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 可用模板 */}
      {templates && (
        <Card>
          <CardHeader>
            <CardTitle>
              <div className="flex items-center justify-between">
                <span>可用模板 ({templates.theme})</span>
                <Select value={theme} onValueChange={setTheme}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default</SelectItem>
                    <SelectItem value="modern-minimal">Modern Minimal</SelectItem>
                    <SelectItem value="tech-blog">Tech Blog</SelectItem>
                    <SelectItem value="magazine">Magazine</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {templates.templates.map((tpl: string) => (
                <Badge key={tpl} variant="outline">{tpl}.html</Badge>
              ))}
            </div>
            <p className="text-sm text-gray-600 mt-2">共 {templates.count} 个模板文件</p>
          </CardContent>
        </Card>
      )}

      {/* 模板解析测试 */}
      <Card>
        <CardHeader>
          <CardTitle>模板解析测试</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">文章ID</label>
              <Input
                type="number"
                placeholder="123"
                value={articleData.id}
                onChange={(e) => setArticleData({...articleData, id: e.target.value})}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Slug</label>
              <Input
                placeholder="my-article"
                value={articleData.slug}
                onChange={(e) => setArticleData({...articleData, slug: e.target.value})}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">内容类型</label>
              <Select 
                value={articleData.post_type} 
                onValueChange={(v) => setArticleData({...articleData, post_type: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="post">Post</SelectItem>
                  <SelectItem value="page">Page</SelectItem>
                  <SelectItem value="product">Product</SelectItem>
                  <SelectItem value="event">Event</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={handleResolveArticle} disabled={loading}>
            {loading ? '解析中...' : '解析模板'}
          </Button>

          {resolvedTemplate && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>解析结果</AlertTitle>
              <AlertDescription>
                <div className="mt-2 space-y-1">
                  <p><strong>主题:</strong> {resolvedTemplate.theme}</p>
                  <p><strong>模板文件:</strong> <code className="bg-gray-100 px-2 py-1 rounded">{resolvedTemplate.template_name}</code></p>
                  <p><strong>完整路径:</strong> <code className="text-xs">{resolvedTemplate.template}</code></p>
                </div>
              </AlertDescription>
            </Alert>
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
            <AlertTitle>什么是模板层级?</AlertTitle>
            <AlertDescription>
              模板层级(Template Hierarchy)是WordPress的核心特性,允许根据页面类型自动选择最合适的模板文件。
              FastBlog实现了相同的机制,让主题开发更灵活。
            </AlertDescription>
          </Alert>

          <div>
            <h3 className="font-semibold mb-2">工作原理:</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>系统根据当前页面类型(文章/页面/归档等)确定查找范围</li>
              <li>按优先级从高到低尝试匹配模板文件</li>
              <li>找到第一个存在的模板即使用</li>
              <li>如果都不存在,回退到index.html</li>
            </ol>
          </div>

          <div>
            <h3 className="font-semibold mb-2">示例场景:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>访问文章 /hello-world → 查找 single-post-hello-world.html → single-post.html → single.html → index.html</li>
              <li>访问分类 /category/news → 查找 category-news.html → category.html → archive.html → index.html</li>
              <li>访问作者页 /author/1 → 查找 author-1.html → author.html → archive.html → index.html</li>
            </ul>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">主题开发建议:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• 至少提供 index.html 作为兜底模板</li>
              <li>• 为常用页面类型提供专用模板(single.html, page.html等)</li>
              <li>• 使用特定slug的模板定制特殊页面(page-about.html)</li>
              <li>• 保持模板命名规范,便于维护</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
