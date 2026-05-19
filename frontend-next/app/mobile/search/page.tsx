"use client"

import React, {Suspense, useEffect, useState} from 'react'
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
import {Skeleton} from "@/components/ui/skeleton"
import {ArrowLeft, Calendar, Eye, Heart, Search} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import {useSearchParams} from "next/navigation"
import {API_ENDPOINTS, getApiUrl} from '@/lib/mobile-api'

interface Article {
    id: number
    title: string
    excerpt: string
    cover_image: string | null
    author: {
        id: number | null
        username: string
        avatar: string | null
    }
    views: number
    likes: number
    created_at: string | null
}

interface Pagination {
    current_page: number
    per_page: number
    total: number
    total_pages: number
}

function MobileSearchContent() {
    const searchParams = useSearchParams()
    const initialKeyword = searchParams.get('q') || ''

    const [articles, setArticles] = useState<Article[]>([])
    const [pagination, setPagination] = useState<Pagination | null>(null)
    const [loading, setLoading] = useState(false)
    const [searchTerm, setSearchTerm] = useState(initialKeyword)
    const [currentPage, setCurrentPage] = useState(1)
    const [hasSearched, setHasSearched] = useState(!!initialKeyword)

    // 执行搜索
    const performSearch = async (keyword: string, page = 1) => {
        if (!keyword.trim()) return

        try {
            setLoading(true)
            const url = getApiUrl(API_ENDPOINTS.ARTICLES_SEARCH) + `?keyword=${encodeURIComponent(keyword)}&page=${page}&per_page=20`
            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setArticles(data.data.articles)
                setPagination(data.data.pagination)
                setHasSearched(true)
            } else {
                console.error('Search failed:', data.error)
            }
        } catch (error) {
            console.error('Error searching articles:', error)
        } finally {
            setLoading(false)
        }
    }

    // 初始搜索（如果有URL参数）
    useEffect(() => {
        if (initialKeyword) {
            performSearch(initialKeyword, 1)
        }
    }, [initialKeyword])

    // 搜索处理
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        setCurrentPage(1)
        performSearch(searchTerm, 1)
    }

    // 分页处理
    const handlePageChange = (newPage: number) => {
        setCurrentPage(newPage)
        performSearch(searchTerm, newPage)
    }

    // 格式化日期
    const formatDate = (dateString: string | null) => {
        if (!dateString) return ''
        return new Date(dateString).toLocaleDateString('zh-CN')
    }

    return (
        <div className="container mx-auto p-4 max-w-4xl">
            {/* 返回按钮 */}
            <div className="mb-4">
                <Link href="/mobile/articles">
                    <Button variant="ghost" size="sm">
                        <ArrowLeft className="h-4 w-4 mr-2"/>
                        返回文章列表
                    </Button>
                </Link>
            </div>

            {/* 搜索栏 */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Search className="h-5 w-5"/>
                        搜索文章
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search
                                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4"/>
                            <Input
                                type="text"
                                placeholder="输入关键词搜索文章..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                        <Button type="submit" disabled={!searchTerm.trim()}>
                            搜索
                        </Button>
                    </form>
                </CardContent>
            </Card>

            {/* 搜索结果 */}
            {!hasSearched ? (
                <Card>
                    <CardContent className="p-8 text-center">
                        <Search className="h-12 w-12 text-gray-400 mx-auto mb-4"/>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">开始搜索</h3>
                        <p className="text-gray-500">
                            在上方输入框中输入关键词，搜索相关文章
                        </p>
                    </CardContent>
                </Card>
            ) : loading ? (
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-4">
                                <Skeleton className="h-6 w-3/4 mb-2"/>
                                <Skeleton className="h-4 w-full mb-2"/>
                                <Skeleton className="h-4 w-2/3"/>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <>
                    {/* 搜索结果统计 */}
                    {pagination && (
                        <div className="mb-4 text-sm text-gray-600">
                            找到 {pagination.total} 篇相关文章
                        </div>
                    )}

                    {/* 文章列表 */}
                    <div className="space-y-4">
                        {articles.map((article) => (
                            <Card key={article.id} className="hover:shadow-md transition-shadow">
                                <Link href={`/mobile/article-detail?id=${article.id}`}>
                                    <CardContent className="p-4">
                                        <div className="flex gap-4">
                                            {/* 封面图 */}
                                            {article.cover_image && (
                                                <div className="flex-shrink-0">
                                                    <Image
                                                        src={article.cover_image}
                                                        alt={article.title}
                                                        width={80}
                                                        height={60}
                                                        className="rounded object-cover"
                                                    />
                                                </div>
                                            )}

                                            {/* 文章内容 */}
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-semibold text-lg mb-2 line-clamp-2">
                                                    {article.title}
                                                </h3>

                                                <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                                                    {article.excerpt}
                                                </p>

                                                {/* 元信息 */}
                                                <div
                                                    className="flex items-center justify-between text-xs text-gray-500">
                                                    <div className="flex items-center gap-4">
                                                        <span>{article.author.username}</span>
                                                        <span className="flex items-center gap-1">
                              <Eye className="h-3 w-3"/>
                                                            {article.views}
                            </span>
                                                        <span className="flex items-center gap-1">
                              <Heart className="h-3 w-3"/>
                                                            {article.likes}
                            </span>
                                                    </div>
                                                    <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3"/>
                                                        {formatDate(article.created_at)}
                          </span>
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Link>
                            </Card>
                        ))}
                    </div>

                    {/* 分页 */}
                    {pagination && pagination.total_pages > 1 && (
                        <div className="flex justify-center items-center gap-2 mt-6">
                            <Button
                                variant="outline"
                                onClick={() => handlePageChange(currentPage - 1)}
                                disabled={currentPage <= 1}
                            >
                                上一页
                            </Button>

                            <span className="text-sm text-gray-600">
                第 {currentPage} / {pagination.total_pages} 页
              </span>

                            <Button
                                variant="outline"
                                onClick={() => handlePageChange(currentPage + 1)}
                                disabled={currentPage >= pagination.total_pages}
                            >
                                下一页
                            </Button>
                        </div>
                    )}

                    {/* 无结果 */}
                    {articles.length === 0 && (
                        <Card>
                            <CardContent className="p-8 text-center">
                                <Search className="h-12 w-12 text-gray-400 mx-auto mb-4"/>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">未找到相关文章</h3>
                                <p className="text-gray-500">
                                    尝试使用其他关键词进行搜索
                                </p>
                            </CardContent>
                        </Card>
                    )}
                </>
            )}
        </div>
    )
}

// 使用 Suspense 包装主组件
export default function MobileSearch() {
    return (
        <Suspense fallback={
            <div className="container mx-auto p-4 max-w-4xl">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-32"/>
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-10 w-full"/>
                    </CardContent>
                </Card>
                <div className="space-y-4 mt-4">
                    {[...Array(3)].map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-4">
                                <Skeleton className="h-6 w-3/4 mb-2"/>
                                <Skeleton className="h-4 w-full mb-2"/>
                                <Skeleton className="h-4 w-2/3"/>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        }>
            <MobileSearchContent/>
        </Suspense>
    )
}