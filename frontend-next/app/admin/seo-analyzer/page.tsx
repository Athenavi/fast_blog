'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Textarea} from '@/components/ui/textarea';
import {Progress} from '@/components/ui/progress';
import {Badge} from '@/components/ui/badge';
import {Alert, AlertDescription} from '@/components/ui/alert';
import apiClient from '@/lib/api-client';
import {AlertTriangle, CheckCircle2, Lightbulb, Search, XCircle} from 'lucide-react';

interface SEOCheck {
    item: string;
    status: 'pass' | 'warning' | 'fail';
    message: string;
}

interface SEOAnalysisResult {
    score: number;
    grade: string;
    checks: SEOCheck[];
    suggestions: string[];
    total_checks: number;
    passed_checks: number;
    warnings: number;
    failures: number;
}

const SEOAnalyzerPage = () => {
    const [articleData, setArticleData] = useState({
        title: '',
        excerpt: '',
        content: '',
        cover_image: '',
        tags: [] as string[],
        slug: ''
    });
    const [analysisResult, setAnalysisResult] = useState<SEOAnalysisResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 执行SEO分析
    const handleAnalyze = async () => {
        if (!articleData.title) {
            setError('请至少输入文章标题');
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const response = await apiClient.post('/api/v1/seo/analyze', articleData);

            if (response.success && response.data) {
                setAnalysisResult(response.data as SEOAnalysisResult);
            } else {
                setError(response.error || '分析失败');
            }
        } catch (err: any) {
            setError(err.message || '网络请求失败');
        } finally {
            setIsLoading(false);
        }
    };

    // 获取等级颜色
    const getGradeColor = (grade: string) => {
        const colors: Record<string, string> = {
            'A': 'bg-green-500',
            'B': 'bg-blue-500',
            'C': 'bg-yellow-500',
            'D': 'bg-orange-500',
            'F': 'bg-red-500'
        };
        return colors[grade] || 'bg-gray-500';
    };

    // 获取检查项图标
    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pass':
                return <CheckCircle2 className="w-5 h-5 text-green-500"/>;
            case 'warning':
                return <AlertTriangle className="w-5 h-5 text-yellow-500"/>;
            case 'fail':
                return <XCircle className="w-5 h-5 text-red-500"/>;
            default:
                return null;
        }
    };

    // 获取检查项背景色
    const getStatusBgColor = (status: string) => {
        switch (status) {
            case 'pass':
                return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
            case 'warning':
                return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
            case 'fail':
                return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
            default:
                return 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-6xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    SEO 分析工具
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                    分析文章内容的SEO质量，获取改进建议
                </p>
            </div>

            {/* 输入表单 */}
            <Card className="mb-8">
                <CardHeader>
                    <CardTitle>文章信息</CardTitle>
                    <CardDescription>
                        输入文章内容进行SEO分析
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <Label htmlFor="title">文章标题 *</Label>
                        <Input
                            id="title"
                            value={articleData.title}
                            onChange={(e) => setArticleData({...articleData, title: e.target.value})}
                            placeholder="输入文章标题"
                        />
                    </div>

                    <div>
                        <Label htmlFor="slug">URL Slug</Label>
                        <Input
                            id="slug"
                            value={articleData.slug}
                            onChange={(e) => setArticleData({...articleData, slug: e.target.value})}
                            placeholder="my-article-slug"
                        />
                    </div>

                    <div>
                        <Label htmlFor="excerpt">文章摘要</Label>
                        <Textarea
                            id="excerpt"
                            value={articleData.excerpt}
                            onChange={(e) => setArticleData({...articleData, excerpt: e.target.value})}
                            placeholder="输入文章摘要（150-160字符）"
                            rows={3}
                        />
                    </div>

                    <div>
                        <Label htmlFor="content">文章内容</Label>
                        <Textarea
                            id="content"
                            value={articleData.content}
                            onChange={(e) => setArticleData({...articleData, content: e.target.value})}
                            placeholder="输入文章内容"
                            rows={6}
                        />
                    </div>

                    <div>
                        <Label htmlFor="cover_image">封面图片URL</Label>
                        <Input
                            id="cover_image"
                            value={articleData.cover_image}
                            onChange={(e) => setArticleData({...articleData, cover_image: e.target.value})}
                            placeholder="https://example.com/image.jpg"
                        />
                    </div>

                    <div>
                        <Label htmlFor="tags">标签（逗号分隔）</Label>
                        <Input
                            id="tags"
                            value={articleData.tags.join(', ')}
                            onChange={(e) => setArticleData({
                                ...articleData,
                                tags: e.target.value.split(',').map(t => t.trim()).filter(t => t)
                            })}
                            placeholder="技术, 编程, Python"
                        />
                    </div>

                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    <Button onClick={handleAnalyze} disabled={isLoading} className="w-full">
                        {isLoading ? (
                            <>
                                <Search className="w-4 h-4 mr-2 animate-spin"/>
                                分析中...
                            </>
                        ) : (
                            <>
                                <Search className="w-4 h-4 mr-2"/>
                                开始分析
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* 分析结果 */}
            {analysisResult && (
                <div className="space-y-6">
                    {/* 总分和等级 */}
                    <Card>
                        <CardHeader>
                            <CardTitle>SEO评分</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex-1">
                                    <div className="flex items-center space-x-4 mb-2">
                                        <span className="text-4xl font-bold">{analysisResult.score}</span>
                                        <Badge
                                            className={`${getGradeColor(analysisResult.grade)} text-white text-lg px-4 py-1`}
                                        >
                                            {analysisResult.grade}级
                                        </Badge>
                                    </div>
                                    <Progress value={analysisResult.score} className="h-3"/>
                                </div>
                            </div>

                            <div className="grid grid-cols-4 gap-4 text-center">
                                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                                        {analysisResult.passed_checks}
                                    </div>
                                    <div className="text-sm text-gray-600 dark:text-gray-400">通过</div>
                                </div>
                                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                                    <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                                        {analysisResult.warnings}
                                    </div>
                                    <div className="text-sm text-gray-600 dark:text-gray-400">警告</div>
                                </div>
                                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                    <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                                        {analysisResult.failures}
                                    </div>
                                    <div className="text-sm text-gray-600 dark:text-gray-400">失败</div>
                                </div>
                                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                        {analysisResult.total_checks}
                                    </div>
                                    <div className="text-sm text-gray-600 dark:text-gray-400">总计</div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* 检查项详情 */}
                    <Card>
                        <CardHeader>
                            <CardTitle>检查项详情</CardTitle>
                            <CardDescription>
                                共{analysisResult.total_checks}项检查
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {analysisResult.checks.map((check, index) => (
                                <div
                                    key={index}
                                    className={`p-4 rounded-lg border ${getStatusBgColor(check.status)}`}
                                >
                                    <div className="flex items-start space-x-3">
                                        {getStatusIcon(check.status)}
                                        <div className="flex-1">
                                            <div className="font-medium text-gray-900 dark:text-white mb-1">
                                                {check.item}
                                            </div>
                                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                                {check.message}
                                            </div>
                                        </div>
                                        <Badge
                                            variant={
                                                check.status === 'pass' ? 'default' :
                                                    check.status === 'warning' ? 'secondary' : 'destructive'
                                            }
                                        >
                                            {check.status === 'pass' ? '通过' :
                                                check.status === 'warning' ? '警告' : '失败'}
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    {/* 改进建议 */}
                    {analysisResult.suggestions.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center space-x-2">
                                    <Lightbulb className="w-5 h-5 text-yellow-500"/>
                                    <span>改进建议</span>
                                </CardTitle>
                                <CardDescription>
                                    共{analysisResult.suggestions.length}条建议
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-3">
                                    {analysisResult.suggestions.map((suggestion, index) => (
                                        <li key={index} className="flex items-start space-x-3">
                                            <div
                                                className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                        <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                          {index + 1}
                        </span>
                                            </div>
                                            <span className="text-gray-700 dark:text-gray-300">{suggestion}</span>
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}
        </div>
    );
};

export default SEOAnalyzerPage;
