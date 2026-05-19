"use client"

import React, {useState} from 'react'
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
import {Label} from "@/components/ui/label"
import {useRouter} from "next/navigation"
import {API_ENDPOINTS, getApiUrl} from '@/lib/mobile-api'

export default function MobileLogin() {
    const router = useRouter()
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (!username || !password) {
            setError('请输入用户名和密码')
            return
        }

        try {
            setLoading(true)

            const url = getApiUrl(API_ENDPOINTS.LOGIN)
            console.log('[Mobile Login] Request URL:', url)
            console.log('[Mobile Login] Request body:', {username, password})

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    password
                })
            })

            console.log('[Mobile Login] Response status:', response.status)
            const data = await response.json()
            console.log('[Mobile Login] Response data:', data)

            if (data.success) {
                // 保存token到localStorage
                localStorage.setItem('access_token', data.data.access_token)
                localStorage.setItem('refresh_token', data.data.refresh_token)
                localStorage.setItem('user', JSON.stringify(data.data.user))

                // 跳转到移动端首页
                router.push('/mobile')
            } else {
                setError(data.error || '登录失败')
            }
        } catch (err) {
            console.error('Login error:', err)
            setError('网络错误，请稍后重试')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container mx-auto p-4 max-w-md min-h-screen flex items-center justify-center">
            <Card className="w-full">
                <CardHeader>
                    <CardTitle className="text-2xl text-center">FastBlog 登录</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="username">用户名或邮箱</Label>
                            <Input
                                id="username"
                                type="text"
                                placeholder="输入用户名或邮箱"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password">密码</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="输入密码"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? '登录中...' : '登录'}
                        </Button>

                        <div className="text-center text-sm text-gray-600">
                            还没有账号？{' '}
                            <button
                                type="button"
                                onClick={() => router.push('/mobile/register')}
                                className="text-blue-600 hover:underline"
                                disabled={loading}
                            >
                                立即注册
                            </button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
