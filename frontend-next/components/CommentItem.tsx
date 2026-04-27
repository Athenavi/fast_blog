/**
 * 单个评论项组件 - 支持嵌套回复
 */

'use client';

import React, {useState} from 'react';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Avatar, AvatarFallback, AvatarImage} from '@/components/ui/avatar';
import {MessageSquare, MoreVertical, ThumbsUp} from 'lucide-react';
import {DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,} from '@/components/ui/dropdown-menu';
import {parseEmotes} from '@/lib/emoteService';

interface Comment {
    id: number;
    article_id: number;
    user_id: number | null;
    username?: string;
    author_name: string | null;
    author_email: string | null;
    author_url: string | null;
    content: string;
    is_approved: boolean;
    created_at: string;
    likes: number;
    parent_id: number | null;
    avatar_url?: string;
    replies?: Comment[];
}

interface CommentItemProps {
    comment: Comment;
    onReply: (commentId: number, authorName: string) => void;
    onLike: (commentId: number) => void;
    formatDate: (dateString: string) => string;
    depth: number;
}

const CommentItem: React.FC<CommentItemProps> = ({
                                                     comment,
                                                     onReply,
                                                     onLike,
                                                     formatDate,
                                                     depth
                                                 }) => {
    const [isLiked, setIsLiked] = useState(false);
    const maxDepth = 5; // 最大嵌套层级

    // 获取作者名称
    const getAuthorName = () => {
        return comment.username || comment.author_name || '匿名用户';
    };

    // 获取头像
    const getAvatarUrl = () => {
        return comment.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${comment.id}`;
    };

    // 处理点赞
    const handleLike = () => {
        if (!isLiked) {
            setIsLiked(true);
            onLike(comment.id);
        }
    };

    // 处理回复
    const handleReply = () => {
        onReply(comment.id, getAuthorName());
    };

    // 渲染评论内容（支持简单的Markdown和表情）
    const renderContent = (content: string) => {
        // 先解析表情
        const contentWithEmotes = parseEmotes(content);
        
        // 检测 @用户名 并高亮
        const parts = contentWithEmotes.split(/(@\w+)/g);
        return parts.map((part, index) => {
            if (part.startsWith('@')) {
                return (
                    <span key={index} className="text-blue-600 dark:text-blue-400 font-medium">
            {part}
          </span>
                );
            }
            return part;
        });
    };

    return (
        <div className={`${depth > 0 ? 'ml-8 mt-4' : ''}`}>
            <div
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow">
                <div className="flex gap-3">
                    {/* 头像 */}
                    <Avatar className="w-10 h-10 flex-shrink-0">
                        <AvatarImage src={getAvatarUrl()} alt={getAuthorName()}/>
                        <AvatarFallback>
                            {getAuthorName().charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>

                    {/* 评论内容 */}
                    <div className="flex-1 min-w-0">
                        {/* 作者信息 */}
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 dark:text-white">
                  {getAuthorName()}
                </span>
                                {comment.user_id && (
                                    <Badge variant="secondary" className="text-xs">
                                        已认证
                                    </Badge>
                                )}
                                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDate(comment.created_at)}
                </span>
                            </div>

                            {/* 更多操作 */}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                        <MoreVertical className="w-4 h-4"/>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={handleReply}>
                                        <MessageSquare className="w-4 h-4 mr-2"/>
                                        回复
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>

                        {/* 评论内容 */}
                        <div className="text-gray-700 dark:text-gray-300 mb-3 whitespace-pre-wrap break-words">
                            {renderContent(comment.content)}
                        </div>

                        {/* 操作按钮 */}
                        <div className="flex items-center gap-4">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleLike}
                                className={`h-8 px-2 ${isLiked ? 'text-blue-600' : 'text-gray-500'}`}
                            >
                                <ThumbsUp className={`w-4 h-4 mr-1 ${isLiked ? 'fill-current' : ''}`}/>
                                {comment.likes > 0 && <span>{comment.likes}</span>}
                            </Button>

                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleReply}
                                className="h-8 px-2 text-gray-500"
                            >
                                <MessageSquare className="w-4 h-4 mr-1"/>
                                回复
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* 递归渲染回复 */}
            {comment.replies && comment.replies.length > 0 && depth < maxDepth && (
                <div className="mt-2">
                    {comment.replies.map((reply) => (
                        <CommentItem
                            key={reply.id}
                            comment={reply}
                            onReply={onReply}
                            onLike={onLike}
                            formatDate={formatDate}
                            depth={depth + 1}
                        />
                    ))}
                </div>
            )}

            {/* 超过最大深度提示 */}
            {comment.replies && comment.replies.length > 0 && depth >= maxDepth && (
                <div className="ml-8 mt-2 text-sm text-gray-500">
                    还有 {comment.replies.length} 条回复...
                </div>
            )}
        </div>
    );
};

export default CommentItem;
