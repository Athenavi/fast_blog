'use client';

import React, {useState} from 'react';
import {Avatar, AvatarFallback} from '@/components/ui/avatar';
import {Button} from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {Clock, Save, Users, Wifi, WifiOff} from 'lucide-react';
import {CollaborativeUser, generateUserColor} from '@/lib/collaborative-editing';
import {getSaveDocumentUrl} from '@/lib/collaboration-config';
import {useToast} from '@/hooks/use-toast';

interface CollaborationBarProps {
    documentId: string;
    userId: string;
    userName: string;
    articleId?: number;
    editor?: any; // ProseMirror/Tiptap editor instance
    isConnected?: boolean; // 从父组件传入连接状态
    onlineUsers?: CollaborativeUser[]; // 从父组件传入在线用户列表
}

export default function CollaborationBar({
                                             documentId,
                                             userId,
                                             userName,
                                             articleId,
                                             editor,
                                             isConnected: propIsConnected,
                                             onlineUsers: propOnlineUsers
                                         }: CollaborationBarProps) {
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [showUserList, setShowUserList] = useState(false);
    const {toast} = useToast();

    // 使用父组件传入的状态，如果没有则使用内部状态
    const [internalIsConnected, setInternalIsConnected] = useState(false);
    const [internalOnlineUsers, setInternalOnlineUsers] = useState<CollaborativeUser[]>([]);

    const isConnected = propIsConnected !== undefined ? propIsConnected : internalIsConnected;
    const onlineUsers = propOnlineUsers !== undefined ? propOnlineUsers : internalOnlineUsers;

    // 保存文档到修订历史
    const handleSave = async () => {
        if (!editor) {
            toast({
                title: '保存失败',
                description: '编辑器未初始化',
                variant: 'destructive'
            });
            return;
        }

        // 不检查 isConnected，允许离线保存
        // if (!isConnected) {
        //     toast({
        //         title: '保存失败',
        //         description: '未连接到协作服务器',
        //         variant: 'destructive'
        //     });
        //     return;
        // }

        try {
            setIsSaving(true);

            // 兼容不同类型的编辑器
            let content = '';
            if (typeof editor.getHTML === 'function') {
                // Tiptap/ProseMirror 编辑器
                content = editor.getHTML();
            } else if (typeof editor.value === 'function') {
                // EasyMDE/Markdown 编辑器
                content = editor.value();
            } else {
                throw new Error('不支持的编辑器类型');
            }

            console.log('[Collab] 准备保存内容，长度:', content.length);
            const url = getSaveDocumentUrl(documentId);

            const response = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({
                    content,
                    change_summary: '协作编辑手动保存'
                }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Collab] Save API error:', response.status, errorText);
                throw new Error(`保存失败: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[Collab] 保存成功:', data);

            setLastSaved(new Date());
            toast({
                title: '保存成功',
                description: '内容已保存到修订历史'
            });
        } catch (error) {
            console.error('[Collab] 保存错误:', error);
            const errorMsg = error instanceof Error ? error.message : '保存失败';
            toast({
                title: '保存失败',
                description: errorMsg,
                variant: 'destructive'
            });
        } finally {
            setIsSaving(false);
        }
    };

    if (!userId || !userName) {
        return null;
    }

    // 获取当前用户信息
    const currentUser: CollaborativeUser = {
        id: userId,
        name: userName,
        color: generateUserColor(),
        cursor: undefined,
        selection: undefined
    };

    // 所有在线用户（包括当前用户）
    const allUsers = [currentUser, ...onlineUsers];

    // 格式化时间
    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
    };

    return (
        <div className="flex items-center justify-between gap-4 px-4 py-2 bg-white dark:bg-gray-800 border-b">
            {/* 左侧：连接状态和在线用户 */}
            <div className="flex items-center gap-4">
                {/* 连接状态 */}
                <div className="flex items-center gap-2">
                    {isConnected ? (
                        <>
                            <Wifi className="w-4 h-4 text-green-600"/>
                            <span className="text-xs text-green-600 font-medium">在线</span>
                        </>
                    ) : (
                        <>
                            <WifiOff className="w-4 h-4 text-red-600"/>
                            <span className="text-xs text-red-600 font-medium">离线</span>
                        </>
                    )}
                </div>

                {/* 分隔线 */}
                <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"/>

                {/* 在线用户下拉菜单 */}
                <DropdownMenu open={showUserList} onOpenChange={setShowUserList}>
                    <DropdownMenuTrigger asChild>
                        <button
                            className="flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg px-2 py-1 transition-colors">
                            <Users className="w-4 h-4 text-gray-500"/>
                            <span className="text-xs text-gray-600 dark:text-gray-400">
                                {allUsers.length} 人在线
                            </span>
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-64">
                        <div className="px-2 py-1.5 text-sm font-semibold text-gray-900 dark:text-gray-100">
                            在线用户
                        </div>
                        <DropdownMenuSeparator/>
                        {allUsers.map((user) => (
                            <DropdownMenuItem key={user.id} className="flex items-center gap-3 cursor-default">
                                <Avatar className="w-8 h-8">
                                    <AvatarFallback style={{backgroundColor: user.color}}>
                                        {user.name.charAt(0).toUpperCase()}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex flex-col">
                                    <span className="text-sm font-medium">{user.name}</span>
                                    {user.id === userId && (
                                        <span className="text-xs text-gray-500">（我）</span>
                                    )}
                                </div>
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* 用户头像列表 */}
                <div className="flex items-center -space-x-2">
                    {/* 当前用户 */}
                    <Avatar className="w-8 h-8 border-2 border-white dark:border-gray-800">
                        <AvatarFallback style={{backgroundColor: currentUser.color}}>
                            {userName.charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>

                    {/* 其他在线用户 */}
                    {onlineUsers.slice(0, 4).map((user) => (
                        <Avatar
                            key={user.id}
                            className="w-8 h-8 border-2 border-white dark:border-gray-800"
                            title={user.name}
                        >
                            <AvatarFallback style={{backgroundColor: user.color}}>
                                {user.name.charAt(0).toUpperCase()}
                            </AvatarFallback>
                        </Avatar>
                    ))}

                    {/* 更多用户 */}
                    {onlineUsers.length > 4 && (
                        <div
                            className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 border-2 border-white dark:border-gray-800 flex items-center justify-center">
                            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                                +{onlineUsers.length - 4}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* 右侧：保存按钮和最后保存时间 */}
            <div className="flex items-center gap-3">
                {/* 最后保存时间 */}
                {lastSaved && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock className="w-3 h-3"/>
                        <span>最后保存: {formatTime(lastSaved)}</span>
                    </div>
                )}

                {/* 保存按钮 */}
                <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    size="sm"
                    className="gap-2"
                >
                    <Save className={`w-4 h-4 ${isSaving ? 'animate-spin' : ''}`}/>
                    {isSaving ? '保存中...' : '保存'}
                </Button>
            </div>
        </div>
    );
}
