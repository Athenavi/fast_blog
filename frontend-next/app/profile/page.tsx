'use client';

import React, {useCallback, useEffect, useState} from 'react';
import {useRouter} from 'next/navigation';
import Image from 'next/image';
import {motion} from 'framer-motion';
import {
    Calendar,
    Edit3,
    Eye,
    FileText,
    Heart,
    Link as LinkIcon,
    Lock,
    Mail,
    MapPin,
    Settings,
    UserPlus,
    Users
} from 'lucide-react';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient, UserProfileResponse} from '@/lib/api';
import {getConfig} from '@/lib/config';

// 动画配置
const fadeInUp = {
    initial: {opacity: 0, y: 20},
    animate: {opacity: 1, y: 0},
    transition: {duration: 0.5}
};

const staggerContainer = {
    animate: {
        transition: {
            staggerChildren: 0.1
        }
    }
};

const ProfilePage = () => {
    const router = useRouter();
    const [userData, setUserData] = useState<UserProfileResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [avatarUrl, setAvatarUrl] = useState<string>('');
    const [activeTab, setActiveTab] = useState<'articles' | 'about'>('articles');

    // 获取头像URL（使用 useCallback 确保稳定引用）
    const fetchAvatarUrl = useCallback(async (userId: number, username: string, avatar?: string) => {
        let avatarUrl = avatar;

        console.log('[fetchAvatarUrl] 初始 avatar:', avatar);

        // 如果后端没有返回头像，则通过 API 获取
        if (!avatarUrl && userId) {
            try {
                const apiConfig = getConfig();
                const avatarResponse = await fetch(
                    `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/user/avatar?user_id=${userId}`,
                    {credentials: 'include'}
                );
                if (avatarResponse.ok) {
                    const text = await avatarResponse.text();
                    // 后端返回的是纯文本 URL，需要去除可能的引号
                    avatarUrl = text.replace(/^"|"$/g, '').trim();
                    console.log('[fetchAvatarUrl] 从 API 获取的 avatarUrl:', avatarUrl);
                }
            } catch (error) {
                console.error('获取头像 URL 失败:', error);
            }
        }

        // 如果 avatarUrl 是相对路径（以 / 开头但不包含 http），拼接完整路径
        if (avatarUrl && !avatarUrl.startsWith('http')) {
            const apiConfig = getConfig();
            console.log('[fetchAvatarUrl] 处理相对路径:', avatarUrl);
            // 如果已经是完整路径（如 /static/avatar/xxx.png），直接拼接 API_BASE_URL
            if (avatarUrl.startsWith('/')) {
                avatarUrl = `${apiConfig.API_BASE_URL}${avatarUrl}`;
            } else {
                // 如果是 UUID 或其他格式，尝试拼接 static/avatar 路径并添加 .png 扩展名
                // 先尝试 .png，如果失败会在 onError 中处理
                avatarUrl = `${apiConfig.API_BASE_URL}/static/avatar/${avatarUrl}.png`;
            }
            console.log('[fetchAvatarUrl] 拼接后的 avatarUrl:', avatarUrl);
        }

        // 最终检查：如果 avatarUrl 为空或无效，返回默认头像
        const defaultAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(username || 'User')}&background=random`;

        // 验证 URL 是否有效
        if (avatarUrl && avatarUrl.trim()) {
            try {
                // 尝试构造 URL 对象来验证
                new URL(avatarUrl);
                console.log('[fetchAvatarUrl] 最终返回的 avatarUrl:', avatarUrl);
                return avatarUrl;
            } catch (e) {
                console.warn('无效的头像 URL，使用默认头像:', avatarUrl);
                return defaultAvatar;
            }
        }

        console.log('[fetchAvatarUrl] avatarUrl 为空，使用默认头像');
        return defaultAvatar;
    }, []);

    useEffect(() => {
        let isCancelled = false; // 防止组件卸载后更新状态
        
        async function fetchUserProfile() {
            try {
                setLoading(true);
                const response = await apiClient.get<UserProfileResponse>('/users/me');

                if (!response.success || !response.data) {
                    if (response.requires_auth || response.error?.includes('401')) {
                        router.push('/login');
                    }
                    return;
                }

                if (isCancelled) return;

                const data = response.data;
                const userData = (data as any).user ? data : {user: data};
                setUserData(userData as UserProfileResponse);

                const user = (userData as UserProfileResponse).user;
                // 确保传递完整的头像 URL
                const userAvatar = (user as any).avatar_url || (user as any).avatar || (user as any).profile_picture;
                const avatar = await fetchAvatarUrl(user.id, user.username, userAvatar);

                if (!isCancelled) {
                    setAvatarUrl(avatar);
                }
            } catch (error) {
                console.error('加载用户资料失败:', error);
            } finally {
                if (!isCancelled) {
                    setLoading(false);
                }
            }
        }

        fetchUserProfile();

        return () => {
            isCancelled = true;
        };
    }, [router, fetchAvatarUrl]);

    if (loading || !userData) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
                <motion.div
                    animate={{rotate: 360}}
                    transition={{duration: 1, repeat: Infinity, ease: "linear"}}
                    className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"
                />
            </div>
        );
    }

    const user = userData.user;
    const recentArticles = userData.recent_articles || [];
    const stats = userData.stats || {articles_count: 0, followers_count: 0, following_count: 0};

    return (
        <WithAuthProtection loadingMessage="正在加载用户资料...">
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
                {/* 封面区域 */}
                <div
                    className="relative h-64 bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600 overflow-hidden">
                    {/* 装饰性图案 */}
                    <div className="absolute inset-0 opacity-20">
                        <div
                            className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2"/>
                        <div
                            className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl translate-x-1/2 translate-y-1/2"/>
                    </div>

                    {/* 网格背景 */}
                    <div
                        className="absolute inset-0 opacity-10"
                        style={{
                            backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
                            backgroundSize: '40px 40px'
                        }}
                    />
                </div>

                {/* 主要内容区 */}
                <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 -mt-32 relative z-10">
                    {/* 用户信息卡片 */}
                    <motion.div
                        variants={fadeInUp}
                        initial="initial"
                        animate="animate"
                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 p-8 mb-8"
                    >
                        <div className="flex flex-col lg:flex-row gap-8">
                            {/* 头像 */}
                            <div className="flex-shrink-0">
                                <div className="relative">
                                    <div
                                        className="w-32 h-32 rounded-2xl overflow-hidden border-4 border-white dark:border-gray-900 shadow-lg">
                                        <Image
                                            src={avatarUrl || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.username || 'User')}&background=random`}
                                            alt={user.username || 'User'}
                                            width={128}
                                            height={128}
                                            className="w-full h-full object-cover"
                                            onError={(e) => {
                                                const currentSrc = e.currentTarget.src;
                                                // 如果当前是 .png 失败，尝试 .webp
                                                if (currentSrc.endsWith('.png')) {
                                                    e.currentTarget.src = currentSrc.replace('.png', '.webp');
                                                }
                                                // 如果当前是 .webp 失败，尝试 .jpg
                                                else if (currentSrc.endsWith('.webp')) {
                                                    e.currentTarget.src = currentSrc.replace('.webp', '.jpg');
                                                }
                                                // 如果都失败，使用默认头像
                                                else {
                                                    e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.username || 'User')}&background=random`;
                                                }
                                            }}
                                        />
                                    </div>
                                    {/* 在线状态指示器 */}
                                    <div
                                        className="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 border-4 border-white dark:border-gray-900 rounded-full"/>
                                </div>
                            </div>

                            {/* 用户信息 */}
                            <div className="flex-1">
                                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                                    <div>
                                        <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-2">
                                            {user.display_name || user.username}
                                        </h1>
                                        <p className="text-lg text-gray-500 dark:text-gray-400 mb-4">
                                            @{user.username}
                                        </p>

                                        {user.bio && (
                                            <p className="text-gray-700 dark:text-gray-300 mb-4 max-w-2xl">
                                                {user.bio}
                                            </p>
                                        )}

                                        {/* 元信息 */}
                                        <div
                                            className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                                            {user.location && (
                                                <div className="flex items-center gap-1.5">
                                                    <MapPin className="w-4 h-4"/>
                                                    <span>{user.location}</span>
                                                </div>
                                            )}
                                            {user.website && (
                                                <div className="flex items-center gap-1.5">
                                                    <LinkIcon className="w-4 h-4"/>
                                                    <a href={user.website} target="_blank" rel="noopener noreferrer"
                                                       className="text-blue-600 dark:text-blue-400 hover:underline">
                                                        {user.website.replace(/^https?:\/\//, '')}
                                                    </a>
                                                </div>
                                            )}
                                            <div className="flex items-center gap-1.5">
                                                <Calendar className="w-4 h-4"/>
                                                <span>加入于 {user.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN', {
                                                    year: 'numeric',
                                                    month: 'long'
                                                }) : ''}</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* 操作按钮 */}
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => router.push('/settings')}
                                            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-xl transition-colors"
                                        >
                                            <Settings className="w-4 h-4"/>
                                            <span className="hidden sm:inline">编辑资料</span>
                                        </button>
                                        <button
                                            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors">
                                            <UserPlus className="w-4 h-4"/>
                                            <span className="hidden sm:inline">关注</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 统计数据 */}
                        <div
                            className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-8 border-t border-gray-200 dark:border-gray-800">
                            <div className="text-center">
                                <div className="text-3xl font-black text-gray-900 dark:text-white">
                                    {stats.articles_count}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">文章</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-black text-gray-900 dark:text-white">
                                    {stats.followers_count}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">粉丝</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-black text-gray-900 dark:text-white">
                                    {stats.following_count}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">关注</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-black text-gray-900 dark:text-white">
                                    {recentArticles.reduce((sum, article) => sum + (article.views || 0), 0)}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">总浏览</div>
                            </div>
                        </div>
                    </motion.div>

                    {/* 标签页导航 */}
                    <div
                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 mb-8">
                        <div className="flex border-b border-gray-200 dark:border-gray-800">
                            <button
                                onClick={() => setActiveTab('articles')}
                                className={`flex-1 px-6 py-4 font-medium transition-colors ${
                                    activeTab === 'articles'
                                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                }`}
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <FileText className="w-5 h-5"/>
                                    <span>文章</span>
                                    <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded-full text-xs">
                                        {recentArticles.length}
                                    </span>
                                </div>
                            </button>
                            <button
                                onClick={() => setActiveTab('about')}
                                className={`flex-1 px-6 py-4 font-medium transition-colors ${
                                    activeTab === 'about'
                                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                }`}
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <Users className="w-5 h-5"/>
                                    <span>关于</span>
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* 文章内容 */}
                    {activeTab === 'articles' && (
                        <motion.div
                            variants={staggerContainer}
                            initial="initial"
                            animate="animate"
                            className="space-y-4"
                        >
                            {recentArticles.length > 0 ? (
                                recentArticles.map((article, index) => (
                                    <motion.article
                                        key={article.id}
                                        variants={fadeInUp}
                                        className="group bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-all hover:shadow-lg cursor-pointer"
                                        onClick={() => router.push(`/blog/detail?slug=${article.slug}`)}
                                    >
                                        <div className="p-6">
                                            <div className="flex gap-6">
                                                {/* 封面图 */}
                                                {article.cover_image && (
                                                    <div
                                                        className="hidden sm:block relative w-40 h-28 flex-shrink-0 rounded-xl overflow-hidden">
                                                        <Image
                                                            src={article.cover_image}
                                                            alt={article.title}
                                                            fill
                                                            className="object-cover group-hover:scale-105 transition-transform duration-500"
                                                            sizes="160px"
                                                        />
                                                    </div>
                                                )}

                                                {/* 内容 */}
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                        {article.title}
                                                    </h3>

                                                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                                                        {article.excerpt || article.summary || '暂无摘要'}
                                                    </p>

                                                    {/* 元数据 */}
                                                    <div
                                                        className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                                                        <span className="flex items-center gap-1.5">
                                                            <Calendar className="w-4 h-4"/>
                                                            {article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}
                                                        </span>
                                                        <span className="flex items-center gap-1.5">
                                                            <Eye className="w-4 h-4"/>
                                                            {article.views || 0}
                                                        </span>
                                                        <span className="flex items-center gap-1.5">
                                                            <Heart className="w-4 h-4"/>
                                                            {article.likes || 0}
                                                        </span>
                                                    </div>

                                                    {/* 标签 */}
                                                    {article.tags && article.tags.length > 0 && (
                                                        <div className="flex flex-wrap gap-2 mt-4">
                                                            {article.tags.slice(0, 3).map((tag, tagIndex) => (
                                                                <span
                                                                    key={tagIndex}
                                                                    className="px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs font-medium rounded-full"
                                                                >
                                                                    #{tag}
                                                                </span>
                                                            ))}
                                                            {article.tags.length > 3 && (
                                                                <span
                                                                    className="text-xs text-gray-400">+{article.tags.length - 3}</span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </motion.article>
                                ))
                            ) : (
                                <motion.div
                                    variants={fadeInUp}
                                    className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-12 text-center"
                                >
                                    <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/>
                                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">暂无文章</h3>
                                    <p className="text-gray-600 dark:text-gray-400 mb-6">开始创作你的第一篇文章吧</p>
                                    <button
                                        onClick={() => router.push('/my/posts/create')}
                                        className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
                                    >
                                        <Edit3 className="w-5 h-5"/>
                                        创建文章
                                    </button>
                                </motion.div>
                            )}
                        </motion.div>
                    )}

                    {/* 关于内容 */}
                    {activeTab === 'about' && (
                        <motion.div
                            variants={fadeInUp}
                            initial="initial"
                            animate="animate"
                            className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8"
                        >
                            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">个人信息</h2>

                            <div className="space-y-6">
                                <div className="flex items-start gap-4">
                                    <div
                                        className="w-10 h-10 bg-blue-50 dark:bg-blue-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                                        <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">邮箱</div>
                                        <div className="text-gray-900 dark:text-white">{user.email}</div>
                                    </div>
                                </div>

                                <div className="flex items-start gap-4">
                                    <div
                                        className="w-10 h-10 bg-purple-50 dark:bg-purple-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                                        <MapPin className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">位置</div>
                                        <div className="text-gray-900 dark:text-white">{user.location || '未设置'}</div>
                                    </div>
                                </div>

                                <div className="flex items-start gap-4">
                                    <div
                                        className="w-10 h-10 bg-green-50 dark:bg-green-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                                        <LinkIcon className="w-5 h-5 text-green-600 dark:text-green-400"/>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">网站</div>
                                        {user.website ? (
                                            <a href={user.website} target="_blank" rel="noopener noreferrer"
                                               className="text-blue-600 dark:text-blue-400 hover:underline">
                                                {user.website}
                                            </a>
                                        ) : (
                                            <div className="text-gray-900 dark:text-white">未设置</div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-start gap-4">
                                    <div
                                        className="w-10 h-10 bg-orange-50 dark:bg-orange-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                                        <Lock className="w-5 h-5 text-orange-600 dark:text-orange-400"/>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">隐私设置</div>
                                        <div className="text-gray-900 dark:text-white">
                                            {user.profile_private ? '私密账户' : '公开账户'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </div>

                {/* 底部间距 */}
                <div className="h-20"/>
            </div>
        </WithAuthProtection>
    );
};

export default ProfilePage;
