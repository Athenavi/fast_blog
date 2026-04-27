'use client';

import React, {useEffect, useState} from 'react';
import {Avatar, AvatarFallback} from '@/components/ui/avatar';
import {Users, Wifi, WifiOff} from 'lucide-react';
import {CollaborativeEditingService, CollaborativeUser, generateUserColor} from '@/lib/collaborative-editing';

interface CollaborationBarProps {
    documentId: string;
    userId: string;
    userName: string;
}

export default function CollaborationBar({documentId, userId, userName}: CollaborationBarProps) {
    const [service, setService] = useState<CollaborativeEditingService | null>(null);
    const [onlineUsers, setOnlineUsers] = useState<CollaborativeUser[]>([]);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const collabService = new CollaborativeEditingService(
            documentId,
            userId,
            userName
        );

        // 设置回调
        collabService.onUserListChange = (users) => {
            setOnlineUsers(users);
        };

        collabService.onConnectionFailed = () => {
            setIsConnected(false);
        };

        // 连接服务器
        collabService.connect()
            .then(() => {
                setIsConnected(true);
            })
            .catch((error) => {
                console.error('连接失败:', error);
                setIsConnected(false);
            });

        setService(collabService);

        // 清理
        return () => {
            collabService.disconnect();
        };
    }, [documentId, userId, userName]);

    if (!service) {
        return null;
    }

    return (
        <div className="flex items-center gap-4 px-4 py-2 bg-white dark:bg-gray-800 border-b">
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

            {/* 在线用户 */}
            <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-gray-500"/>
                <span className="text-xs text-gray-600 dark:text-gray-400">
                    {onlineUsers.length + 1} 人在线
                </span>
            </div>

            {/* 用户头像列表 */}
            <div className="flex items-center -space-x-2">
                {/* 当前用户 */}
                <Avatar className="w-8 h-8 border-2 border-white dark:border-gray-800">
                    <AvatarFallback style={{backgroundColor: generateUserColor()}}>
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
    );
}
