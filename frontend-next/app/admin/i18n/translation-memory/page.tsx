'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Info, Download, Upload, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function TranslationMemoryPage() {
  const [stats, setStats] = useState<any>(null);
  const [sourceText, setSourceText] = useState('');
  const [targetText, setTargetText] = useState('');
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('zh-CN');
  const [context, setContext] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);

  // 加载统计
  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/translation-memory/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setStats(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  // 添加翻译
  const handleAddTranslation = async () => {
    if (!sourceText || !targetText) {
      toast.error('请填写原文和译文');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/translation-memory/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          source_text: sourceText,
          target_text: targetText,
          source_lang: sourceLang,
          target_lang: targetLang,
          context: context,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success('翻译已添加到记忆库');
        setSourceText('');
        setTargetText('');
        setContext('');
        loadStats();
      } else {
        toast.error(result.error || '添加失败');
      }
    } catch (error) {
      console.error('Error adding translation:', error);
      toast.error('添加失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取建议
  const handleGetSuggestions = async () => {
    if (!searchText) {
      toast.error('请输入要搜索的文本');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/translation-memory/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_text: searchText,
          source_lang: sourceLang,
          target_lang: targetLang,
          threshold: 0.7,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        setSuggestions(result.data.suggestions);
        toast.success(`找到${result.data.count}条建议`);
      } else {
        toast.error(result.error || '查询失败');
      }
    } catch (error) {
      console.error('Error getting suggestions:', error);
      toast.error('查询失败');
    } finally {
      setLoading(false);
    }
  };

  // 导出记忆
  const handleExport = async () => {
    try {
      const response = await fetch('/api/v1/translation-memory/export', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'translation_memory.json';
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success('导出成功');
      }
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('导出失败');
    }
  };

  // 清除记忆
  const handleClear = async () => {
    if (!confirm('确定要清除所有翻译记忆吗?此操作不可恢复!')) {
      return;
    }

    try {
      const response = await fetch('/api/v1/translation-memory/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({}),
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success('已清除所有翻译记忆');
        setSuggestions([]);
        loadStats();
      } else {
        toast.error(result.error || '清除失败');
      }
    } catch (error) {
      console.error('Error clearing:', error);
      toast.error('清除失败');
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">翻译记忆系统</h1>
          <p className="text-gray-600 mt-1">Translation Memory - 存储和管理翻译对</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={handleExport} variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            导出
          </Button>
          <Button onClick={handleClear} variant="outline" size="sm">
            <Trash2 className="w-4 h-4 mr-2" />
            清除
          </Button>
        </div>
      </div>

      {/* 统计信息 */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="w-5 h-5 mr-2" />
              翻译记忆统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">总条目数</p>
                <p className="text-2xl font-bold">{stats.total_entries}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">语言对数量</p>
                <p className="text-2xl font-bold">{stats.language_pairs}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">存储文件</p>
                <code className="text-xs bg-gray-100 px-2 py-1 rounded block mt-1">
                  {stats.memory_file?.split('/').slice(-2).join('/')}
                </code>
              </div>
            </div>

            {stats.pairs_detail && stats.pairs_detail.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-semibold mb-2">语言对详情:</p>
                <div className="flex flex-wrap gap-2">
                  {stats.pairs_detail.map((pair: any, index: number) => (
                    <Badge key={index} variant="outline">
                      {pair.source_lang} → {pair.target_lang}: {pair.entry_count}条
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 添加翻译 */}
      <Card>
        <CardHeader>
          <CardTitle>添加翻译</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">源语言</label>
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">中文</SelectItem>
                  <SelectItem value="ja">日本語</SelectItem>
                  <SelectItem value="ko">한국어</SelectItem>
                  <SelectItem value="ar">العربية</SelectItem>
                  <SelectItem value="he">עברית</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">目标语言</label>
              <Select value={targetLang} onValueChange={setTargetLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zh-CN">中文</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="ja">日本語</SelectItem>
                  <SelectItem value="ko">한국어</SelectItem>
                  <SelectItem value="ar">العربية</SelectItem>
                  <SelectItem value="he">עברית</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">原文</label>
            <Textarea
              placeholder="输入原文..."
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              rows={2}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">译文</label>
            <Textarea
              placeholder="输入译文..."
              value={targetText}
              onChange={(e) => setTargetText(e.target.value)}
              rows={2}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">上下文(可选)</label>
            <Input
              placeholder="例如: greeting, button, menu..."
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>

          <Button onClick={handleAddTranslation} disabled={loading}>
            {loading ? '添加中...' : '添加到记忆库'}
          </Button>
        </CardContent>
      </Card>

      {/* 查找建议 */}
      <Card>
        <CardHeader>
          <CardTitle>查找翻译建议</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">搜索文本</label>
            <div className="flex space-x-2">
              <Input
                placeholder="输入要翻译的文本..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Button onClick={handleGetSuggestions} disabled={loading}>
                {loading ? '搜索中...' : '搜索'}
              </Button>
            </div>
          </div>

          {suggestions.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold">相似翻译:</p>
              {suggestions.map((suggestion, index) => (
                <div key={index} className="border rounded-lg p-3 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={suggestion.similarity >= 0.9 ? 'default' : 'secondary'}>
                      相似度: {Math.round(suggestion.similarity * 100)}%
                    </Badge>
                    <span className="text-xs text-gray-500">
                      使用次数: {suggestion.usage_count}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm"><strong>原文:</strong> {suggestion.source}</p>
                    <p className="text-sm"><strong>译文:</strong> {suggestion.target}</p>
                    {suggestion.context && (
                      <p className="text-xs text-gray-600">上下文: {suggestion.context}</p>
                    )}
                  </div>
                </div>
              ))}
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
            <AlertTitle>什么是翻译记忆?</AlertTitle>
            <AlertDescription>
              翻译记忆(Translation Memory)是一种存储原文-译文对的技术。
              当翻译新内容时,系统会自动查找相似的已有翻译,提高翻译效率和一致性。
            </AlertDescription>
          </Alert>

          <div>
            <h3 className="font-semibold mb-2">核心功能:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li><strong>存储管理:</strong> 保存原文-译文对,支持多语言对</li>
              <li><strong>相似度匹配:</strong> 使用Levenshtein算法计算文本相似度</li>
              <li><strong>自动建议:</strong> 翻译时自动推荐相似的历史翻译</li>
              <li><strong>导入导出:</strong> 支持JSON格式的数据交换</li>
              <li><strong>上下文支持:</strong> 可记录翻译的使用场景</li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-2">使用场景:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>网站国际化(i18n)翻译管理</li>
              <li>多语言内容同步</li>
              <li>术语一致性维护</li>
              <li>翻译团队协作</li>
            </ul>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">API示例:</h3>
            <pre className="text-xs text-blue-800 overflow-x-auto">
{`// 添加翻译
POST /api/v1/translation-memory/add
{
  "source_text": "Hello",
  "target_text": "你好",
  "source_lang": "en",
  "target_lang": "zh-CN"
}

// 获取建议
POST /api/v1/translation-memory/suggest
{
  "source_text": "Hello world",
  "source_lang": "en",
  "target_lang": "zh-CN",
  "threshold": 0.7
}`}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
