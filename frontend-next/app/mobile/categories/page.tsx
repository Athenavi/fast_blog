"use client"

import React, {Suspense, useEffect, useState} from 'react'
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Badge} from "@/components/ui/badge"
import {Skeleton} from "@/components/ui/skeleton"
import {ArrowLeft, Calendar, Eye, Folder, Heart} from "lucide-react"
import Link from "next/link"
import {useRouter, useSearchParams} from "next/navigation"
import {API_ENDPOINTS, getApiUrl} from '@/lib/mobile-api'

interface Category {
    id: number
    name: string
    description: string | null
    slug: string
    parent_id: number | null
}

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

function MobileCategoryDetailContent() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const categoryId = searchParams.get('id')

    const [categories, setCategories] = useState<Category[]>([])
    const [articles, setArticles] = useState<Article[]>([])
    const [selectedCategory, setSelectedCategory] = useState<number | null>(null)
    const [loading, setLoading] = useState(true)
    const [categoryLoading, setCategoryLoading] = useState(true)

    // 获取分类列表
    const fetchCategories = async () => {
        try {
            setCategoryLoading(true)
            const url = getApiUrl(API_ENDPOINTS.CATEGORIES_LIST)
            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setCategories(data.data.categories)

                // 如果 URL 中有分类 ID，选中该分类
                if (categoryId) {
                    const catId = parseInt(categoryId)
                    setSelectedCategory(catId)
                    fetchArticlesByCategory(catId)
                }
            }
        } catch (error) {
            console.error('Error fetching categories:', error)
        } finally {
            setCategoryLoading(false)
        }
    }

    // 根据分类获取文章
    const fetchArticlesByCategory = async (catId: number) => {
        try {
            setLoading(true)
            const url = getApiUrl(API_ENDPOINTS.ARTICLES_LIST) + `?category_id=${catId}&per_page=20`
            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setArticles(data.data.articles)
            }
        } catch (error) {
            console.error('Error fetching articles by category:', error)
        } finally {
            setLoading(false)
        }
    }

    // 初始加载
    useEffect(() => {
        fetchCategories()
    }, [categoryId])

    // 处理分类选择
    const handleCategorySelect = (catId: number) => {
        setSelectedCategory(catId)
        fetchArticlesByCategory(catId)
        // 更新URL
        router.push(`/mobile/categories?id=${catId}`)
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
                <Button variant="ghost" size="sm" onClick={() => router.push('/mobile/articles')}>
                    <ArrowLeft className="h-4 w-4 mr-2"/>
                    返回文章列表
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* 分类列表 */}
                <div className="md:col-span-1">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Folder className="h-5 w-5"/>
                                分类目录
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {categoryLoading ? (
                                <div className="p-4 space-y-2">
                                    {[...Array(5)].map((_, i) => (
                                        <Skeleton key={i} className="h-10 w-full"/>
                                    ))}
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    {categories.map((category) => (
                                        <button
                                            key={category.id}
                                            onClick={() => handleCategorySelect(category.id)}
                                            className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                                                selectedCategory === category.id
                                                    ? 'bg-blue-50 text-blue-600 border-r-2 border-blue-600'
                                                    : ''
                                            }`}
                                        >
                                            <div className="font-medium">{category.name}</div>
                                            {category.description && (
                                                <div className="text-sm text-gray-500 mt-1 line-clamp-1">
                                                    {category.description}
                                                </div>
                                            )}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* 文章列表 */}
                <div className="md:col-span-2">
                    <Card>
                        <CardHeader>
                            <CardTitle>
                                {selectedCategory
                                    ? categories.find(c => c.id === selectedCategory)?.name || '文章列表'
                                    : '请选择分类'
                                }
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <div className="space-y-4">
                                    {[...Array(3)].map((_, i) => (
                                        <div key={i} className="border-b pb-4 last:border-b-0">
                                            <Skeleton className="h-5 w-3/4 mb-2"/>
                                            <Skeleton className="h-4 w-full mb-2"/>
                                            <Skeleton className="h-4 w-1/2"/>
                                        </div>
                                    ))}
                                </div>
                            ) : !selectedCategory ? (
                                <div className="text-center py-8 text-gray-500">
                                    <Folder className="h-12 w-12 mx-auto mb-4 text-gray-300"/>
                                    <p>请从左侧选择一个分类查看文章</p>
                                </div>
                            ) : articles.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    <p>该分类下暂无文章</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {articles.map((article) => (
                                        <div key={article.id} className="border-b pb-4 last:border-b-0">
                                            <Link href={`/mobile/article-detail?id=${article.id}`}>
                                                <div className="hover:bg-gray-50 p-2 -mx-2 rounded transition-colors">
                                                    <h3 className="font-semibold mb-2 line-clamp-2">
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

                                                    {/* 标签 */}
                                                    {article.tags && article.tags.length > 0 && (
                                                        <div className="flex gap-1 mt-2 flex-wrap">
                                                            {article.tags.slice(0, 3).map((tag, index) => (
                                                                <Badge key={index} variant="outline"
                                                                       className="text-xs">
                                                                    {tag}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </Link>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}

// 使用 Suspense 包装主组件
export default function MobileCategoryDetailPage() {
    return (
        <Suspense fallback={
            <div className="container mx-auto p-4 max-w-4xl">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-1">
                        <Card>
                            <CardHeader>
                                <Skeleton className="h-6 w-32"/>
                            </CardHeader>
                            <CardContent>
                                {[...Array(5)].map((_, i) => (
                                    <Skeleton key={i} className="h-10 w-full mb-2"/>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                    <div className="md:col-span-2">
                        <Card>
                            <CardHeader>
                                <Skeleton className="h-6 w-48"/>
                            </CardHeader>
                            <CardContent>
                                {[...Array(3)].map((_, i) => (
                                    <Skeleton key={i} className="h-20 w-full mb-4"/>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        }>
            <MobileCategoryDetailContent/>
        </Suspense>
    )
}
