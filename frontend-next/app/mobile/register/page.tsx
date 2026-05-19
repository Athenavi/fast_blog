"use client"

import React, {useState} from 'react'
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
import {Label} from "@/components/ui/label"
import {useRouter} from "next/navigation"
import {API_ENDPOINTS, getApiUrl} from '@/lib/mobile-api'

export default function MobileRegister() {
    const router = useRouter()
    const [username, setUsername] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        // 验证输入
        if (!username || !email || !password) {
            setError('请填写所有必填字段')
            return
        }

        if (password !== confirmPassword) {
            setError('两次输入的密码不一致')
            return
        }

        if (password.length < 8) {
            setError('密码长度至少为8个字符')
            return
        }

        try {
            setLoading(true)

            const url = getApiUrl(API_ENDPOINTS.REGISTER)
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    email,
                    password
                })
            })

            const data = await response.json()

            if (data.success) {
                // 保存token到localStorage
                localStorage.setItem('access_token', data.data.access_token)
                localStorage.setItem('refresh_token', data.data.refresh_token)
                localStorage.setItem('user', JSON.stringify(data.data.user))

                // 跳转到移动端首页
                router.push('/mobile')
            } else {
                setError(data.error || '注册失败')
            }
        } catch (err) {
            console.error('Register error:', err)
            setError('网络错误，请稍后重试')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container mx-auto p-4 max-w-md min-h-screen flex items-center justify-center">
            <Card className="w-full">
                <CardHeader>
                    <CardTitle className="text-2xl text-center">FastBlog 注册</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleRegister} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="username">用户名</Label>
                            <Input
                                id="username"
                                type="text"
                                placeholder="输入用户名（至少3个字符）"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="email">邮箱</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="输入邮箱地址"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password">密码</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="输入密码（至少8个字符）"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirmPassword">确认密码</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                placeholder="再次输入密码"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? '注册中...' : '注册'}
                        </Button>

                        <div className="text-center text-sm text-gray-600">
                            已有账号？{' '}
                            <button
                                type="button"
                                onClick={() => router.push('/mobile/login')}
                                className="text-blue-600 hover:underline"
                                disabled={loading}
                            >
                                立即登录
                            </button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
