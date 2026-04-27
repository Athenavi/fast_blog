'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {ArrowLeft, ArrowRight, CheckCircle2, Loader2, XCircle} from 'lucide-react';
import apiClient from '@/lib/api-client';

type InstallStep = 'prerequisites' | 'database' | 'confirm-database' | 'admin' | 'site' | 'sample-data' | 'complete';

interface PrerequisiteCheck {
    python_version: {passed: boolean; message: string};
    database_connection: {passed: boolean; message: string};
    writable_directories: {passed: boolean; message: string};
    required_packages: {passed: boolean; message: string};
    all_passed: boolean;
}

/**
 * 一键安装向导
 */
const InstallationWizard: React.FC = () => {
    const [currentStep, setCurrentStep] = useState<InstallStep>('prerequisites');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    // 前置检查结果
    const [prerequisites, setPrerequisites] = useState<PrerequisiteCheck | null>(null);
    
    // 数据库配置
    const [dbConfig, setDbConfig] = useState({
        db_type: 'postgresql',
        host: 'localhost',
        port: '5432',
        database: 'fast_blog',
        username: 'postgres',
        password: ''
    });

    // 数据库配置摘要（用于确认）
    const [dbConfigSummary, setDbConfigSummary] = useState<any>(null);
    
    // 管理员配置
    const [adminConfig, setAdminConfig] = useState({
        username: '',
        email: '',
        password: '',
        password_confirm: ''
    });
    
    // 站点配置
    const [siteConfig, setSiteConfig] = useState({
        site_name: 'FastBlog',
        site_url: 'http://localhost:8000',
        site_description: '',
        admin_email: '',
        language: 'zh_CN'
    });
    
    // 示例数据
    const [importSampleData, setImportSampleData] = useState(true);

    // 迁移日志
    const [migrationLogs, setMigrationLogs] = useState<Array<{ type: string; message: string; timestamp: number }>>([]);

    // 检查前置条件
    const checkPrerequisites = async () => {
        setLoading(true);
        setError('');
        
        try {
            const response = await apiClient.get('/api/v1/install/prerequisites');

            if (response.success && response.data) {
                setPrerequisites(response.data as PrerequisiteCheck);
                setCurrentStep('database');
            } else {
                setError(response.error || '检查失败');
            }
        } catch (err) {
            setError('检查前置条件失败');
        } finally {
            setLoading(false);
        }
    };

    // 配置数据库
    const configureDatabase = async () => {
        setLoading(true);
        setError('');

        // 验证必要字段
        if (!dbConfig.host || !dbConfig.port || !dbConfig.username || !dbConfig.database) {
            setError('请填写所有必填字段');
            setLoading(false);
            return;
        }

        // 确保端口是有效数字
        const port = parseInt(dbConfig.port);
        if (isNaN(port) || port < 1 || port > 65535) {
            setError('端口号必须是 1-65535 之间的数字');
            setLoading(false);
            return;
        }
        
        try {
            const response = await apiClient.post('/api/v1/install/configure-database', {
                ...dbConfig,
                port: port.toString()  // 确保端口是字符串格式
            });
            
            if (response.success) {
                // 保存配置摘要用于确认
                setDbConfigSummary((response.data as any).config_summary);
                setCurrentStep('confirm-database');
            } else {
                setError(response.error || '配置失败');
            }
        } catch (err) {
            setError('配置数据库失败');
        } finally {
            setLoading(false);
        }
    };

    // 确认数据库配置并执行迁移
    const confirmDatabaseAndMigrate = async () => {
        setLoading(true);
        setError('');
        setMigrationLogs([]);  // 清空日志

        try {
            // 获取 API 基础 URL
            const config = await import('@/lib/config').then(m => m.getConfig());
            const apiUrl = `${config.API_BASE_URL}${config.API_PREFIX}/install/migration/stream`;

            console.log('[Install] Connecting to SSE:', apiUrl);

            // 使用 EventSource 连接 SSE
            const eventSource = new EventSource(apiUrl);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[Install] SSE message:', data);
                    setMigrationLogs(prev => [...prev, data]);

                    // 如果收到成功或错误消息，关闭连接
                    if (data.type === 'success' || data.type === 'error') {
                        console.log('[Install] Migration finished, type:', data.type);
                        eventSource.close();

                        if (data.type === 'success') {
                            // 迁移成功，进入下一步
                            console.log('[Install] Migration successful, moving to admin step');
                            setTimeout(() => {
                                setCurrentStep('admin');
                                setLoading(false);
                            }, 1500);
                        } else {
                            console.log('[Install] Migration failed:', data.message);
                            setError(data.message);
                            setLoading(false);
                        }
                    }
                } catch (e) {
                    console.error('[Install] 解析 SSE 数据失败:', e);
                }
            };

            eventSource.onerror = (error) => {
                console.error('[Install] SSE 连接错误:', error);
                eventSource.close();
                setError('迁移日志流连接失败');
                setLoading(false);
            };

        } catch (err) {
            console.error('[Install] 启动迁移失败:', err);
            setError('启动迁移失败');
            setLoading(false);
        }
    };

    // 创建管理员
    const createAdmin = async () => {
        if (adminConfig.password !== adminConfig.password_confirm) {
            setError('两次输入的密码不一致');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            const response = await apiClient.post('/api/v1/install/create-admin', adminConfig);
            
            if (response.success) {
                setCurrentStep('site');
            } else {
                setError(response.error || '创建失败');
            }
        } catch (err) {
            setError('创建管理员失败');
        } finally {
            setLoading(false);
        }
    };

    // 配置站点
    const configureSite = async () => {
        setLoading(true);
        setError('');
        
        try {
            const response = await apiClient.post('/api/v1/install/configure-site', siteConfig);
            
            if (response.success) {
                setCurrentStep('sample-data');
            } else {
                setError(response.error || '配置失败');
            }
        } catch (err) {
            setError('配置站点失败');
        } finally {
            setLoading(false);
        }
    };

    // 完成安装
    const completeInstallation = async () => {
        setLoading(true);
        setError('');
        
        try {
            // 完成安装（后端会自动导入示例数据）
            const response = await apiClient.post('/api/v1/install/complete', {
                import_sample_data: importSampleData,
                import_articles: true,
                import_categories: true
            });
            
            if (response.success) {
                setCurrentStep('complete');
            } else {
                setError(response.error || '完成安装失败');
            }
        } catch (err) {
            setError('完成安装失败');
        } finally {
            setLoading(false);
        }
    };

    // 渲染步骤指示器
    const renderStepIndicator = () => {
        const steps = [
            {key: 'prerequisites', label: '前置检查'},
            {key: 'database', label: '数据库配置'},
            {key: 'confirm-database', label: '确认数据库'},
            {key: 'admin', label: '管理员账号'},
            {key: 'site', label: '站点信息'},
            {key: 'sample-data', label: '示例数据'},
            {key: 'complete', label: '完成'}
        ];
        
        const currentIndex = steps.findIndex(s => s.key === currentStep);
        
        return (
            <div className="flex items-center justify-center mb-8">
                {steps.map((step, index) => (
                    <React.Fragment key={step.key}>
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium
                            ${index < currentIndex ? 'bg-green-500 text-white' : 
                              index === currentIndex ? 'bg-blue-600 text-white' : 
                              'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}`}>
                            {index < currentIndex ? <CheckCircle2 className="w-5 h-5"/> : index + 1}
                        </div>
                        {index < steps.length - 1 && (
                            <div className={`w-12 h-1 ${index < currentIndex ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`}/>
                        )}
                    </React.Fragment>
                ))}
            </div>
        );
    };

    // 渲染前置检查步骤
    const renderPrerequisitesStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>系统前置检查</CardTitle>
                <CardDescription>检查系统环境是否满足安装要求</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <Button onClick={checkPrerequisites} disabled={loading} className="w-full">
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}
                    开始检查
                </Button>
                
                {prerequisites && (
                    <div className="space-y-2">
                        <div className={`p-3 rounded-lg ${prerequisites.python_version.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                            <div className="flex items-center gap-2">
                                {prerequisites.python_version.passed ? 
                                    <CheckCircle2 className="w-5 h-5 text-green-600"/> : 
                                    <XCircle className="w-5 h-5 text-red-600"/>}
                                <span>{prerequisites.python_version.message}</span>
                            </div>
                        </div>
                        
                        <div className={`p-3 rounded-lg ${prerequisites.database_connection.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                            <div className="flex items-center gap-2">
                                {prerequisites.database_connection.passed ? 
                                    <CheckCircle2 className="w-5 h-5 text-green-600"/> : 
                                    <XCircle className="w-5 h-5 text-red-600"/>}
                                <span>{prerequisites.database_connection.message}</span>
                            </div>
                        </div>
                        
                        <div className={`p-3 rounded-lg ${prerequisites.writable_directories.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                            <div className="flex items-center gap-2">
                                {prerequisites.writable_directories.passed ? 
                                    <CheckCircle2 className="w-5 h-5 text-green-600"/> : 
                                    <XCircle className="w-5 h-5 text-red-600"/>}
                                <span>{prerequisites.writable_directories.message}</span>
                            </div>
                        </div>
                        
                        <div className={`p-3 rounded-lg ${prerequisites.required_packages.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                            <div className="flex items-center gap-2">
                                {prerequisites.required_packages.passed ? 
                                    <CheckCircle2 className="w-5 h-5 text-green-600"/> : 
                                    <XCircle className="w-5 h-5 text-red-600"/>}
                                <span>{prerequisites.required_packages.message}</span>
                            </div>
                        </div>
                        
                        {prerequisites.all_passed && (
                            <Button onClick={() => setCurrentStep('database')} className="w-full mt-4">
                                继续 <ArrowRight className="w-4 h-4 ml-2"/>
                            </Button>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );

    // 其他步骤的渲染...
    const renderDatabaseStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>数据库配置</CardTitle>
                <CardDescription>配置 PostgreSQL 数据库连接信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <Alert>
                    <CheckCircle2 className="w-4 h-4"/>
                    <AlertDescription>
                        系统仅支持 PostgreSQL 数据库。请确保已安装并运行 PostgreSQL 18+。
                    </AlertDescription>
                </Alert>

                <div className="space-y-2">
                    <Label>主机地址</Label>
                    <Input
                        value={dbConfig.host}
                        onChange={(e) => setDbConfig({...dbConfig, host: e.target.value})}
                        placeholder="localhost"
                    />
                </div>

                <div className="space-y-2">
                    <Label>端口</Label>
                    <Input
                        value={dbConfig.port}
                        onChange={(e) => setDbConfig({...dbConfig, port: e.target.value})}
                        placeholder="5432"
                    />
                </div>

                <div className="space-y-2">
                    <Label>用户名</Label>
                    <Input
                        value={dbConfig.username}
                        onChange={(e) => setDbConfig({...dbConfig, username: e.target.value})}
                    />
                </div>

                <div className="space-y-2">
                    <Label>密码</Label>
                    <Input
                        type="password"
                        value={dbConfig.password}
                        onChange={(e) => setDbConfig({...dbConfig, password: e.target.value})}
                    />
                </div>
                
                <div className="space-y-2">
                    <Label>数据库名</Label>
                    <Input 
                        value={dbConfig.database} 
                        onChange={(e) => setDbConfig({...dbConfig, database: e.target.value})}
                    />
                </div>
                
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setCurrentStep('prerequisites')}>
                        <ArrowLeft className="w-4 h-4 mr-2"/> 上一步
                    </Button>
                    <Button onClick={configureDatabase} disabled={loading} className="flex-1">
                        {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}
                        下一步
                    </Button>
                </div>
            </CardContent>
        </Card>
    );

    // 简化的其他步骤渲染
    const renderAdminStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>创建管理员账号</CardTitle>
                <CardDescription>设置超级管理员账户</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>用户名</Label>
                    <Input value={adminConfig.username} onChange={(e) => setAdminConfig({...adminConfig, username: e.target.value})}/>
                </div>
                <div className="space-y-2">
                    <Label>邮箱</Label>
                    <Input type="email" value={adminConfig.email} onChange={(e) => setAdminConfig({...adminConfig, email: e.target.value})}/>
                </div>
                <div className="space-y-2">
                    <Label>密码</Label>
                    <Input type="password" value={adminConfig.password} onChange={(e) => setAdminConfig({...adminConfig, password: e.target.value})}/>
                </div>
                <div className="space-y-2">
                    <Label>确认密码</Label>
                    <Input type="password" value={adminConfig.password_confirm} onChange={(e) => setAdminConfig({...adminConfig, password_confirm: e.target.value})}/>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setCurrentStep('confirm-database')}><ArrowLeft
                        className="w-4 h-4 mr-2"/> 上一步</Button>
                    <Button onClick={createAdmin} disabled={loading} className="flex-1">{loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}下一步</Button>
                </div>
            </CardContent>
        </Card>
    );

    const renderConfirmDatabaseStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>确认数据库配置</CardTitle>
                <CardDescription>请确认以下数据库配置信息，确认后将自动初始化数据库</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {dbConfigSummary && (
                    <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <span className="text-sm text-gray-500">主机:</span>
                                <p className="font-mono">{dbConfigSummary.host}</p>
                            </div>
                            <div>
                                <span className="text-sm text-gray-500">端口:</span>
                                <p className="font-mono">{dbConfigSummary.port}</p>
                            </div>
                            <div>
                                <span className="text-sm text-gray-500">数据库:</span>
                                <p className="font-mono">{dbConfigSummary.database}</p>
                            </div>
                            <div>
                                <span className="text-sm text-gray-500">用户:</span>
                                <p className="font-mono">{dbConfigSummary.username}</p>
                            </div>
                        </div>
                    </div>
                )}

                <Alert>
                    <CheckCircle2 className="w-4 h-4"/>
                    <AlertDescription>
                        点击“确认并初始化”后，系统将测试数据库连接并创建所有必需的表。
                        此过程可能需要几秒钟时间。
                    </AlertDescription>
                </Alert>

                {/* 迁移日志显示 */}
                {migrationLogs.length > 0 && (
                    <div
                        className="border rounded-lg p-4 bg-black text-green-400 font-mono text-sm max-h-96 overflow-y-auto">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-gray-400">迁移日志</span>
                            {loading && <Loader2 className="w-4 h-4 animate-spin"/>}
                        </div>
                        <div className="space-y-1">
                            {migrationLogs.map((log, index) => (
                                <div key={index} className={`${
                                    log.type === 'error' ? 'text-red-400' :
                                        log.type === 'success' ? 'text-green-400' :
                                            'text-gray-300'
                                }`}>
                                    {log.message}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => {
                        // 返回时清除迁移日志和错误
                        setMigrationLogs([]);
                        setError('');
                        setCurrentStep('database');
                    }}>
                        <ArrowLeft className="w-4 h-4 mr-2"/> 返回修改
                    </Button>
                    <Button onClick={confirmDatabaseAndMigrate} disabled={loading} className="flex-1">
                        {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}
                        确认并初始化
                    </Button>
                </div>
            </CardContent>
        </Card>
    );

    const renderSiteStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>站点信息配置</CardTitle>
                <CardDescription>设置站点基本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>站点名称</Label>
                    <Input value={siteConfig.site_name} onChange={(e) => setSiteConfig({...siteConfig, site_name: e.target.value})}/>
                </div>
                <div className="space-y-2">
                    <Label>站点URL</Label>
                    <Input value={siteConfig.site_url} onChange={(e) => setSiteConfig({...siteConfig, site_url: e.target.value})}/>
                </div>
                <div className="space-y-2">
                    <Label>站点描述</Label>
                    <Input value={siteConfig.site_description} onChange={(e) => setSiteConfig({...siteConfig, site_description: e.target.value})}/>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setCurrentStep('admin')}><ArrowLeft className="w-4 h-4 mr-2"/> 上一步</Button>
                    <Button onClick={configureSite} disabled={loading} className="flex-1">{loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}下一步</Button>
                </div>
            </CardContent>
        </Card>
    );

    const renderSampleDataStep = () => (
        <Card>
            <CardHeader>
                <CardTitle>导入示例数据</CardTitle>
                <CardDescription>可选:导入示例文章和分类以便快速体验</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                    <input 
                        type="checkbox" 
                        id="import-sample"
                        checked={importSampleData}
                        onChange={(e) => setImportSampleData(e.target.checked)}
                        className="w-4 h-4"
                    />
                    <Label htmlFor="import-sample">导入示例数据(5个分类,10篇文章)</Label>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setCurrentStep('site')}><ArrowLeft className="w-4 h-4 mr-2"/> 上一步</Button>
                    <Button onClick={completeInstallation} disabled={loading} className="flex-1">
                        {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : null}
                        完成安装
                    </Button>
                </div>
            </CardContent>
        </Card>
    );

    const renderCompleteStep = () => (
        <Card>
            <CardHeader>
                <CardTitle className="text-center text-2xl text-green-600">🎉 安装完成!</CardTitle>
            </CardHeader>
            <CardContent className="text-center space-y-4">
                <p className="text-lg">系统已成功安装并配置完成</p>
                <Button onClick={() => window.location.href = '/admin'} className="w-full">
                    进入管理后台
                </Button>
            </CardContent>
        </Card>
    );

    // 主渲染
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 py-12 px-4">
            <div className="max-w-3xl mx-auto">
                <h1 className="text-4xl font-bold text-center mb-8 text-gray-900 dark:text-white">
                    FastBlog 安装向导
                </h1>
                
                {renderStepIndicator()}
                
                {error && (
                    <Alert variant="destructive" className="mb-4">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}
                
                {currentStep === 'prerequisites' && renderPrerequisitesStep()}
                {currentStep === 'database' && renderDatabaseStep()}
                {currentStep === 'confirm-database' && renderConfirmDatabaseStep()}
                {currentStep === 'admin' && renderAdminStep()}
                {currentStep === 'site' && renderSiteStep()}
                {currentStep === 'sample-data' && renderSampleDataStep()}
                {currentStep === 'complete' && renderCompleteStep()}
            </div>
        </div>
    );
};

export default InstallationWizard;
