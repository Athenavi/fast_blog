"use client"

import React, {useEffect, useState} from 'react'
import {Card, CardContent} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {useRouter} from "next/navigation"
import {BookOpen, LogIn, LogOut, User, UserPlus} from "lucide-react"

export default function MobileHome() {
    const router = useRouter()
    const [isLoggedIn, setIsLoggedIn] = useState(false)
    const [userInfo, setUserInfo] = useState<any>(null)

    // 检查登录状态
    useEffect(() => {
        const token = localStorage.getItem('access_token')
        const userStr = localStorage.getItem('user')

        if (token && userStr) {
            setIsLoggedIn(true)
            try {
                setUserInfo(JSON.parse(userStr))
            } catch (e) {
                console.error('Failed to parse user info:', e)
            }
        }
    }, [])

    // 登出功能
    const handleLogout = () => {
        // 清除 localStorage
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')

        // 清除所有 cookie
        document.cookie.split(';').forEach((c) => {
            const name = c.trim().split('=')[0]
            document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
        })

        setIsLoggedIn(false)
        setUserInfo(null)
        alert('已退出登录')
    }

    return (
        <div className="container mx-auto p-4 max-w-md min-h-screen flex flex-col items-center justify-center">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold mb-2">FastBlog</h1>
                <p className="text-gray-600">移动端应用</p>
            </div>

            <div className="space-y-4 w-full">
                <Card>
                    <CardContent className="p-6">
                        {/* 已登录状态 */}
                        {isLoggedIn ? (
                            <div className="space-y-4">
                                {/* 用户信息 */}
                                <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
                                    <div
                                        className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                                        <User className="h-6 w-6 text-white"/>
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-semibold">{userInfo?.username || '用户'}</p>
                                        <p className="text-sm text-gray-600">{userInfo?.email || ''}</p>
                                    </div>
                                </div>

                                {/* 功能按钮 */}
                                <Button
                                    onClick={() => router.push('/mobile/articles')}
                                    className="w-full"
                                    size="lg"
                                >
                                    <BookOpen className="mr-2 h-5 w-5"/>
                                    浏览文章
                                </Button>

                                <Button
                                    onClick={handleLogout}
                                    variant="destructive"
                                    className="w-full"
                                    size="lg"
                                >
                                    <LogOut className="mr-2 h-5 w-5"/>
                                    退出登录
                                </Button>
                            </div>
                        ) : (
                            /* 未登录状态 */
                            <div className="space-y-4">
                                <Button
                                    onClick={() => router.push('/mobile/login')}
                                    className="w-full"
                                    size="lg"
                                >
                                    <LogIn className="mr-2 h-5 w-5"/>
                                    登录
                                </Button>

                                <Button
                                    onClick={() => router.push('/mobile/register')}
                                    variant="outline"
                                    className="w-full"
                                    size="lg"
                                >
                                    <UserPlus className="mr-2 h-5 w-5"/>
                                    注册
                                </Button>

                                <Button
                                    onClick={() => router.push('/mobile/articles')}
                                    variant="secondary"
                                    className="w-full"
                                    size="lg"
                                >
                                    <BookOpen className="mr-2 h-5 w-5"/>
                                    浏览文章
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <div className="text-center text-sm text-gray-500 mt-8">
                    <p>FastBlog Mobile App v1.0</p>
                </div>
            </div>
        </div>
    )
}
