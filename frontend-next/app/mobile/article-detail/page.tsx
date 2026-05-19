"use client"

import React, {Suspense, useEffect, useState} from 'react'
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card"
import {Button} from "@/components/ui/button"
import {Badge} from "@/components/ui/badge"
import {Skeleton} from "@/components/ui/skeleton"
import {Textarea} from "@/components/ui/textarea"
import {ArrowLeft, Calendar, Eye, Heart, MessageCircle, Send, Tag, User} from "lucide-react"
import Image from "next/image"
import {useRouter, useSearchParams} from "next/navigation"
import {API_ENDPOINTS, getApiUrl} from '@/lib/mobile-api'

interface ArticleDetail {
    id: number
    title: string
    slug: string
    excerpt: string
    content: string
    cover_image: string | null
    author: {
        id: number | null
        username: string
        avatar: string | null
        bio: string
    }
    category: {
        id: number | null
        name: string | null
    }
    views: number
    likes: number
    created_at: string | null
    updated_at: string | null
    tags: string[]
    is_vip_only: boolean
    required_vip_level: number
}

interface Comment {
    id: number
    content: string
    author: {
        id: number | null
        username: string
        avatar: string | null
    }
    created_at: string | null
    likes: number
    parent_id: number | null
}

function MobileArticleDetailContent() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const articleId = searchParams?.get('id')

    const [article, setArticle] = useState<ArticleDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // 评论相关状态
    const [comments, setComments] = useState<Comment[]>([])
    const [commentContent, setCommentContent] = useState('')
    const [submitting, setSubmitting] = useState(false)

    // 获取文章详情
    const fetchArticleDetail = async () => {
        if (!articleId) {
            setError('缺少文章ID')
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const url = getApiUrl(API_ENDPOINTS.ARTICLES_DETAIL(articleId))
            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setArticle(data.data)
            } else {
                setError(data.error || '获取文章详情失败')
            }
        } catch (error) {
            console.error('Error fetching article detail:', error)
            setError('网络错误，请稍后重试')
        } finally {
            setLoading(false)
        }
    }

    // 初始加载
    useEffect(() => {
        if (articleId) {
            fetchArticleDetail()
            fetchComments()
        }
    }, [articleId])

    // 获取评论列表
    const fetchComments = async () => {
        if (!articleId) return

        try {
            const url = getApiUrl(`/comments/article/${articleId}?page=1&per_page=50`)
            const response = await fetch(url)
            const data = await response.json()

            if (data.success) {
                setComments(data.data.comments || [])
            }
        } catch (error) {
            console.error('Error fetching comments:', error)
        }
    }

    // 提交评论
    const handleSubmitComment = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!commentContent.trim()) {
            alert('请输入评论内容')
            return
        }

        // 检查是否登录
        const token = localStorage.getItem('access_token')
        if (!token) {
            alert('请先登录')
            router.push('/mobile/login')
            return
        }

        try {
            setSubmitting(true)

            const url = getApiUrl(`/comments?article_id=${articleId}&content=${encodeURIComponent(commentContent)}`)
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                }
            })

            const data = await response.json()

            if (data.success) {
                setCommentContent('')
                fetchComments() // 重新加载评论
                alert('评论发表成功')
            } else {
                alert(data.error || '评论失败')
            }
        } catch (error) {
            console.error('Error submitting comment:', error)
            alert('网络错误，请稍后重试')
        } finally {
            setSubmitting(false)
        }
    }

    // 格式化日期
    const formatDate = (dateString: string | null) => {
        if (!dateString) return ''
        return new Date(dateString).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        })
    }

    if (loading) {
        return (
            <div className="container mx-auto p-4 max-w-4xl">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-8 w-3/4 mb-2"/>
                        <Skeleton className="h-4 w-1/2"/>
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-64 w-full mb-4"/>
                        <Skeleton className="h-4 w-full mb-2"/>
                        <Skeleton className="h-4 w-full mb-2"/>
                        <Skeleton className="h-4 w-2/3"/>
                    </CardContent>
                </Card>
            </div>
        )
    }

    if (error || !article) {
        return (
            <div className="container mx-auto p-4 max-w-4xl">
                <Card>
                    <CardContent className="p-8 text-center">
                        <h3 className="text-lg font-medium text-red-600 mb-2">加载失败</h3>
                        <p className="text-gray-500 mb-4">{error || '文章不存在'}</p>
                        <Button variant="outline" onClick={() => router.back()}>
                            <ArrowLeft className="h-4 w-4 mr-2"/>
                            返回
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="container mx-auto p-4 max-w-4xl">
            {/* 返回按钮 */}
            <div className="mb-4">
                <Button variant="ghost" size="sm" onClick={() => router.back()}>
                    <ArrowLeft className="h-4 w-4 mr-2"/>
                    返回文章列表
                </Button>
            </div>

            {/* 文章头部 */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-2xl font-bold">{article.title}</CardTitle>

                    {/* 元信息 */}
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <User className="h-4 w-4"/>
                {article.author.username}
            </span>
                        <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4"/>
                            {formatDate(article.created_at)}
            </span>
                        <span className="flex items-center gap-1">
              <Eye className="h-4 w-4"/>
                            {article.views} 阅读
            </span>
                        <span className="flex items-center gap-1">
              <Heart className="h-4 w-4"/>
                            {article.likes} 点赞
            </span>
                    </div>

                    {/* 分类和标签 */}
                    <div className="flex flex-wrap gap-2 mt-2">
                        {article.category && article.category.name && (
                            <Badge variant="secondary">
                                {article.category.name}
                            </Badge>
                        )}

                        {article.tags.map((tag, index) => (
                            <Badge key={index} variant="outline" className="flex items-center gap-1">
                                <Tag className="h-3 w-3"/>
                                {tag}
                            </Badge>
                        ))}

                        {article.is_vip_only && (
                            <Badge variant="destructive">VIP专属</Badge>
                        )}
                    </div>
                </CardHeader>

                {/* 封面图 */}
                {article.cover_image && (
                    <CardContent className="px-6 pb-6">
                        <Image
                            src={article.cover_image}
                            alt={article.title}
                            width={800}
                            height={400}
                            className="w-full h-64 object-cover rounded-lg"
                        />
                    </CardContent>
                )}
            </Card>

            {/* 文章内容 */}
            <Card className="mb-6">
                <CardContent className="p-6">
                    <div
                        className="prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{__html: article.content}}
                    />
                </CardContent>
            </Card>

            {/* 作者信息 */}
            <Card className="mb-6">
                <CardContent className="p-6">
                    <div className="flex items-center gap-4">
                        {article.author.avatar ? (
                            <Image
                                src={article.author.avatar}
                                alt={article.author.username}
                                width={50}
                                height={50}
                                className="rounded-full"
                            />
                        ) : (
                            <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                                <User className="h-6 w-6 text-gray-500"/>
                            </div>
                        )}

                        <div className="flex-1">
                            <h4 className="font-semibold">{article.author.username}</h4>
                            {article.author.bio && (
                                <p className="text-sm text-gray-600">{article.author.bio}</p>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 评论区 */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <MessageCircle className="h-5 w-5"/>
                        评论 ({comments.length})
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* 发表评论 */}
                    <form onSubmit={handleSubmitComment} className="space-y-3">
                        <Textarea
                            placeholder="写下你的评论..."
                            value={commentContent}
                            onChange={(e) => setCommentContent(e.target.value)}
                            rows={3}
                            disabled={submitting}
                        />
                        <Button type="submit" disabled={submitting || !commentContent.trim()}>
                            <Send className="h-4 w-4 mr-2"/>
                            {submitting ? '发表中...' : '发表评论'}
                        </Button>
                    </form>

                    {/* 评论列表 */}
                    <div className="space-y-4 mt-6">
                        {comments.length === 0 ? (
                            <p className="text-center text-gray-500 py-8">暂无评论，快来抢沙发吧！</p>
                        ) : (
                            comments.map((comment) => (
                                <div key={comment.id} className="border-b pb-4 last:border-0">
                                    <div className="flex gap-3">
                                        {comment.author.avatar ? (
                                            <Image
                                                src={comment.author.avatar}
                                                alt={comment.author.username}
                                                width={40}
                                                height={40}
                                                className="rounded-full flex-shrink-0"
                                            />
                                        ) : (
                                            <div
                                                className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                                                <User className="h-5 w-5 text-gray-500"/>
                                            </div>
                                        )}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="font-medium text-sm">{comment.author.username}</span>
                                                <span className="text-xs text-gray-500">
                          {comment.created_at ? new Date(comment.created_at).toLocaleDateString('zh-CN') : ''}
                        </span>
                                            </div>
                                            <p className="text-sm text-gray-700 break-words">{comment.content}</p>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* 操作按钮 */}
            <div className="flex gap-2">
                <Button className="flex-1">
                    <Heart className="h-4 w-4 mr-2"/>
                    点赞 ({article.likes})
                </Button>

                <Button variant="outline" className="flex-1">
                    分享
                </Button>
            </div>
        </div>
    )
}

// 使用 Suspense 包装主组件
export default function MobileArticleDetail() {
    return (
        <Suspense fallback={
            <div className="container mx-auto p-4 max-w-4xl">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-8 w-3/4 mb-2"/>
                        <Skeleton className="h-4 w-1/2"/>
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-64 w-full mb-4"/>
                        <Skeleton className="h-4 w-full mb-2"/>
                        <Skeleton className="h-4 w-full mb-2"/>
                        <Skeleton className="h-4 w-2/3"/>
                    </CardContent>
                </Card>
            </div>
        }>
            <MobileArticleDetailContent/>
        </Suspense>
    )
}
