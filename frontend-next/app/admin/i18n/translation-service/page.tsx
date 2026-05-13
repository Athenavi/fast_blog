'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Badge} from '@/components/ui/badge';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {Info, Settings} from 'lucide-react';
import {toast} from 'sonner';
import {getAccessTokenFromCookie} from '@/lib/auth-utils';

export default function TranslationServicePage() {
  const [providers, setProviders] = useState<any>(null);
  const [text, setText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('zh-CN');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [apiKey, setApiKey] = useState('');

    // 加载提供商列�?
  const loadProviders = async () => {
    try {
      const token = getAccessTokenFromCookie();
        const response = await fetch('/api/v2/translation-service/providers', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
          if (result.success && result.data) {
              setProviders(result.data as any);
              if ((result.data as any).providers.length > 0) {
                  setSelectedProvider((result.data as any).default_provider || (result.data as any).providers[0]);
          }
        }
      }
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  // 翻译文本
  const handleTranslate = async () => {
    if (!text) {
        toast.error('请输入要翻译的文�?);
      return;
    }

    if (!selectedProvider) {
      toast.error('请先配置翻译服务');
      return;
    }

    try {
      setLoading(true);
      const token = getAccessTokenFromCookie();
        const response = await fetch('/api/v2/translation-service/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          text: text,
          target_lang: targetLang,
          source_lang: sourceLang,
          provider: selectedProvider,
        }),
      });

      const result = await response.json();

        if (result.success && result.data) {
            setTranslatedText((result.data as any).translated_text);
        toast.success('翻译完成');
      } else {
        toast.error(result.error || '翻译失败');
      }
    } catch (error) {
      console.error('Error translating:', error);
      toast.error('翻译失败');
    } finally {
      setLoading(false);
    }
  };

  // 检测语言
  const handleDetectLanguage = async () => {
    if (!text) {
      toast.error('请输入要检测的文本');
      return;
    }

    try {
      setLoading(true);
      const token = getAccessTokenFromCookie();
        const response = await fetch('/api/v2/translation-service/detect-language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          text: text,
          provider: selectedProvider,
        }),
      });

      const result = await response.json();

        if (result.success && result.data) {
            setSourceLang((result.data as any).language);
            toast.success(`检测到语言: ${(result.data as any).language} (置信�? ${Math.round((result.data as any).confidence * 100)}%)`);
      } else {
            toast.error(result.error || '检测失�?);
      }
    } catch (error) {
      console.error('Error detecting language:', error);
        toast.error('检测失�?);
    } finally {
      setLoading(false);
    }
  };

  // 配置API密钥
  const handleConfigure = async () => {
    if (!apiKey) {
      toast.error('请输入API密钥');
      return;
    }

    try {
      const token = getAccessTokenFromCookie();
        const response = await fetch('/api/v2/translation-service/configure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          provider: selectedProvider,
          api_key: apiKey,
          set_as_default: true,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        toast.success('配置成功');
        setShowConfig(false);
        setApiKey('');
        loadProviders();
      } else {
        toast.error(result.error || '配置失败');
      }
    } catch (error) {
      console.error('Error configuring:', error);
      toast.error('配置失败');
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">专业翻译服务</h1>
          <p className="text-gray-600 mt-1">集成Google Translate、DeepL等翻译API</p>
        </div>
        <Button onClick={() => setShowConfig(!showConfig)} variant="outline" size="sm">
          <Settings className="w-4 h-4 mr-2" />
          配置
        </Button>
      </div>

      {/* 配置面板 */}
      {showConfig && (
        <Card>
          <CardHeader>
            <CardTitle>配置翻译服务</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
                <label className="text-sm font-medium mb-1 block">选择提供�?/label>
              <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                <SelectTrigger>
                    <SelectValue placeholder="选择提供�? />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google">Google Translate</SelectItem>
                  <SelectItem value="deepl">DeepL</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">API密钥</label>
              <Input
                type="password"
                placeholder="输入API密钥..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">
                {selectedProvider === 'google' 
                  ? '�?Google Cloud Console 获取 API 密钥'
                  : '�?DeepL Developer 获取 API 密钥'}
              </p>
            </div>

            <Button onClick={handleConfigure}>保存配置</Button>
          </CardContent>
        </Card>
      )}

      {/* 提供商信�?*/}
      {providers && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="w-5 h-5 mr-2" />
              已配置的服务
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {providers.providers.map((provider: string) => (
                <Badge 
                  key={provider}
                  variant={provider === providers.default_provider ? 'default' : 'outline'}
                >
                  {provider} {provider === providers.default_provider && '(默认)'}
                </Badge>
              ))}
            </div>
            {providers.providers.length === 0 && (
              <p className="text-sm text-gray-500">尚未配置任何翻译服务</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* 翻译工具 */}
      <Card>
        <CardHeader>
          <CardTitle>在线翻译</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">源语言</label>
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=" auto">自动检�?/SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">中文</SelectItem>
                  <SelectItem value=" ja">日本�?/SelectItem>
                  <SelectItem value=" ko">한국�?/SelectItem>
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
                  <SelectItem value=" ja">日本�?/SelectItem>
                  <SelectItem value=" ko">한국�?/SelectItem>
                  <SelectItem value="ar">العربية</SelectItem>
                  <SelectItem value="he">עברית</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className=" text-sm font-medium mb-1 block">提供�?/label>
              <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                <SelectTrigger>
                  <SelectValue placeholder="选择" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google">Google</SelectItem>
                  <SelectItem value="deepl">DeepL</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">原文</label>
            <Textarea
              placeholder="输入要翻译的文本..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
            />
          </div>

          <div className="flex space-x-2">
            <Button onClick={handleTranslate} disabled={loading}>
              {loading ? '翻译�?..' : '翻译'}
            </Button>
            <Button onClick={handleDetectLanguage} variant="outline" disabled={loading}>
              检测语言
            </Button>
          </div>

          {translatedText && (
            <div>
              <label className="text-sm font-medium mb-1 block">译文</label>
              <div className="bg-gray-50 p-4 rounded-lg border">
                <p className="text-gray-900">{translatedText}</p>
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
            <AlertTitle>专业翻译服务</AlertTitle>
            <AlertDescription>
              集成Google Translate和DeepL等专业翻译API,提供高质量的机器翻译服务�?
              需要自行申请API密钥并按使用量付费�?
            </AlertDescription>
          </Alert>

          <div>
            <h3 className="font-semibold mb-2">支持的提供商:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>
                <strong>Google Translate:</strong> 支持100+语言,准确性高,价格适中
              </li>
              <li>
                <strong>DeepL:</strong> 欧洲语言表现优异,自然度高,价格略高
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-2">使用场景:</h3>
            <ul className="list-disc list-inside space-y-2 text-sm text-gray-700 ml-2">
              <li>网站内容批量翻译</li>
              <li>用户生成内容的实时翻�?/li>
              <li>多语言客服支持</li>
              <li>国际化内容管�?/li>
            </ul>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className=" font-semibold text-blue-900 mb-2">API定价参�?</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>�?Google Translate: $20 / 百万字符</li>
              <li>�?DeepL Pro: �?.49 / �?50万字�?</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
