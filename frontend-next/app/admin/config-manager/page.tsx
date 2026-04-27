'use client';

import React, {useEffect, useState} from 'react';
import {FaCloud, FaDatabase, FaEnvelope, FaSave, FaSyncAlt} from 'react-icons/fa';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {toast} from 'sonner';

interface ConfigSettings {
    mail_host: string;
    mail_port: string;
    mail_user: string;
    mail_password: string;
    s3_storage_type: string;
    s3_access_key: string;
    s3_secret_key: string;
    s3_region: string;
    s3_endpoint: string;
    s3_bucket: string;
    s3_use_ssl: string;
    redis_host: string;
    redis_port: string;
    redis_password: string;
    redis_database: string;
    site_name: string;
    site_description: string;
    site_url: string;
    enable_registration: string;
    enable_comments: string;
    theme_name: string;
}

const ConfigManager = () => {
    const [config, setConfig] = useState<ConfigSettings>({
        mail_host: '',
        mail_port: '465',
        mail_user: '',
        mail_password: '',
        s3_storage_type: 'none',
        s3_access_key: '',
        s3_secret_key: '',
        s3_region: 'us-east-1',
        s3_endpoint: '',
        s3_bucket: 'media-bucket',
        s3_use_ssl: 'true',
        redis_host: 'localhost',
        redis_port: '6379',
        redis_password: '',
        redis_database: '0',
        site_name: '我的博客',
        site_description: '这是一个很棒的博客平台',
        site_url: 'https://example.com',
        enable_registration: 'true',
        enable_comments: 'true',
        theme_name: 'default'
    });

    // Load config settings
    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        try {
            // In a real implementation, fetch from API
            // const response = await fetch('/api/admin/config');
            // if (response.ok) {
            //   const result = await response.json();
            //   if (result.success) {
            //     setConfig(result.data.settings || {});
            //   }
            // }

            // Using mock data for now
            setTimeout(() => {
                setConfig({
                    mail_host: 'smtp.example.com',
                    mail_port: '465',
                    mail_user: 'user@example.com',
                    mail_password: 'password',
                    s3_storage_type: 'minio',
                    s3_access_key: 'access-key',
                    s3_secret_key: 'secret-key',
                    s3_region: 'us-east-1',
                    s3_endpoint: 'https://s3.example.com',
                    s3_bucket: 'media-bucket',
                    s3_use_ssl: 'true',
                    redis_host: 'localhost',
                    redis_port: '6379',
                    redis_password: '',
                    redis_database: '0',
                    site_name: '我的博客',
                    site_description: '这是一个很棒的博客平台',
                    site_url: 'https://example.com',
                    enable_registration: 'true',
                    enable_comments: 'true',
                    theme_name: 'default'
                });
            }, 500);
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    };

    const handleInputChange = (field: keyof ConfigSettings, value: string) => {
        setConfig(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleSwitchChange = (field: keyof ConfigSettings, checked: boolean) => {
        setConfig(prev => ({
            ...prev,
            [field]: checked ? 'true' : 'false'
        }));
    };

    const handleMailConfigSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            // In a real implementation, send to API
            // const response = await fetch('/api/admin/config/mail', {
            //   method: 'PUT',
            //   headers: {
            //     'Content-Type': 'application/json',
            //   },
            //   body: JSON.stringify({
            //     mail_host: config.mail_host,
            //     mail_port: config.mail_port,
            //     mail_user: config.mail_user,
            //     mail_password: config.mail_password
            //   }),
            // });
            //
            // const result = await response.json();

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            toast.success('邮件配置保存成功');
        } catch (error) {
            console.error('Failed to save mail config:', error);
            toast.error('保存失败，请重试');
        }
    };

    const handleS3ConfigSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            // In a real implementation, send to API
            // const response = await fetch('/api/admin/config/s3', {
            //   method: 'PUT',
            //   headers: {
            //     'Content-Type': 'application/json',
            //   },
            //   body: JSON.stringify({
            //     s3_storage_type: config.s3_storage_type,
            //     s3_access_key: config.s3_access_key,
            //     s3_secret_key: config.s3_secret_key,
            //     s3_region: config.s3_region,
            //     s3_endpoint: config.s3_endpoint,
            //     s3_bucket: config.s3_bucket,
            //     s3_use_ssl: config.s3_use_ssl
            //   }),
            // });
            //
            // const result = await response.json();

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            toast.success('S3配置保存成功');
        } catch (error) {
            console.error('Failed to save S3 config:', error);
            toast.error('保存失败，请重试');
        }
    };

    const handleRedisConfigSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            toast.success('Redis配置保存成功');
        } catch (error) {
            console.error('Failed to save Redis config:', error);
            toast.error('保存失败，请重试');
        }
    };

    const handleSiteConfigSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            toast.success('站点配置保存成功');
        } catch (error) {
            console.error('Failed to save site config:', error);
            toast.error('保存失败，请重试');
        }
    };

    const handleRefreshConfig = async () => {
        try {
            // In a real implementation, send to API
            // const response = await fetch('/api/admin/config/refresh', {
            //   method: 'POST',
            // });
            //
            // const result = await response.json();

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            toast.success('配置刷新成功');
        } catch (error) {
            console.error('Failed to refresh config:', error);
            toast.error('刷新失败，请重试');
        }
    };

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-gray-900">系统配置管理</h1>
                        <p className="text-gray-600 mt-1">管理系统的各种配置，包括邮件、Redis、S3存储等</p>
                    </div>
                    <Button onClick={handleRefreshConfig} className="bg-green-600 hover:bg-green-700">
                        <FaSyncAlt className="mr-2"/> 刷新配置
                    </Button>
                </div>
            </div>

            <Tabs defaultValue="site" className="w-full">
                <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
                    <TabsTrigger value="mail">邮件配置</TabsTrigger>
                    <TabsTrigger value="storage">存储配置</TabsTrigger>
                    <TabsTrigger value="cache">缓存配置</TabsTrigger>
                </TabsList>

                {/* 邮件配置选项卡 */}
                <TabsContent value="mail">
                    <Card className="border border-gray-200">
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <FaEnvelope className="text-blue-500 mr-2"/> 邮件服务器配置
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleMailConfigSubmit} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <Label htmlFor="mail_host">SMTP 主机</Label>
                                        <Input
                                            type="text"
                                            id="mail_host"
                                            value={config.mail_host}
                                            onChange={(e) => handleInputChange('mail_host', e.target.value)}
                                            className="mt-1"
                                            placeholder="smtp.example.com"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="mail_port">端口</Label>
                                        <Input
                                            type="number"
                                            id="mail_port"
                                            value={config.mail_port}
                                            onChange={(e) => handleInputChange('mail_port', e.target.value)}
                                            className="mt-1"
                                        />
                                    </div>

                                    <div className="md:col-span-2">
                                        <Label htmlFor="mail_user">邮箱地址</Label>
                                        <Input
                                            type="email"
                                            id="mail_user"
                                            value={config.mail_user}
                                            onChange={(e) => handleInputChange('mail_user', e.target.value)}
                                            className="mt-1"
                                            placeholder="your-email@example.com"
                                        />
                                    </div>

                                    <div className="md:col-span-2">
                                        <Label htmlFor="mail_password">邮箱密码/授权码</Label>
                                        <Input
                                            type="password"
                                            id="mail_password"
                                            value={config.mail_password}
                                            onChange={(e) => handleInputChange('mail_password', e.target.value)}
                                            className="mt-1"
                                            placeholder="输入邮箱密码或授权码"
                                        />
                                        <p className="text-xs text-gray-500 mt-1">
                                            注意：密码将以加密形式存储
                                        </p>
                                    </div>
                                </div>

                                <div className="flex justify-end pt-4">
                                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                                        <FaSave className="mr-2"/> 保存邮件配置
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 存储配置选项卡 */}
                <TabsContent value="storage">
                    <Card className="border border-gray-200">
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <FaCloud className="text-green-500 mr-2"/> S3 存储配置
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleS3ConfigSubmit} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                    <div>
                                        <Label htmlFor="s3_storage_type">S3 存储类型</Label>
                                        <Select
                                            value={config.s3_storage_type}
                                            onValueChange={(value) => handleInputChange('s3_storage_type', value)}
                                        >
                                            <SelectTrigger className="mt-1">
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="minio">MinIO</SelectItem>
                                                <SelectItem value="aws_s3">AWS S3</SelectItem>
                                                <SelectItem value="aliyun_oss">阿里云OSS</SelectItem>
                                                <SelectItem value="tencent_cos">腾讯云COS</SelectItem>
                                                <SelectItem value="none">本地存储</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div>
                                        <Label htmlFor="s3_access_key">S3 访问密钥</Label>
                                        <Input
                                            type="text"
                                            id="s3_access_key"
                                            value={config.s3_access_key}
                                            onChange={(e) => handleInputChange('s3_access_key', e.target.value)}
                                            className="mt-1"
                                            placeholder="S3访问密钥"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="s3_secret_key">S3 密钥</Label>
                                        <Input
                                            type="password"
                                            id="s3_secret_key"
                                            value={config.s3_secret_key}
                                            onChange={(e) => handleInputChange('s3_secret_key', e.target.value)}
                                            className="mt-1"
                                            placeholder="S3密钥"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="s3_region">S3 区域</Label>
                                        <Input
                                            type="text"
                                            id="s3_region"
                                            value={config.s3_region}
                                            onChange={(e) => handleInputChange('s3_region', e.target.value)}
                                            className="mt-1"
                                            placeholder="如: us-east-1"
                                        />
                                    </div>

                                    <div className="md:col-span-2">
                                        <Label htmlFor="s3_endpoint">S3 端点</Label>
                                        <Input
                                            type="url"
                                            id="s3_endpoint"
                                            value={config.s3_endpoint}
                                            onChange={(e) => handleInputChange('s3_endpoint', e.target.value)}
                                            className="mt-1"
                                            placeholder="如: https://s3.amazonaws.com"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="s3_bucket">S3 存储桶名称</Label>
                                        <Input
                                            type="text"
                                            id="s3_bucket"
                                            value={config.s3_bucket}
                                            onChange={(e) => handleInputChange('s3_bucket', e.target.value)}
                                            className="mt-1"
                                            placeholder="存储桶名称"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="s3_use_ssl">使用SSL</Label>
                                        <Select
                                            value={config.s3_use_ssl}
                                            onValueChange={(value) => handleInputChange('s3_use_ssl', value)}
                                        >
                                            <SelectTrigger className="mt-1">
                                                <SelectValue/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="true">是</SelectItem>
                                                <SelectItem value="false">否</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="flex justify-end pt-4">
                                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                                        <FaSave className="mr-2"/> 保存S3配置
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 缓存配置选项卡 */}
                <TabsContent value="cache">
                    <Card className="border border-gray-200">
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <FaDatabase className="text-purple-500 mr-2"/> Redis 缓存配置
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleRedisConfigSubmit} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <Label htmlFor="redis_host">Redis 主机</Label>
                                        <Input
                                            type="text"
                                            id="redis_host"
                                            value={config.redis_host}
                                            onChange={(e) => handleInputChange('redis_host', e.target.value)}
                                            className="mt-1"
                                            placeholder="localhost 或 IP 地址"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="redis_port">Redis 端口</Label>
                                        <Input
                                            type="number"
                                            id="redis_port"
                                            value={config.redis_port}
                                            onChange={(e) => handleInputChange('redis_port', e.target.value)}
                                            className="mt-1"
                                            placeholder="默认: 6379"
                                        />
                                    </div>

                                    <div className="md:col-span-2">
                                        <Label htmlFor="redis_password">Redis 密码</Label>
                                        <Input
                                            type="password"
                                            id="redis_password"
                                            value={config.redis_password}
                                            onChange={(e) => handleInputChange('redis_password', e.target.value)}
                                            className="mt-1"
                                            placeholder="如果设置了密码则输入"
                                        />
                                    </div>

                                    <div>
                                        <Label htmlFor="redis_database">Redis 数据库</Label>
                                        <Input
                                            type="number"
                                            id="redis_database"
                                            value={config.redis_database}
                                            onChange={(e) => handleInputChange('redis_database', e.target.value)}
                                            className="mt-1"
                                            placeholder="默认: 0"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end pt-4">
                                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                                        <FaSave className="mr-2"/> 保存Redis配置
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default ConfigManager;