'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {Progress} from '@/components/ui/progress';
import {Code, Database, Globe, Image, RefreshCw, Server, Zap} from 'lucide-react';
import {toast} from 'sonner';

interface CacheStats {
    total_keys: number;
    memory_used: string;
    hit_rate: number;
    keys_by_prefix: Record<string, number>;
}

interface QueryStats {
    slow_queries_count: number;
    n_plus_one_warnings: number;
    total_queries_tracked: number;
    avg_query_time: number;
}

interface LazyLoadConfig {
    threshold: number;
    placeholder_color: string;
    fade_duration: number;
}

interface CodeSplittingReport {
    total_chunks: number;
    total_size_kb: number;
    recommendations_count: number;
}

interface ISRStats {
    total_pages: number;
    active_pages?: number;
    cache_hits: number;
    cache_misses: number;
    background_revalidations: number;
}

interface CDNStats {
    total_uploads: number;
    successful_uploads: number;
    cache_hits: number;
    active_providers: number;
}

export default function PerformanceOptimizationPage() {
    const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
    const [queryStats, setQueryStats] = useState<QueryStats | null>(null);
    const [lazyLoadConfig, setLazyLoadConfig] = useState<LazyLoadConfig | null>(null);
    const [codeSplittingReport, setCodeSplittingReport] = useState<CodeSplittingReport | null>(null);
    const [isrStats, setIsrStats] = useState<ISRStats | null>(null);
    const [cdnStats, setCdnStats] = useState<CDNStats | null>(null);
    const [loading, setLoading] = useState(false);

    const fetchAllStats = async () => {
        setLoading(true);
        try {
            await Promise.all([
                fetchCacheStats(),
                fetchQueryStats(),
                fetchLazyLoadConfig(),
                fetchCodeSplittingReport(),
                fetchISRStats(),
                fetchCDNStats()
            ]);
        } catch (error) {
            toast.error('获取统计数据失败');
        } finally {
            setLoading(false);
        }
    };

    const fetchCacheStats = async () => {
        try {
            const res = await fetch('/api/v2/cache-optimization/stats');
            const data = await res.json();
            if (data.success) {
                setCacheStats(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch cache stats:', error);
        }
    };

    const fetchQueryStats = async () => {
        try {
            const res = await fetch('/api/v2/query-optimization/stats');
            const data = await res.json();
            if (data.success) {
                setQueryStats(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch query stats:', error);
        }
    };

    const fetchLazyLoadConfig = async () => {
        try {
            const res = await fetch('/api/v2/lazy-load/config');
            const data = await res.json();
            if (data.success) {
                setLazyLoadConfig(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch lazy load config:', error);
        }
    };

    const fetchCodeSplittingReport = async () => {
        try {
            const res = await fetch('/api/v2/code-splitting/report');
            const data = await res.json();
            if (data.success) {
                setCodeSplittingReport(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch code splitting report:', error);
        }
    };

    const fetchISRStats = async () => {
        try {
            const res = await fetch('/api/v2/isr/stats');
            const data = await res.json();
            if (data.success) {
                setIsrStats(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch ISR stats:', error);
        }
    };

    const fetchCDNStats = async () => {
        try {
            const res = await fetch('/api/v2/cdn/stats');
            const data = await res.json();
            if (data.success) {
                setCdnStats(data.data);
            }
        } catch (error) {
            console.error('Failed to fetch CDN stats:', error);
        }
    };

    const handleClearCache = async () => {
        try {
            const res = await fetch('/api/v2/cache-optimization/clear', {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                toast.success('缓存清理成功');
                fetchCacheStats();
            } else {
                toast.error(data.error || '缓存清理失败');
            }
        } catch (error) {
            toast.error('缓存清理失败');
        }
    };

    const handleWarmupCache = async () => {
        try {
            const res = await fetch('/api/v2/cache-optimization/warmup', {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                toast.success('缓存预热成功');
                fetchCacheStats();
            } else {
                toast.error(data.error || '缓存预热失败');
            }
        } catch (error) {
            toast.error('缓存预热失败');
        }
    };

    const handleGenerateSSG = async () => {
        try {
            const res = await fetch('/api/v2/static-site/articles/batch', {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                toast.success(`静态页面生成完成，'{data.data.total}篇`);
            } else {
                toast.error(data.error || '生成失败');
            }
        } catch (error) {
            toast.error('生成失败');
        }
    };

    useEffect(() => {
        fetchAllStats();
    }, []);

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">性能优化</h1>
                    <p className="text-muted-foreground mt-1">
                        管理和监控网站性能优化功能
                    </p>
                </div>
                <Button onClick={fetchAllStats} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`}/>
                    刷新数据
                </Button>
            </div>

            <Tabs defaultValue="cache" className="space-y-4">
                <TabsList className="grid w-full grid-cols-6">
                    <TabsTrigger value="cache">
                        <Server className="w-4 h-4 mr-2"/>
                        缓存优化
                    </TabsTrigger>
                    <TabsTrigger value="query">
                        <Database className="w-4 h-4 mr-2"/>
                        查询优化
                    </TabsTrigger>
                    <TabsTrigger value="lazyload">
                        <Image className="w-4 h-4 mr-2"/>
                        懒加' </TabsTrigger>
                    <TabsTrigger value="codesplit">
                        <Code className="w-4 h-4 mr-2"/>
                        代码分割
                    </TabsTrigger>
                    <TabsTrigger value="ssg">
                        <Globe className="w-4 h-4 mr-2"/>
                        静态生' </TabsTrigger>
                    <TabsTrigger value="cdn">
                        <Zap className="w-4 h-4 mr-2"/>
                        CDN分发
                    </TabsTrigger>
                </TabsList>

                {/* 缓存优化 */}
                <TabsContent value="cache" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Server className="w-5 h-5 mr-2"/>
                                Redis缓存统计
                            </CardTitle>
                            <CardDescription>
                                查看和管理Redis缓存状' </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {cacheStats ? (
                                <>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">总键</p>
                                            <p className="text-2xl font-bold">{cacheStats.total_keys}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">内存使用</p>
                                            <p className="text-2xl font-bold">{cacheStats.memory_used}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">命中</p>
                                            <p className="text-2xl font-bold">{(cacheStats.hit_rate * 100).toFixed(1)}%</p>
                                        </div>
                                    </div>

                                    <Progress value={cacheStats.hit_rate * 100} className="h-2"/>

                                    <div className="flex gap-2">
                                        <Button onClick={handleClearCache} variant="outline">
                                            清理缓存
                                        </Button>
                                        <Button onClick={handleWarmupCache}>
                                            预热缓存
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 查询优化 */}
                <TabsContent value="query" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Database className="w-5 h-5 mr-2"/>
                                数据库查询优' </CardTitle>
                            <CardDescription>
                                监控和优化数据库查询性能
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {queryStats ? (
                                <>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">慢查询数</p>
                                            <p className="text-2xl font-bold text-red-600">{queryStats.slow_queries_count}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">N+1警告</p>
                                            <p className="text-2xl font-bold text-orange-600">{queryStats.n_plus_one_warnings}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">平均查询时间</p>
                                            <p className="text-2xl font-bold">{queryStats.avg_query_time.toFixed(2)}ms</p>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button variant="outline"
                                                onClick={() => window.open('/api/v2/query-optimization/report', '_blank')}>
                                            查看完整报告
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 懒加'*/}
                <TabsContent value="lazyload" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Image className="w-5 h-5 mr-2"/>
                                图片懒加载配' </CardTitle>
                            <CardDescription>
                                配置图片懒加载行' </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {lazyLoadConfig ? (
                                <>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">触发阈</p>
                                            <p className="text-2xl font-bold">{lazyLoadConfig.threshold}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">占位符颜</p>
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className="w-8 h-8 rounded border"
                                                    style={{backgroundColor: lazyLoadConfig.placeholder_color}}
                                                />
                                                <span
                                                    className="font-mono text-sm">{lazyLoadConfig.placeholder_color}</span>
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">淡入时长</p>
                                            <p className="text-2xl font-bold">{lazyLoadConfig.fade_duration}ms</p>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 代码分割 */}
                <TabsContent value="codesplit" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Code className="w-5 h-5 mr-2"/>
                                代码分割分析
                            </CardTitle>
                            <CardDescription>
                                分析和优化JavaScript包大' </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {codeSplittingReport ? (
                                <>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">总Chunk</p>
                                            <p className="text-2xl font-bold">{codeSplittingReport.total_chunks}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">总大</p>
                                            <p className="text-2xl font-bold">{codeSplittingReport.total_size_kb} KB</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">优化建议</p>
                                            <Badge
                                                variant={codeSplittingReport.recommendations_count > 0 ? "destructive" : "default"}>
                                                {codeSplittingReport.recommendations_count} ' </Badge>
                                        </div>
                                    </div>

                                    <Button variant="outline"
                                            onClick={() => window.open('/api/v2/code-splitting/recommendations', '_blank')}>
                                        查看详细建议
                                    </Button>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 静态生'*/}
                <TabsContent value="ssg" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Globe className="w-5 h-5 mr-2"/>
                                静态站点生' </CardTitle>
                            <CardDescription>
                                生成和管理静态HTML页面
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {isrStats ? (
                                <>
                                    <div className="grid grid-cols-4 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">活跃页面</p>
                                            <p className="text-2xl font-bold">{isrStats.active_pages}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">缓存命中</p>
                                            <p className="text-2xl font-bold text-green-600">{isrStats.cache_hits}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">缓存未命</p>
                                            <p className="text-2xl font-bold text-yellow-600">{isrStats.cache_misses}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">后台重新验证</p>
                                            <p className="text-2xl font-bold text-blue-600">{isrStats.background_revalidations}</p>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button onClick={handleGenerateSSG}>
                                            批量生成文章
                                        </Button>
                                        <Button variant="outline"
                                                onClick={() => window.open('/api/v2/static-site/stats', '_blank')}>
                                            查看详细统计
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* CDN分发 */}
                <TabsContent value="cdn" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <Zap className="w-5 h-5 mr-2"/>
                                CDN智能分发
                            </CardTitle>
                            <CardDescription>
                                管理CDN资源和缓存策' </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {cdnStats ? (
                                <>
                                    <div className="grid grid-cols-4 gap-4">
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">总上传数</p>
                                            <p className="text-2xl font-bold">{cdnStats.total_uploads}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">成功上传</p>
                                            <p className="text-2xl font-bold text-green-600">{cdnStats.successful_uploads}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">缓存命中</p>
                                            <p className="text-2xl font-bold">{cdnStats.cache_hits}</p>
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-sm text-muted-foreground">活跃提供</p>
                                            <p className="text-2xl font-bold">{cdnStats.active_providers}</p>
                                        </div>
                                    </div>

                                    <Button variant="outline"
                                            onClick={() => window.open('/api/v2/cdn/config', '_blank')}>
                                        查看CDN配置
                                    </Button>
                                </>
                            ) : (
                                <p className="text-muted-foreground">加载'..</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
