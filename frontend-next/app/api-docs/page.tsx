'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Badge} from '@/components/ui/badge';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Textarea} from '@/components/ui/textarea';
import {BookOpen, Code, Copy, ExternalLink, Play} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

export default function APIDocsPage() {
    const {toast} = useToast();
    const [apiEndpoint, setApiEndpoint] = useState('/api/v2/articles');
    const [method, setMethod] = useState('GET');
    const [headers, setHeaders] = useState('Authorization: Bearer YOUR_TOKEN\nContent-Type: application/json');
    const [body, setBody] = useState('{}');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);

    const apiModules = [
        {name: '认证授权', prefix: '/api/v2/auth', icon: '🔐', endpoints: 8},
        {name: '文章管理', prefix: '/api/v2/articles', icon: '📝', endpoints: 15},
        {name: '用户管理', prefix: '/api/v2/users', icon: '👤', endpoints: 12},
        {name: '分类管理', prefix: '/api/v2/categories', icon: '📁', endpoints: 6},
        {name: '媒体管理', prefix: '/api/v2/media', icon: '🖼�?, endpoints: 10},
        {name: '仪表�?, prefix: ' / api / v2 / dashboard', icon: '📊', endpoints: 8},
    {
        name: '插件管理', prefix
    :
        '/api/v2/plugins', icon
    :
        '🔌', endpoints
    :
        9
    }
,
    {
        name: '系统设置', prefix
    :
        '/api/v2/settings', icon
    :
        '⚙️', endpoints
    :
        7
    }
,
    {
        name: '打赏系统', prefix
    :
        '/api/v2/tips', icon
    :
        '💰', endpoints
    :
        11
    }
,
    {
        name: '广告管理', prefix
    :
        '/api/v2/ads', icon
    :
        '📢', endpoints
    :
        12
    }
,
    ];

    const codeExamples = {
        python: `import requests

# API 基础配置
BASE_URL = "http://localhost:9421/api/v1"
TOKEN = "YOUR_ACCESS_TOKEN"

# 设置请求�?headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 示例：获取文章列�?response = requests.get(
    f"{BASE_URL}/articles",
    headers=headers,
    params={"page": 1, "per_page": 10}
)

if response.status_code == 200:
    data = response.json()
    print(f"找到 {data['data']['total']} 篇文�?)
    for article in data['data']['items']:
        print(f"- {article['title']}")
else:
    print(f"错误: {response.status_code}")
    print(response.json())`,

        javascript: `// API 基础配置
const BASE_URL = 'http://localhost:9421/api/v1';
const TOKEN = 'YOUR_ACCESS_TOKEN';

// 示例：获取文章列�?async function getArticles() {
    try {
        const response = await fetch(\`\${BASE_URL}/articles?page=1&per_page=10\`, {
            method: 'GET',
            headers: {
                'Authorization': \`Bearer \${TOKEN}\`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(\`HTTP error! status: \${response.status}\`);
        }

        const data = await response.json();
        console.log(\`找到 \${data.data.total} 篇文章\`);
        
        data.data.items.forEach(article => {
            console.log(\`- \${article.title}\`);
        });
        
        return data;
    } catch (error) {
        console.error('请求失败:', error);
    }
}

getArticles();`,

        go: `package main

import (
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

// API 基础配置
const (
    BaseURL = "http://localhost:9421/api/v1"
    Token   = "YOUR_ACCESS_TOKEN"
)

// Article 结构�?type Article struct {
    ID    int    \`json:"id"\`
    Title string \`json:"title"\`
}

// APIResponse 响应结构
type APIResponse struct {
    Success bool       \`json:"success"\`
    Data    ArticleData \`json:"data"\`
}

type ArticleData struct {
    Total int       \`json:"total"\`
    Items []Article \`json:"items"\`
}

func main() {
    // 创建请求
    req, err := http.NewRequest("GET", BaseURL+"/articles?page=1&per_page=10", nil)
    if err != nil {
        fmt.Println("创建请求失败:", err)
        return
    }

    // 设置请求�?    req.Header.Set("Authorization", "Bearer "+Token)
    req.Header.Set("Content-Type", "application/json")

    // 发送请�?    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        fmt.Println("请求失败:", err)
        return
    }
    defer resp.Body.Close()

    // 读取响应
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
        fmt.Println("读取响应失败:", err)
        return
    }

    // 解析 JSON
    var result APIResponse
    if err := json.Unmarshal(body, &result); err != nil {
        fmt.Println("解析 JSON 失败:", err)
        return
    }

    fmt.Printf("找到 %d 篇文章\\n", result.Data.Total)
    for _, article := range result.Data.Items {
        fmt.Printf("- %s\\n", article.Title)
    }
}`
    };

    const handleTestRequest = async () => {
        setLoading(true);
        setResponse('');

        try {
            // 解析headers
            const headerLines = headers.split('\n').filter(line => line.trim());
            const headerObj = {};
            headerLines.forEach(line => {
                const [key, ...valueParts] = line.split(':');
                if (key && valueParts.length > 0) {
                    headerObj[key.trim()] = valueParts.join(':').trim();
                }
            });

            // 构建请求选项
            const options: RequestInit = {
                method,
                headers: headerObj,
            };

            if (method !== 'GET' && body) {
                options.body = body;
            }

            const startTime = Date.now();
            const res = await fetch(apiEndpoint, options);
            const endTime = Date.now();

            const data = await res.json();
            const responseText = {
                status: res.status,
                statusText: res.statusText,
                time: `${endTime - startTime}ms`,
                data: data
            };

            setResponse(JSON.stringify(responseText, null, 2));
        } catch (error) {
            setResponse(JSON.stringify({
                error: error.message,
                hint: '请确保API服务正在运行，并且CORS配置正确'
            }, null, 2));
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        toast({
            title: '已复�?,
            description: '代码已复制到剪贴�?,
        });
    };

    return (
        <div className="container mx-auto py-8 px-4">
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">FastBlog API 文档</h1>
                <p className="text-muted-foreground">
                    现代化的博客系统 API，提供完整的博客管理功能。支�?OpenAPI 3.0 标准�? </p>
            </div>

            <Tabs defaultValue="overview" className="space-y-6">
                <TabsList className="grid w-full max-w-2xl grid-cols-4">
                    <TabsTrigger value="overview">概览</TabsTrigger>
                    <TabsTrigger value="modules">API模块</TabsTrigger>
                    <TabsTrigger value="test">在线测试</TabsTrigger>
                    <TabsTrigger value="examples">代码示例</TabsTrigger>
                </TabsList>

                {/* 概览 */}
                <TabsContent value="overview" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>快速开�?/CardTitle>
                            <CardDescription>了解如何使用 FastBlog API</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <h3 className="font-semibold mb-2">1. 获取访问令牌</h3>
                                <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm">
{`POST /api/v2/auth/login
{
  "username": "your_username",
  "password": "your_password"
}`}
                                </pre>
                            </div>

                            <div>
                                <h3 className="font-semibold mb-2">2. 使用令牌访问API</h3>
                                <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm">
{`GET /api/v2/articles
Authorization: Bearer YOUR_ACCESS_TOKEN`}
                                </pre>
                            </div>

                            <div className="flex gap-2">
                                <Button onClick={() => window.open('/docs', '_blank')}>
                                    <BookOpen className="mr-2 h-4 w-4"/>
                                    Swagger UI
                                </Button>
                                <Button variant="outline" onClick={() => window.open('/redoc', '_blank')}>
                                    <ExternalLink className="mr-2 h-4 w-4"/>
                                    ReDoc
                                </Button>
                                <Button variant="outline" onClick={() => window.open('/openapi.json', '_blank')}>
                                    <Code className="mr-2 h-4 w-4"/>
                                    OpenAPI JSON
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">📚 完整文档</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground mb-2">
                                    访问 Swagger UI 查看完整�?API 文档和交互式测试
                                </p>
                                <Badge>Swagger UI</Badge>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">🧪 在线测试</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground mb-2">
                                    在浏览器中直接测�?API 端点，无需额外工具
                                </p>
                                <Badge>API Tester</Badge>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">💻 代码示例</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground mb-2">
                                    Python、JavaScript、Go 等多种语言的示例代�? </p>
                                <Badge>Multi-Language</Badge>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* API模块 */}
                <TabsContent value="modules">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {apiModules.map((module) => (
                            <Card key={module.prefix} className="hover:shadow-md transition-shadow">
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                <span>{module.icon}</span>
                                                {module.name}
                                            </CardTitle>
                                            <CardDescription>{module.prefix}</CardDescription>
                                        </div>
                                        <Badge variant="secondary">{module.endpoints} 个端�?/Badge>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => {
                                            setApiEndpoint(module.prefix);
                                            toast({
                                                title: '已选择',
                                                description: `已选择 ${module.name} 模块`,
                                            });
                                        }}
                                    >
                                        查看端点
                                    </Button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* 在线测试 */}
                <TabsContent value="test" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Play className="h-5 w-5"/>
                                API 测试工具
                            </CardTitle>
                            <CardDescription>在线测试 API 端点</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-2">
                                <Select value={method} onValueChange={setMethod}>
                                    <SelectTrigger className="w-32">
                                        <SelectValue/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="GET">GET</SelectItem>
                                        <SelectItem value="POST">POST</SelectItem>
                                        <SelectItem value="PUT">PUT</SelectItem>
                                        <SelectItem value="DELETE">DELETE</SelectItem>
                                        <SelectItem value="PATCH">PATCH</SelectItem>
                                    </SelectContent>
                                </Select>
                                <Input
                                    placeholder="/api/v2/articles"
                                    value={apiEndpoint}
                                    onChange={(e) => setApiEndpoint(e.target.value)}
                                />
                                <Button onClick={handleTestRequest} disabled={loading}>
                                    {loading ? '请求�?..' : '发�?}
                                </Button>
                            </div>

                            <div className="space-y-2">
                                        <Label>请求�?(每行一个，格式: Key: Value)</Label>
                                <Textarea
                                    value={headers}
                                    onChange={(e) => setHeaders(e.target.value)}
                                    className="font-mono text-sm"
                                    rows={3}
                                />
                            </div>

                            {method !== 'GET' && (
                                <div className="space-y-2">
                                    <Label>请求�?(JSON)</Label>
                                    <Textarea
                                        value={body}
                                        onChange={(e) => setBody(e.target.value)}
                                        className="font-mono text-sm"
                                        rows={5}
                                    />
                                </div>
                            )}

                            {response && (
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label>响应</Label>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => copyToClipboard(response)}
                                        >
                                            <Copy className="h-4 w-4 mr-1"/>
                                            复制
                                        </Button>
                                    </div>
                                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-96">
                                        {response}
                                    </pre>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 代码示例 */}
                <TabsContent value="examples">
                    <Tabs defaultValue="python" className="w-full">
                        <TabsList className="grid w-full max-w-md grid-cols-3">
                            <TabsTrigger value="python">Python</TabsTrigger>
                            <TabsTrigger value="javascript">JavaScript</TabsTrigger>
                            <TabsTrigger value="go">Go</TabsTrigger>
                        </TabsList>

                        <TabsContent value="python" className="mt-4">
                            <Card>
                                <CardHeader>
                                    <div className="flex justify-between items-center">
                                        <CardTitle>Python 示例</CardTitle>
                                        <Button size="sm" variant="ghost"
                                                onClick={() => copyToClipboard(codeExamples.python)}>
                                            <Copy className="h-4 w-4 mr-1"/>
                                            复制
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto text-sm">
                                        {codeExamples.python}
                                    </pre>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="javascript" className="mt-4">
                            <Card>
                                <CardHeader>
                                    <div className="flex justify-between items-center">
                                        <CardTitle>JavaScript 示例</CardTitle>
                                        <Button size="sm" variant="ghost"
                                                onClick={() => copyToClipboard(codeExamples.javascript)}>
                                            <Copy className="h-4 w-4 mr-1"/>
                                            复制
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto text-sm">
                                        {codeExamples.javascript}
                                    </pre>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="go" className="mt-4">
                            <Card>
                                <CardHeader>
                                    <div className="flex justify-between items-center">
                                        <CardTitle>Go 示例</CardTitle>
                                        <Button size="sm" variant="ghost"
                                                onClick={() => copyToClipboard(codeExamples.go)}>
                                            <Copy className="h-4 w-4 mr-1"/>
                                            复制
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto text-sm">
                                        {codeExamples.go}
                                    </pre>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </TabsContent>
            </Tabs>
        </div>
    );
}
