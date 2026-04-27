'use client';

import React, {useState} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {AlertCircle, Lock} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface PasswordProtectedArticleProps {
    articleId: number;
    onPasswordVerified: () => void;
}

/**
 * 密码保护文章组件
 * 
 * @param articleId - 文章ID
 * @param onPasswordVerified - 密码验证成功回调
 */
const PasswordProtectedArticle: React.FC<PasswordProtectedArticleProps> = ({
                                                                               articleId,
                                                                               onPasswordVerified
                                                                           }) => {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!password.trim()) {
            setError('请输入密码');
            return;
        }

        try {
            setLoading(true);
            setError('');

            const response = await apiClient.post(
                `/articles/${articleId}/verify`,
                {password}
            );

            if (response.success) {
                // 验证成功，保存access_token到cookie
                const responseData = response.data as any;
                if (responseData?.access_token) {
                    // 设置cookie，有效期24小时
                    document.cookie = `article_access_${articleId}=${responseData.access_token}; path=/; max-age=86400; SameSite=Lax`;
                }
                // 触发回调
                onPasswordVerified();
            } else {
                setError(response.error || '密码错误');
            }
        } catch (err) {
            console.error('Password verification failed:', err);
            setError('验证失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-[60vh] flex items-center justify-center px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="mx-auto w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mb-4">
                        <Lock className="w-8 h-8 text-blue-600 dark:text-blue-400"/>
                    </div>
                    <CardTitle className="text-2xl">此文章受密码保护</CardTitle>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        请输入密码以查看文章内容
                    </p>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="password">密码</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="请输入访问密码"
                                disabled={loading}
                                autoFocus
                            />
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
                                <AlertCircle className="w-4 h-4"/>
                                <span>{error}</span>
                            </div>
                        )}

                        <Button
                            type="submit"
                            className="w-full"
                            disabled={loading}
                        >
                            {loading ? '验证中...' : '验证密码'}
                        </Button>
                    </form>

                    <div className="mt-6 text-center text-xs text-gray-500 dark:text-gray-400">
                        <p>忘记密码?请联系网站管理员</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default PasswordProtectedArticle;
