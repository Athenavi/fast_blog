"use client"

import React, {useEffect, useState} from 'react'
import {Card, CardContent, CardHeader} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
import {Badge} from "@/components/ui/badge"
import {Skeleton} from "@/components/ui/skeleton"
import {BookOpen, Calendar, Eye, Heart, Search} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
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
    category: {
        id: number | null
        name: string | null
    }
    views: number
    likes: number
    created_at: string | null
    tags: string[]
}

interface Pagination {
    current_page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
}

export default function MobileArticlesList() {
    const [articles, setArticles] = useState<Article[]>([])
    const [pagination, setPagination] = useState<Pagination | null>(null)
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedCategory, setSelectedCategory] = useState<number | null>(null)
    const [currentPage, setCurrentPage] = useState(1)

    // 获取文章列表
    const fetchArticles = async (page = 1, search = '', categoryId: number | null = null) => {
        try {
            setLoading(true)
            let url = getApiUrl(API_ENDPOINTS.ARTICLES_LIST) + `?page=${page}&per_page=20`

            if (search) {
                url += `&search=${encodeURIComponent(search)}`
            }

            if (categoryId) {
                url += `&category_id=${categoryId}`
            }

            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setArticles(data.data.articles)
                setPagination(data.data.pagination)
            } else {
                console.error('Failed to fetch articles:', data.error)
            }
        } catch (error) {
            console.error('Error fetching articles:', error)
        } finally {
            setLoading(false)
        }
    }

    // 初始加载
    useEffect(() => {
        fetchArticles(currentPage, searchTerm, selectedCategory)
    }, [currentPage, searchTerm, selectedCategory])

    // 搜索处理
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        setCurrentPage(1)
        fetchArticles(1, searchTerm, selectedCategory)
    }

    // 分页处理
    const handlePageChange = (newPage: number) => {
        setCurrentPage(newPage)
    }

    // 格式化日期
    const formatDate = (dateString: string | null) => {
        if (!dateString) return ''
        return new Date(dateString).toLocaleDateString('zh-CN')
    }

    if (loading && articles.length === 0) {
        return (
            <div className="container mx-auto p-4 max-w-4xl">
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <Card key={i}>
                            <CardHeader>
                                <Skeleton className="h-6 w-3/4"/>
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-4 w-full mb-2"/>
                                <Skeleton className="h-4 w-2/3"/>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className="container mx-auto p-4 max-w-4xl">
            {/* 搜索栏 */}
            <Card className="mb-6">
                <CardContent className="p-4">
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search
                                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4"/>
                            <Input
                                type="text"
                                placeholder="搜索文章..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                        <Button type="submit">搜索</Button>
                    </form>
                </CardContent>
            </Card>

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
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                            <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                          <BookOpen className="h-3 w-3"/>
                            {article.author.username}
                        </span>
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

                                        {/* 标签 */}
                                        {article.tags && article.tags.length > 0 && (
                                            <div className="flex gap-1 mt-2 flex-wrap">
                                                {article.tags.slice(0, 3).map((tag, index) => (
                                                    <Badge key={index} variant="secondary" className="text-xs">
                                                        {tag}
                                                    </Badge>
                                                ))}
                                            </div>
                                        )}
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
                        disabled={!pagination.has_prev}
                    >
                        上一页
                    </Button>

                    <span className="text-sm text-gray-600">
            第 {currentPage} / {pagination.total_pages} 页
          </span>

                    <Button
                        variant="outline"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={!pagination.has_next}
                    >
                        下一页
                    </Button>
                </div>
            )}

            {/* 空状态 */}
            {!loading && articles.length === 0 && (
                <Card>
                    <CardContent className="p-8 text-center">
                        <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4"/>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">暂无文章</h3>
                        <p className="text-gray-500">
                            {searchTerm ? '没有找到匹配的文章' : '还没有发布任何文章'}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}