'use client';

import React from 'react';
import Link from 'next/link';
import {useAuth} from '@/hooks/useAuth';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {Crown, FileText, LogOut, Settings, User} from 'lucide-react';

interface UserDropdownProps {
  user: {
    id: number;
    username: string;
    avatar?: string;
    is_vip?: boolean;
    is_superuser?: boolean;
  };
}

const UserDropdown = ({ user }: UserDropdownProps) => {
  const { logout } = useAuth();

  const handleLogout = async () => {
    if (window.confirm('确定要退出登录吗？')) {
      await logout();
    }
  };

  const getUserDisplayInfo = () => {
    const badges = [];
    if (user.is_superuser) {
      badges.push(
        <span key="admin" className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
          <Crown className="w-3 h-3 mr-1" />
          管理员
        </span>
      );
    }
    if (user.is_vip) {
      badges.push(
        <span key="vip" className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          VIP
        </span>
      );
    }
    return badges;
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md transition-colors duration-200"
          aria-label="用户菜单"
        >
          {user.avatar ? (
            <img 
              src={user.avatar} 
              alt="用户头像" 
              className="w-8 h-8 rounded-full ring-2 ring-white dark:ring-gray-700"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
              {user.username.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="hidden sm:block text-left">
            <div className="flex items-center space-x-2">
              <span className="truncate max-w-[120px]">{user.username}</span>
              {getUserDisplayInfo()}
            </div>
          </div>
          <svg 
            className="w-4 h-4 text-gray-500" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        className="w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1"
        align="end"
        sideOffset={8}
      >
        <DropdownMenuLabel className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-white">
          <div className="flex items-center space-x-2">
            {user.avatar ? (
              <img 
                src={user.avatar} 
                alt="用户头像" 
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
                {user.username.charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <div className="font-medium">{user.username}</div>
              <div className="flex items-center space-x-1 mt-1">
                {getUserDisplayInfo()}
              </div>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="my-1" />
        <DropdownMenuItem asChild>
          <Link 
            href="/profile" 
            className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 cursor-pointer"
          >
            <User className="w-4 h-4 mr-2" />
            <span>个人资料</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link 
            href="/my/posts" 
            className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 cursor-pointer"
          >
            <FileText className="w-4 h-4 mr-2" />
            <span>我的文章</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link 
            href="/settings" 
            className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 cursor-pointer"
          >
            <Settings className="w-4 h-4 mr-2" />
            <span>账户设置</span>
          </Link>
        </DropdownMenuItem>
        {user.is_superuser && (
          <DropdownMenuItem asChild>
            <Link 
              href="/admin" 
              className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 cursor-pointer"
            >
              <Crown className="w-4 h-4 mr-2 text-red-500" />
              <span>管理后台</span>
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator className="my-1" />
        <DropdownMenuItem 
          onClick={handleLogout}
          className="flex items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-gray-700 cursor-pointer"
        >
          <LogOut className="w-4 h-4 mr-2" />
          <span>退出登录</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

UserDropdown.displayName = 'UserDropdown';

export default UserDropdown;