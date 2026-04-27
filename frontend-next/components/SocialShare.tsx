'use client';

import React, {useState} from 'react';
import {Check, Copy, Facebook, Linkedin, Mail, MessageCircle, Share2, Twitter} from 'lucide-react';

interface SocialShareProps {
    url: string;
    title: string;
    description?: string;
    image?: string;
    platforms?: SocialPlatform[];
    size?: 'sm' | 'md' | 'lg';
    layout?: 'horizontal' | 'vertical' | 'dropdown';
}

type SocialPlatform = 'facebook' | 'twitter' | 'linkedin' | 'wechat' | 'weibo' | 'email' | 'copy';

interface PlatformConfig {
    name: string;
    icon: React.ElementType;
    color: string;
    shareUrl: (url: string, title: string, description?: string) => string;
}

const platformConfigs: Record<SocialPlatform, PlatformConfig> = {
    facebook: {
        name: 'Facebook',
        icon: Facebook,
        color: '#1877F2',
        shareUrl: (url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
    },
    twitter: {
        name: 'Twitter',
        icon: Twitter,
        color: '#1DA1F2',
        shareUrl: (url, title) => `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
    },
    linkedin: {
        name: 'LinkedIn',
        icon: Linkedin,
        color: '#0A66C2',
        shareUrl: (url, title, description) => 
            `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}&summary=${encodeURIComponent(description || '')}`,
    },
    wechat: {
        name: '微信',
        icon: MessageCircle,
        color: '#07C160',
        shareUrl: () => '', // 需要特殊处理
    },
    weibo: {
        name: '微博',
        icon: Share2,
        color: '#E6162D',
        shareUrl: (url, title, description) => 
            `http://service.weibo.com/share/share.php?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title + ' - ' + (description || ''))}`,
    },
    email: {
        name: '邮件',
        icon: Mail,
        color: '#EA4335',
        shareUrl: (url, title, description) => 
            `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(description + '\n\n' + url)}`,
    },
    copy: {
        name: '复制链接',
        icon: Copy,
        color: '#6B7280',
        shareUrl: () => '', // 特殊处理
    },
};

const SocialShare: React.FC<SocialShareProps> = ({
    url,
    title,
    description = '',
    image,
    platforms = ['facebook', 'twitter', 'linkedin', 'wechat', 'weibo', 'email', 'copy'],
    size = 'md',
    layout = 'horizontal',
}) => {
    const [copied, setCopied] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);

    // 尺寸配置
    const sizeConfig = {
        sm: { button: 'w-8 h-8', icon: 16, text: 'text-xs' },
        md: { button: 'w-10 h-10', icon: 20, text: 'text-sm' },
        lg: { button: 'w-12 h-12', icon: 24, text: 'text-base' },
    };

    const currentSize = sizeConfig[size];

    // 复制链接
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error('复制失败:', error);
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // 分享处理
    const handleShare = (platform: SocialPlatform) => {
        const config = platformConfigs[platform];
        
        if (platform === 'copy') {
            handleCopy();
            return;
        }

        if (platform === 'wechat') {
            // 微信分享需要特殊处理（生成二维码）
            alert('请使用微信扫一扫分享');
            return;
        }

        const shareUrl = config.shareUrl(url, title, description);
        if (shareUrl) {
            window.open(shareUrl, '_blank', 'width=600,height=400');
        }

        setShowDropdown(false);
    };

    // 渲染单个分享按钮
    const renderShareButton = (platform: SocialPlatform) => {
        const config = platformConfigs[platform];
        const Icon = config.icon;

        if (platform === 'copy' && copied) {
            return (
                <button
                    key={platform}
                    className={`${currentSize.button} rounded-full flex items-center justify-center transition-all duration-200 bg-green-500 hover:bg-green-600 text-white`}
                    title="已复制"
                >
                    <Check size={currentSize.icon} />
                </button>
            );
        }

        return (
            <button
                key={platform}
                onClick={() => handleShare(platform)}
                className={`${currentSize.button} rounded-full flex items-center justify-center transition-all duration-200 hover:scale-110 hover:shadow-lg`}
                style={{ backgroundColor: config.color, color: 'white' }}
                title={`分享到${config.name}`}
            >
                <Icon size={currentSize.icon} />
            </button>
        );
    };

    // 水平布局
    if (layout === 'horizontal') {
        return (
            <div className="flex items-center gap-2">
                <span className={`${currentSize.text} text-gray-600 dark:text-gray-400 mr-2`}>
                    分享:
                </span>
                {platforms.map((platform) => renderShareButton(platform))}
            </div>
        );
    }

    // 垂直布局
    if (layout === 'vertical') {
        return (
            <div className="flex flex-col gap-2">
                <span className={`${currentSize.text} text-gray-600 dark:text-gray-400 mb-1`}>
                    分享:
                </span>
                {platforms.map((platform) => renderShareButton(platform))}
            </div>
        );
    }

    // 下拉布局
    if (layout === 'dropdown') {
        return (
            <div className="relative">
                <button
                    onClick={() => setShowDropdown(!showDropdown)}
                    className={`${currentSize.button} rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors`}
                    title="分享"
                >
                    <Share2 size={currentSize.icon} />
                </button>

                {showDropdown && (
                    <>
                        {/* 遮罩层 */}
                        <div
                            className="fixed inset-0 z-10"
                            onClick={() => setShowDropdown(false)}
                        />
                        
                        {/* 下拉菜单 */}
                        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-20 py-2">
                            {platforms.map((platform) => {
                                const config = platformConfigs[platform];
                                const Icon = config.icon;

                                if (platform === 'copy' && copied) {
                                    return (
                                        <button
                                            key={platform}
                                            className="w-full px-4 py-2 flex items-center gap-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-green-600"
                                        >
                                            <Check size={18} />
                                            <span className={currentSize.text}>已复制</span>
                                        </button>
                                    );
                                }

                                return (
                                    <button
                                        key={platform}
                                        onClick={() => handleShare(platform)}
                                        className="w-full px-4 py-2 flex items-center gap-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <div
                                            className="w-6 h-6 rounded-full flex items-center justify-center"
                                            style={{ backgroundColor: config.color, color: 'white' }}
                                        >
                                            <Icon size={14} />
                                        </div>
                                        <span className={`${currentSize.text} text-gray-700 dark:text-gray-300`}>
                                            {config.name}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </>
                )}
            </div>
        );
    }

    return null;
};

export default SocialShare;
