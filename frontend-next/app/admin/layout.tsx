'use client';

import React, {useEffect, useState} from 'react';
import Link from 'next/link';
import {usePathname, useRouter} from 'next/navigation';
import {
    FaArchive,
    FaBars,
    FaChartPie,
    FaCog,
    FaComments,
    FaExclamationTriangle,
    FaFileAlt,
    FaFileArchive,
    FaFolder,
    FaSlidersH,
    FaThLarge,
    FaTimes,
    FaUsers
} from 'react-icons/fa';
import './admin.css';
import {useAuth} from '@/hooks/useAuth';

interface AdminLayoutProps {
    children: React.ReactNode;
}

const AdminLayout: React.FC<AdminLayoutProps> = ({children}) => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [userMenuOpen, setUserMenuOpen] = useState(false);
    const [showGenericModal, setShowGenericModal] = useState(false);
    const [genericModalTitle, setGenericModalTitle] = useState('');
    const [genericModalContent, setGenericModalContent] = useState<React.ReactNode>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteMessage, setDeleteMessage] = useState('');
    const [deleteCallback, setDeleteCallback] = useState<(() => void) | null>(null);

    const pathname = usePathname();
    const router = useRouter();
    const {user: currentUser, loading, checkAuthStatus} = useAuth();

    // 检查用户是否为管理员
    useEffect(() => {
        if (!loading) {
            if (!currentUser) {
                // 用户未登录，重定向到登录页
                router.push('/login');
            } else if (!currentUser.is_superuser) {
                // 用户不是管理员，重定向到首页
                router.push('/');
            }
        }
    }, [currentUser, loading, router]);

    // 切换移动端侧边栏
    const toggleSidebar = () => {
        setSidebarOpen(!sidebarOpen);
    };

    // 关闭侧边栏当点击外部区域（仅在移动端）
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const sidebar = document.querySelector('.sidebar');
            const menuToggle = document.getElementById('menuToggle');

            if (
                window.innerWidth <= 768 &&
                sidebar &&
                menuToggle &&
                !sidebar.contains(event.target as Node) &&
                !menuToggle.contains(event.target as Node)
            ) {
                setSidebarOpen(false);
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, []);

    // 检查当前路径是否匹配指定路径
    const isActivePath = (path: string) => {
        if (path === '/admin') {
            return pathname === '/admin';
        }
        return pathname.startsWith(path);
    };

    // 显示删除确认对话框
    const showDeleteConfirm = (message: string, callback: () => void) => {
        setDeleteMessage(message);
        setDeleteCallback(() => callback);
        setShowDeleteModal(true);
    };

    // 确认删除
    const confirmDelete = () => {
        if (deleteCallback) {
            deleteCallback();
        }
        setShowDeleteModal(false);
    };

    // 显示通用模态框
    const showModal = (title: string, content: React.ReactNode) => {
        setGenericModalTitle(title);
        setGenericModalContent(content);
        setShowGenericModal(true);
    };

    // 关闭模态框
    const closeModal = () => {
        setShowGenericModal(false);
        setShowDeleteModal(false);
    };

    // 注销处理
    const handleLogout = () => {
        if (confirm('确认注销？')) {
            window.location.href = '/logout';
        }
    };

    // 提供全局方法给其他组件使用
    useEffect(() => {
        (window as any).showDeleteConfirm = showDeleteConfirm;
        (window as any).showModal = showModal;

        return () => {
            delete (window as any).showDeleteConfirm;
            delete (window as any).showModal;
        };
    }, [deleteCallback, genericModalContent]);

    return (
        <div className="flex h-screen bg-gray-50 wp-admin-body">
            {/* 移动端菜单按钮 */}
            <div className="md:hidden fixed top-4 left-4 z-50">
                <button
                    id="menuToggle"
                    onClick={toggleSidebar}
                    className="p-2 rounded-md bg-white shadow-md text-gray-600"
                >
                    <FaBars/>
                </button>
            </div>

            {/* 侧边栏 */}
            <aside
                className={`sidebar fixed inset-y-0 left-0 z-40 w-64 bg-white shadow-lg transform ${
                    sidebarOpen ? 'active translate-x-0' : '-translate-x-full'
                } transition-transform duration-300 ease-in-out md:translate-x-0`}
            >
                {/* 导航菜单 */}
                <nav className="mt-6 px-4 flex-grow">
                    <div className="space-y-2">
                        {/* 仪表板 */}
                        <div className="mb-4">
                            <Link
                                href="/admin"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin') && !pathname.startsWith('/admin/analytics')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaChartPie className="mr-3"/>
                                <span>仪表板</span>
                            </Link>
                        </div>

                        {/* 内容管理 */}
                        <div className="mb-4">
                            <div className="nav-group-title px-4 py-2 text-sm font-medium text-gray-500">内容管理</div>
                            <Link
                                href="/admin/blog"
                                className="flex items-center px-4 py-3 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                <FaFileAlt className="mr-3"/>
                                <span>文章管理</span>
                            </Link>
                            <Link
                                href="/admin/categories"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/categories')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaFolder className="mr-3"/>
                                <span>分类管理</span>
                            </Link>
                        </div>

                        <hr className="my-4 border-gray-200"/>

                        {/* 媒体与文件 */}
                        <div className="mb-4">
                            <div className="nav-group-title px-4 py-2 text-sm font-medium text-gray-500">媒体与文件
                            </div>
                            <Link
                                href="/admin/media"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/media')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaFileArchive className="mr-3"/>
                                <span>附件管理</span>
                            </Link>
                            <Link
                                href="/admin/backup"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/backup')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaArchive className="mr-3"/>
                                <span>数据备份</span>
                            </Link>
                        </div>

                        <hr className="my-4 border-gray-200"/>

                        {/* 用户与插件 */}
                        <div className="mb-4">
                            <div className="nav-group-title px-4 py-2 text-sm font-medium text-gray-500">系统扩展</div>
                            <Link
                                href="/admin/user"
                                className="flex items-center px-4 py-3 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                <FaUsers className="mr-3"/>
                                <span>用户管理</span>
                            </Link>
                            <Link
                                href="/admin/comment-config"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/comment-config')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaComments className="mr-3"/>
                                <span>评论配置</span>
                            </Link>
                            <Link
                                href="/admin/config-manager"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/config-manager')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaSlidersH className="mr-3"/>
                                <span>配置管理</span>
                            </Link>
                            <Link
                                href="/admin/vip"
                                className={`flex items-center px-4 py-3 rounded-lg ${
                                    isActivePath('/admin/vip')
                                        ? 'text-primary bg-blue-50 font-medium'
                                        : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <FaThLarge className="mr-3"/>
                                <span>会员管理</span>
                            </Link>
                        </div>
                    </div>
                </nav>

                {/* 固定在底部的设置 */}
                <div className="mt-auto p-4 border-t">
                    <Link
                        href="/admin/settings"
                        className={`flex items-center px-4 py-3 rounded-lg ${
                            isActivePath('/admin/settings')
                                ? 'text-primary bg-blue-50 font-medium'
                                : 'text-gray-600 hover:bg-gray-100'
                        }`}
                    >
                        <FaCog className="mr-3"/>
                        <span>系统设置</span>
                    </Link>
                </div>
            </aside>

            {/* 主内容区域 */}
            <div className="md:ml-64 flex-1 flex flex-col min-h-screen main-content">
                {/* 顶部导航 */}
                <header className="bg-white shadow-sm wp-header">
                    <div className="flex justify-between items-center h-16 px-6">
                        <div className="flex items-center">
                            <h1 className="text-xl font-semibold">
                                {pathname === '/admin' ? '仪表板' :
                                    pathname === '/admin/analytics' ? '分析数据' :
                                        pathname === '/admin/blog' ? '文章管理' :
                                            pathname === '/admin/categories' ? '分类管理' :
                                                pathname === '/admin/media' ? '附件管理' :
                                                    pathname === '/admin/backup' ? '数据备份' :
                                                        pathname === '/admin/users' ? '用户管理' :
                                                            pathname === '/admin/comment-config' ? '评论配置' :
                                                                pathname === '/admin/config-manager' ? '配置管理' :
                                                                    pathname === '/admin/settings' ? '系统设置' :
                                                                        pathname === '/admin/misc' ? '更多管理' : '管理后台'}
                            </h1>
                        </div>
                    </div>
                </header>

                {/* 主要内容 */}
                <main className="flex-1 p-4 md:p-6 bg-gray-50 flex-1 overflow-y-auto">
                    {children}
                </main>
            </div>

            {/* 通用模态框 */}
            {showGenericModal && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                    <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
                        <div className="mt-3">
                            <div className="flex justify-between items-center pb-3 border-b">
                                <h3 className="text-lg font-medium text-gray-900">{genericModalTitle}</h3>
                                <button
                                    className="text-gray-400 hover:text-gray-500"
                                    onClick={closeModal}
                                >
                                    <FaTimes/>
                                </button>
                            </div>
                            <div className="mt-4">
                                {genericModalContent}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 删除确认模态框 */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                    <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                        <div className="mt-3 text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                                <FaExclamationTriangle className="text-red-600"/>
                            </div>
                            <h3 className="text-lg leading-6 font-medium text-gray-900 mt-2">确认删除</h3>
                            <div className="mt-2 px-7 py-3">
                                <p className="text-sm text-gray-500" id="deleteMessage">
                                    {deleteMessage}
                                </p>
                            </div>
                            <div className="items-center px-4 py-3 mt-3">
                                <button
                                    onClick={confirmDelete}
                                    className="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md w-full shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-300"
                                >
                                    确认删除
                                </button>
                                <button
                                    onClick={closeModal}
                                    className="mt-2 px-4 py-2 bg-gray-300 text-gray-700 text-base font-medium rounded-md w-full shadow-sm hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-300"
                                >
                                    取消
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminLayout;