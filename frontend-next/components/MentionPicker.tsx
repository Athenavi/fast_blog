'use client';

import React, {useEffect, useRef, useState} from 'react';
import {Button} from '@/components/ui/button';
import {Avatar, AvatarFallback, AvatarImage} from '@/components/ui/avatar';
import {ScrollArea} from '@/components/ui/scroll-area';

interface User {
    id: number;
    username: string;
    avatar_url?: string;
}

interface MentionPickerProps {
    onSelect: (username: string) => void;
    query: string;
    position: { top: number; left: number };
    users: User[];
}

export function MentionPicker({onSelect, query, position, users}: MentionPickerProps) {
    const [selectedIndex, setSelectedIndex] = useState(0);
    const pickerRef = useRef<HTMLDivElement>(null);

    // 过滤用户列表
    const filteredUsers = users.filter(user =>
        user.username.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 10); // 最多显示10个用户

    // 键盘导航
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (filteredUsers.length === 0) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setSelectedIndex(prev => (prev + 1) % filteredUsers.length);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    setSelectedIndex(prev => (prev - 1 + filteredUsers.length) % filteredUsers.length);
                    break;
                case 'Enter':
                case 'Tab':
                    e.preventDefault();
                    if (filteredUsers[selectedIndex]) {
                        onSelect(filteredUsers[selectedIndex].username);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    // 关闭选择器（由父组件处理）
                    break;
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [filteredUsers, selectedIndex, onSelect]);

    // 点击外部关闭
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
                // 由父组件处理关闭逻辑
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (filteredUsers.length === 0) {
        return null;
    }

    return (
        <div
            ref={pickerRef}
            className="fixed z-50 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl"
            style={{
                top: position.top,
                left: position.left,
            }}
        >
            <ScrollArea className="max-h-64">
                <div className="p-1">
                    {filteredUsers.map((user, index) => (
                        <Button
                            key={user.id}
                            variant="ghost"
                            className={`w-full justify-start px-2 py-1.5 ${
                                index === selectedIndex ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                            }`}
                            onClick={() => onSelect(user.username)}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            <Avatar className="h-6 w-6 mr-2">
                                <AvatarImage src={user.avatar_url} alt={user.username}/>
                                <AvatarFallback>{user.username[0]?.toUpperCase()}</AvatarFallback>
                            </Avatar>
                            <span className="text-sm">{user.username}</span>
                        </Button>
                    ))}
                </div>
            </ScrollArea>
        </div>
    );
}
