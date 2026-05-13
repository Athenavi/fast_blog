'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Switch} from '@/components/ui/switch';
import {Badge} from '@/components/ui/badge';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {useToast} from '@/hooks/use-toast';
import {CheckCircle2, Github, Lock, Save, Shield, Users} from 'lucide-react';

interface OAuthConfig {
    enabled: boolean;
    client_id?: string;
    client_secret?: string;
    redirect_uri?: string;
    auto_create_user: boolean;
    auto_link_existing: boolean;
}

interface SAMLConfig {
    enabled: boolean;
    idp_metadata_url?: string;
    sp_entity_id?: string;
    acs_url?: string;
    certificate?: string;
    private_key?: string;
}

interface LDAPConfig {
    enabled: boolean;
    server_url?: string;
    bind_dn?: string;
    bind_password?: string;
    base_dn?: string;
    user_filter?: string;
    username_attribute?: string;
    email_attribute?: string;
}

interface SSOState {
    google_oauth: OAuthConfig;
    github_oauth: OAuthConfig;
    microsoft_oauth: OAuthConfig;
    saml: SAMLConfig;
    ldap: LDAPConfig;
}

export default function SSOConfigPage() {
    const {toast} = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('oauth');

    const [ssoConfig, setSSOConfig] = useState<SSOState>({
        google_oauth: {
            enabled: false,
            auto_create_user: true,
            auto_link_existing: true,
        },
        github_oauth: {
            enabled: false,
            auto_create_user: true,
            auto_link_existing: true,
        },
        microsoft_oauth: {
            enabled: false,
            auto_create_user: true,
            auto_link_existing: true,
        },
        saml: {
            enabled: false,
        },
        ldap: {
            enabled: false,
            user_filter: '(objectClass=person)',
            username_attribute: 'uid',
            email_attribute: 'mail',
        },
    });

    useEffect(() => {
        loadSSOConfig();
    }, []);

    const loadSSOConfig = async () => {
        try {
            setLoading(true);
            const token = getAccessToken();
            const response = await fetch('/api/v2/sso/config', {
                headers: {'Authorization': `Bearer ${token}`},
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    setSSOConfig(data.data);
                }
            }
        } catch (error) {
            console.error('Failed to load SSO config:', error);
            toast({
                title: '加载失败',
                description: '无法加载SSO配置',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const saveOAuthConfig = async (provider: string) => {
        try {
            setSaving(true);
            const token = getAccessToken();
            const config = ssoConfig[`${provider}_oauth` as keyof SSOState];

            const response = await fetch(`/api/v2/sso/oauth/${provider}/config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(config),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: `${getProviderName(provider)} OAuth配置已保存`,
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save OAuth config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const saveSAMLConfig = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();

            const response = await fetch('/api/v2/sso/saml/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(ssoConfig.saml),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: 'SAML配置已保�?,
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save SAML config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const saveLDAPConfig = async () => {
        try {
            setSaving(true);
            const token = getAccessToken();

            const response = await fetch('/api/v2/sso/ldap/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(ssoConfig.ldap),
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '保存成功',
                    description: 'LDAP配置已保�?,
                });
            } else {
                throw new Error(data.error || '保存失败');
            }
        } catch (error) {
            console.error('Failed to save LDAP config:', error);
            toast({
                title: '保存失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        } finally {
            setSaving(false);
        }
    };

    const testConnection = async (type: string, provider?: string) => {
        try {
            const token = getAccessToken();
            let url = '';

            if (type === 'oauth' && provider) {
                url = `/api/v2/sso/oauth/${provider}/test`;
            } else if (type === 'saml') {
                url = '/api/v2/sso/saml/test';
            } else if (type === 'ldap') {
                url = '/api/v2/sso/ldap/test';
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: {'Authorization': `Bearer ${token}`},
            });

            const data = await response.json();

            if (data.success) {
                toast({
                    title: '测试成功',
                    description: data.message || '连接测试通过',
                });
            } else {
                throw new Error(data.error || '测试失败');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            toast({
                title: '测试失败',
                description: error instanceof Error ? error.message : '未知错误',
                variant: 'destructive',
            });
        }
    };

    const getProviderName = (provider: string) => {
        const names: Record<string, string> = {
            google: 'Google',
            github: 'GitHub',
            microsoft: 'Microsoft',
        };
        return names[provider] || provider;
    };

    const getAccessToken = () => {
        if (typeof document !== 'undefined') {
            const match = document.cookie.match(/access_token=([^;]+)/);
            return match ? match[1] : '';
        }
        return '';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">加载�?..</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">SSO单点登录配置</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    配置OAuth、SAML和LDAP单点登录集成
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="oauth" className="flex items-center gap-2">
                        <Users className="w-4 h-4"/>
                        OAuth配置
                    </TabsTrigger>
                    <TabsTrigger value="saml" className="flex items-center gap-2">
                        <Shield className="w-4 h-4"/>
                        SAML配置
                    </TabsTrigger>
                    <TabsTrigger value="ldap" className="flex items-center gap-2">
                        <Lock className="w-4 h-4"/>
                        LDAP配置
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="oauth" className="space-y-6 mt-6">
                    {/* Google OAuth */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
                                        <span className="text-white font-bold text-lg">G</span>
                                    </div>
                                    <div>
                                        <CardTitle>Google OAuth</CardTitle>
                                        <CardDescription>使用Google账号登录</CardDescription>
                                    </div>
                                </div>
                                {ssoConfig.google_oauth.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="google-enabled">启用 Google OAuth</Label>
                                <Switch
                                    id="google-enabled"
                                    checked={ssoConfig.google_oauth.enabled}
                                    onCheckedChange={(checked) =>
                                        setSSOConfig({
                                            ...ssoConfig,
                                            google_oauth: {...ssoConfig.google_oauth, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {ssoConfig.google_oauth.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="google-client-id">Client ID</Label>
                                        <Input
                                            id="google-client-id"
                                            placeholder="xxxxxxxxxxxx.apps.googleusercontent.com"
                                            value={ssoConfig.google_oauth.client_id || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    google_oauth: {
                                                        ...ssoConfig.google_oauth,
                                                        client_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="google-client-secret">Client Secret</Label>
                                        <Input
                                            id="google-client-secret"
                                            type="password"
                                            placeholder="GOCSPX-xxxxxxxxxxxx"
                                            value={ssoConfig.google_oauth.client_secret || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    google_oauth: {
                                                        ...ssoConfig.google_oauth,
                                                        client_secret: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="google-redirect-uri">Redirect URI</Label>
                                        <Input
                                            id="google-redirect-uri"
                                            value={ssoConfig.google_oauth.redirect_uri || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    google_oauth: {
                                                        ...ssoConfig.google_oauth,
                                                        redirect_uri: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                        <p className="text-sm text-gray-500">
                                            在Google Cloud Console中配置此URI
                                        </p>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <Label htmlFor="google-auto-create">自动创建用户</Label>
                                            <Switch
                                                id="google-auto-create"
                                                checked={ssoConfig.google_oauth.auto_create_user}
                                                onCheckedChange={(checked) =>
                                                    setSSOConfig({
                                                        ...ssoConfig,
                                                        google_oauth: {
                                                            ...ssoConfig.google_oauth,
                                                            auto_create_user: checked,
                                                        },
                                                    })
                                                }
                                            />
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveOAuthConfig('google')}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testConnection('oauth', 'google')}
                                        >
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* GitHub OAuth */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Github className="w-10 h-10"/>
                                    <div>
                                        <CardTitle>GitHub OAuth</CardTitle>
                                        <CardDescription>使用GitHub账号登录</CardDescription>
                                    </div>
                                </div>
                                {ssoConfig.github_oauth.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="github-enabled">启用 GitHub OAuth</Label>
                                <Switch
                                    id="github-enabled"
                                    checked={ssoConfig.github_oauth.enabled}
                                    onCheckedChange={(checked) =>
                                        setSSOConfig({
                                            ...ssoConfig,
                                            github_oauth: {...ssoConfig.github_oauth, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {ssoConfig.github_oauth.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="github-client-id">Client ID</Label>
                                        <Input
                                            id="github-client-id"
                                            placeholder="Iv1.xxxxxxxxxxxx"
                                            value={ssoConfig.github_oauth.client_id || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    github_oauth: {
                                                        ...ssoConfig.github_oauth,
                                                        client_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="github-client-secret">Client Secret</Label>
                                        <Input
                                            id="github-client-secret"
                                            type="password"
                                            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                                            value={ssoConfig.github_oauth.client_secret || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    github_oauth: {
                                                        ...ssoConfig.github_oauth,
                                                        client_secret: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveOAuthConfig('github')}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testConnection('oauth', 'github')}
                                        >
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* Microsoft OAuth */}
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                                        <span className="text-white font-bold text-lg">M</span>
                                    </div>
                                    <div>
                                        <CardTitle>Microsoft OAuth</CardTitle>
                                        <CardDescription>使用Microsoft账号登录</CardDescription>
                                    </div>
                                </div>
                                {ssoConfig.microsoft_oauth.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="microsoft-enabled">启用 Microsoft OAuth</Label>
                                <Switch
                                    id="microsoft-enabled"
                                    checked={ssoConfig.microsoft_oauth.enabled}
                                    onCheckedChange={(checked) =>
                                        setSSOConfig({
                                            ...ssoConfig,
                                            microsoft_oauth: {...ssoConfig.microsoft_oauth, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {ssoConfig.microsoft_oauth.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="microsoft-client-id">Client ID</Label>
                                        <Input
                                            id="microsoft-client-id"
                                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                            value={ssoConfig.microsoft_oauth.client_id || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    microsoft_oauth: {
                                                        ...ssoConfig.microsoft_oauth,
                                                        client_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="microsoft-client-secret">Client Secret</Label>
                                        <Input
                                            id="microsoft-client-secret"
                                            type="password"
                                            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                                            value={ssoConfig.microsoft_oauth.client_secret || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    microsoft_oauth: {
                                                        ...ssoConfig.microsoft_oauth,
                                                        client_secret: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={() => saveOAuthConfig('microsoft')}
                                            disabled={saving}
                                        >
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testConnection('oauth', 'microsoft')}
                                        >
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="saml" className="space-y-6 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Shield className="w-10 h-10 text-purple-600"/>
                                    <div>
                                        <CardTitle>SAML 2.0</CardTitle>
                                        <CardDescription>企业级单点登录协�?/CardDescription>
                                    </div>
                                </div>
                                {ssoConfig.saml.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="saml-enabled">启用 SAML</Label>
                                <Switch
                                    id="saml-enabled"
                                    checked={ssoConfig.saml.enabled}
                                    onCheckedChange={(checked) =>
                                        setSSOConfig({
                                            ...ssoConfig,
                                            saml: {...ssoConfig.saml, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {ssoConfig.saml.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="saml-metadata-url">IdP Metadata URL</Label>
                                        <Input
                                            id="saml-metadata-url"
                                            placeholder="https://idp.example.com/metadata"
                                            value={ssoConfig.saml.idp_metadata_url || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    saml: {
                                                        ...ssoConfig.saml,
                                                        idp_metadata_url: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="saml-entity-id">SP Entity ID</Label>
                                        <Input
                                            id="saml-entity-id"
                                            placeholder="https://yourdomain.com/saml"
                                            value={ssoConfig.saml.sp_entity_id || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    saml: {
                                                        ...ssoConfig.saml,
                                                        sp_entity_id: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="saml-certificate">X.509证书</Label>
                                        <textarea
                                            id="saml-certificate"
                                            className="w-full min-h-[120px] px-3 py-2 border rounded-md font-mono text-sm"
                                            placeholder="-----BEGIN CERTIFICATE-----..."
                                            value={ssoConfig.saml.certificate || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    saml: {
                                                        ...ssoConfig.saml,
                                                        certificate: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="flex gap-2">
                                        <Button onClick={saveSAMLConfig} disabled={saving}>
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testConnection('saml')}
                                        >
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="ldap" className="space-y-6 mt-6">
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Lock className="w-10 h-10 text-orange-600"/>
                                    <div>
                                        <CardTitle>LDAP集成</CardTitle>
                                        <CardDescription>连接到LDAP目录服务</CardDescription>
                                    </div>
                                </div>
                                {ssoConfig.ldap.enabled && (
                                    <Badge variant="default" className="bg-green-600">
                                        <CheckCircle2 className="w-3 h-3 mr-1"/>
                                        已启�? </Badge>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="ldap-enabled">启用 LDAP</Label>
                                <Switch
                                    id="ldap-enabled"
                                    checked={ssoConfig.ldap.enabled}
                                    onCheckedChange={(checked) =>
                                        setSSOConfig({
                                            ...ssoConfig,
                                            ldap: {...ssoConfig.ldap, enabled: checked},
                                        })
                                    }
                                />
                            </div>

                            {ssoConfig.ldap.enabled && (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="ldap-server">服务器URL</Label>
                                        <Input
                                            id="ldap-server"
                                            placeholder="ldap://ldap.example.com:389"
                                            value={ssoConfig.ldap.server_url || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    ldap: {
                                                        ...ssoConfig.ldap,
                                                        server_url: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="ldap-bind-dn">Bind DN</Label>
                                        <Input
                                            id="ldap-bind-dn"
                                            placeholder="cn=admin,dc=example,dc=com"
                                            value={ssoConfig.ldap.bind_dn || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    ldap: {
                                                        ...ssoConfig.ldap,
                                                        bind_dn: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="ldap-bind-password">Bind密码</Label>
                                        <Input
                                            id="ldap-bind-password"
                                            type="password"
                                            placeholder="********"
                                            value={ssoConfig.ldap.bind_password || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    ldap: {
                                                        ...ssoConfig.ldap,
                                                        bind_password: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="ldap-base-dn">Base DN</Label>
                                        <Input
                                            id="ldap-base-dn"
                                            placeholder="dc=example,dc=com"
                                            value={ssoConfig.ldap.base_dn || ''}
                                            onChange={(e) =>
                                                setSSOConfig({
                                                    ...ssoConfig,
                                                    ldap: {
                                                        ...ssoConfig.ldap,
                                                        base_dn: e.target.value,
                                                    },
                                                })
                                            }
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="ldap-username-attr">用户名属�?/Label>
                                            <Input
                                                id="ldap-username-attr"
                                                value={ssoConfig.ldap.username_attribute || ''}
                                                onChange={(e) =>
                                                    setSSOConfig({
                                                        ...ssoConfig,
                                                        ldap: {
                                                            ...ssoConfig.ldap,
                                                            username_attribute: e.target.value,
                                                        },
                                                    })
                                                }
                                            />
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="ldap-email-attr">邮箱属�?/Label>
                                            <Input
                                                id="ldap-email-attr"
                                                value={ssoConfig.ldap.email_attribute || ''}
                                                onChange={(e) =>
                                                    setSSOConfig({
                                                        ...ssoConfig,
                                                        ldap: {
                                                            ...ssoConfig.ldap,
                                                            email_attribute: e.target.value,
                                                        },
                                                    })
                                                }
                                            />
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button onClick={saveLDAPConfig} disabled={saving}>
                                            <Save className="w-4 h-4 mr-2"/>
                                            {saving ? '保存�?..' : '保存配置'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => testConnection('ldap')}
                                        >
                                            测试连接
                                        </Button>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
