'use client';

import React, {useEffect, useRef, useState} from 'react';
import {useRouter} from 'next/navigation';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient} from "@/lib/api";

interface ProfileForm {
    username: string;
    bio: string;
    locale: string;
    profilePrivate: boolean;
}

interface PasswordForm {
    currentPassword: string;
    newPassword: string;
    confirmPassword: string;
}

const SettingsPage = () => {
    const router = useRouter();
    const [user, setUser] = useState<any>(null);
    const [activeSection, setActiveSection] = useState('profile');
    const [userProfile, setUserProfile] = useState<any>(null);
    const [profileForm, setProfileForm] = useState<ProfileForm>({
        username: '',
        bio: '',
        locale: 'zh_CN',
        profilePrivate: false
    });
    const [passwordForm, setPasswordForm] = useState<PasswordForm>({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });
    const [usernameLock, setUsernameLock] = useState(false);
    const avatarInputRef = useRef<HTMLInputElement>(null);
    const [userAvatarUrl, setUserAvatarUrl] = useState('');
    const [loading, setLoading] = useState(true);

    // 加载用户资料
    useEffect(() => {
        const loadUserProfile = async () => {
            try {
                setLoading(true);
                const response = await apiClient.get('/users/me/profile');

                if (response.success && response.data) {
                    let userData;

                    if ((response.data as any).user) {
                        userData = (response.data as any).user;
                    } else {
                        userData = response.data;
                    }

                    setUserProfile(userData);
                    setProfileForm({
                        username: userData.username || '',
                        bio: userData.bio || '',
                        locale: userData.locale || 'zh_CN',
                        profilePrivate: userData.profile_private || false
                    });

                    setUserAvatarUrl(userData.avatar_url || `https://ui-avatars.com/api/?name=${userData.username || 'User'}&background=random`);
                } else {
                    console.error('获取用户资料失败:', response.error);
                }
            } catch (error) {
                console.error('获取用户资料时发生错误:', error);
            } finally {
                setLoading(false);
            }
        };

        loadUserProfile();
    }, []);

    const showSection = (section: string) => {
        setActiveSection(section);
    };

    const handleProfileChange = (field: keyof ProfileForm, value: any) => {
        setProfileForm(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handlePasswordChange = (field: keyof PasswordForm, value: string) => {
        setPasswordForm(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const updateUsername = async () => {
        if (!profileForm.username.trim()) {
            alert('用户名不能为空');
            return;
        }

        try {
            const response = await apiClient.put('/user-settings/profiles', {
                    change_type: 'username',
                    form_data: {
                        username: profileForm.username,
                    },
                },
            );

            if (response.success) {
                alert('用户名已更新');
                if (userProfile) {
                    setUserProfile({...userProfile, username: profileForm.username});
                }
                await refreshUser();
            } else {
                alert(response.error || '更新用户名失败');
            }
        } catch (error) {
            console.error('更新用户名时发生错误:', error);
            alert('更新用户名失败，请稍后重试');
        }
    };

    const updateBio = async () => {
        try {
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'bio',
                form_data: {
                    bio: profileForm.bio,
                }
            });

            if (response.success) {
                alert('个人简介已保存');
                if (userProfile) {
                    setUserProfile({...userProfile, bio: profileForm.bio});
                }
            } else {
                alert(response.error || '保存个人简介失败');
            }
        } catch (error) {
            console.error('保存个人简介时发生错误:', error);
            alert('保存个人简介失败，请稍后重试');
        }
    };

    const updateLocale = async () => {
        try {
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'locale',
                locale: profileForm.locale,
            });

            if (response.success) {
                alert('语言设置已更新');
                if (userProfile) {
                    setUserProfile({...userProfile, locale: profileForm.locale});
                }
                await refreshUser();
            } else {
                alert(response.error || '更新语言设置失败');
            }
        } catch (error) {
            console.error('更新语言设置时发生错误:', error);
            alert('更新语言设置失败，请稍后重试');
        }
    };

    const updatePrivacy = async () => {
        try {
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'privacy',
                profile_private: profileForm.profilePrivate,
            });

            if (response.success) {
                alert('隐私设置已保存');
                if (userProfile) {
                    setUserProfile({...userProfile, profile_private: profileForm.profilePrivate});
                }
            } else {
                alert(response.error || '保存隐私设置失败');
            }
        } catch (error) {
            console.error('保存隐私设置时发生错误:', error);
            alert('保存隐私设置失败，请稍后重试');
        }
    };

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('请上传 JPG、PNG 或 WEBP 格式的图片');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert('图片大小不能超过 5MB');
            return;
        }

        const formData = new FormData();
        formData.append('file', file, file.name);

        try {
            const response = await fetch(`/api/v1/user-settings/profile/avatar`, {
                method: 'PUT',
                body: formData,
                credentials: "include",
            });

            const result = await response.json();

            if (response.ok && result.success) {
                alert('头像更新成功');
                const reader = new FileReader();
                reader.onload = (e) => {
                    setUserAvatarUrl(e.target?.result as string);
                };
                reader.readAsDataURL(file);
                await refreshUser();
            } else {
                alert(result.error || '头像更新失败');
            }
        } catch (error) {
            console.error('上传头像时发生错误:', error);
            alert('头像更新失败，请稍后重试');
        }
    };

    const updatePassword = async () => {
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            alert('两次输入的密码不一致');
            return;
        }

        if (passwordForm.newPassword.length < 6) {
            alert('密码至少需要6位');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('current_password', passwordForm.currentPassword);
            formData.append('new_password', passwordForm.newPassword);
            formData.append('confirm_password', passwordForm.confirmPassword);

            const response = await fetch(`api/v1/users/me/security/change-password`, {
                method: 'PUT',
                body: formData,
                credentials: 'include',
            });

            const result = await response.json();

            if (response.ok && result.success) {
                alert('密码已更新');
                setPasswordForm({
                    currentPassword: '',
                    newPassword: '',
                    confirmPassword: ''
                });
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                router.push('/login');
            } else {
                alert(result.error || '更新密码失败');
            }
        } catch (error) {
            console.error('更新密码时发生错误:', error);
            alert('更新密码失败，请稍后重试');
        }
    };

    const changeEmail = () => {
        alert('换绑邮箱功能将在后续版本中实现');
    };

    const logout = async () => {
        if (confirm('确定要注销登录吗？')) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            router.push('/login');
        }
    };

    const refreshUser = async () => {
        try {
            const response = await apiClient.get('/users/me');
            if (response.success && response.data) {
                setUser(response.data);
            }
        } catch (error) {
            console.error('刷新用户信息失败:', error);
        }
    };

    const triggerAvatarUpload = () => {
        if (avatarInputRef.current) {
            avatarInputRef.current.click();
        }
    };

    const localeOptions = [
        {label: '简体中文', value: 'zh_CN'},
        {label: 'English', value: 'en_US'},
        {label: '日本語', value: 'ja_JP'}
    ];

    return (
        <WithAuthProtection loadingMessage="正在加载设置页面...">
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
                <div className="container mx-auto px-4 max-w-6xl">
                    <div className="flex flex-col lg:flex-row gap-6">
                        {/* 左侧导航 */}
                        <div className="w-full lg:w-64">
                            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                                <div className="space-y-1">
                                    <h4 className="text-lg font-bold mt-2 px-2 py-1">设置中心</h4>
                                    <nav className="space-y-1">
                                        <button
                                            onClick={() => showSection('profile')}
                                            className={`w-full text-left py-2 px-4 rounded-md flex items-center ${
                                                activeSection === 'profile'
                                                    ? 'bg-blue-500 text-white'
                                                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                        >
                                            <i className="fas fa-user mr-3"></i>
                                            个人资料
                                        </button>
                                        <button
                                            onClick={() => showSection('privacy')}
                                            className={`w-full text-left py-2 px-4 rounded-md flex items-center ${
                                                activeSection === 'privacy'
                                                    ? 'bg-blue-500 text-white'
                                                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                        >
                                            <i className="fas fa-lock mr-3"></i>
                                            隐私设置
                                        </button>
                                        <button
                                            onClick={() => showSection('password')}
                                            className={`w-full text-left py-2 px-4 rounded-md flex items-center ${
                                                activeSection === 'password'
                                                    ? 'bg-blue-500 text-white'
                                                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                        >
                                            <i className="fas fa-key mr-3"></i>
                                            修改密码
                                        </button>
                                        <button
                                            onClick={logout}
                                            className="w-full text-left py-2 px-4 rounded-md flex items-center text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                                        >
                                            <i className="fas fa-sign-out-alt mr-3"></i>
                                            注销登录
                                        </button>
                                    </nav>
                                </div>
                            </div>
                        </div>

                        {/* 右侧内容区域 */}
                        <div className="flex-1">
                            {/* 个人资料部分 */}
                            {activeSection === 'profile' && (
                                <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                                    <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
                                        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">个人资料设置</h2>
                                        <p className="text-gray-500 dark:text-gray-400">管理您的个人资料信息</p>
                                    </div>

                                    <div className="p-6">
                                        {/* 头像上传部分 */}
                                        <div className="flex flex-col items-center mb-8">
                                            <div className="relative mb-3">
                                                {userAvatarUrl ? (
                                                    <img
                                                        src={userAvatarUrl}
                                                        alt="头像"
                                                        className="w-32 h-32 rounded-full ring-4 ring-white shadow-lg object-cover cursor-pointer"
                                                        onClick={triggerAvatarUpload}
                                                    />
                                                ) : (
                                                    <div
                                                        className="w-32 h-32 rounded-full ring-4 ring-white shadow-lg bg-gray-200 flex items-center justify-center cursor-pointer"
                                                        onClick={triggerAvatarUpload}>
                                                        <i className="fas fa-user text-gray-500 text-2xl"></i>
                                                    </div>
                                                )}
                                                <div
                                                    className="absolute inset-0 bg-black bg-opacity-30 rounded-full flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity cursor-pointer"
                                                    onClick={triggerAvatarUpload}
                                                >
                                                    <i className="fas fa-edit text-white text-xl"></i>
                                                </div>
                                            </div>
                                            <input
                                                ref={avatarInputRef}
                                                type="file"
                                                accept="image/*"
                                                className="hidden"
                                                onChange={handleAvatarChange}
                                            />
                                            <p className="text-gray-500 text-sm dark:text-gray-400">支持 JPG, PNG 格式，大小不超过
                                                5MB</p>
                                        </div>

                                        {/* 用户名 */}
                                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
                                            <div
                                                className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-800 dark:text-white mb-1">用户名</h3>
                                                    <p className="text-gray-500 text-sm dark:text-gray-400">设置一个独特的用户名，4-16个字符</p>
                                                </div>
                                                <div className="w-full md:w-64 mb-2 md:mb-0">
                                                    <input
                                                        type="text"
                                                        value={profileForm.username}
                                                        onChange={(e) => handleProfileChange('username', e.target.value)}
                                                        disabled={usernameLock}
                                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                                                        placeholder="输入用户名"
                                                    />
                                                </div>
                                                <button
                                                    onClick={updateUsername}
                                                    disabled={usernameLock}
                                                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                                                >
                                                    更新用户名
                                                </button>
                                            </div>
                                        </div>

                                        {/* 电子邮箱 */}
                                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
                                            <div
                                                className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-800 dark:text-white mb-1">电子邮箱</h3>
                                                    <p className="text-gray-500 text-sm dark:text-gray-400">
                                                        当前绑定邮箱: {userProfile?.email || ''}
                                                    </p>
                                                </div>
                                                <button
                                                    onClick={changeEmail}
                                                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 whitespace-nowrap"
                                                >
                                                    换绑邮箱
                                                </button>
                                            </div>
                                        </div>

                                        {/* 个人简介 */}
                                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
                                            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                                                <div className="w-full">
                                                    <h3 className="font-medium text-gray-800 dark:text-white mb-1">个人简介</h3>
                                                    <p className="text-gray-500 text-sm dark:text-gray-400">用一段话介绍你自己</p>
                                                    <textarea
                                                        value={profileForm.bio}
                                                        onChange={(e) => handleProfileChange('bio', e.target.value)}
                                                        rows={3}
                                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white mt-2"
                                                        placeholder="输入个人简介"
                                                    />
                                                </div>
                                                <button
                                                    onClick={updateBio}
                                                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 whitespace-nowrap mt-4 md:mt-0"
                                                >
                                                    保存简介
                                                </button>
                                            </div>
                                        </div>

                                        {/* 语言设置 */}
                                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                                            <div
                                                className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-800 dark:text-white mb-1">语言设置</h3>
                                                    <p className="text-gray-500 text-sm dark:text-gray-400">选择界面显示语言</p>
                                                </div>
                                                <div className="w-full md:w-64 mb-2 md:mb-0">
                                                    <select
                                                        value={profileForm.locale}
                                                        onChange={(e) => handleProfileChange('locale', e.target.value)}
                                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                                                    >
                                                        {localeOptions.map(option => (
                                                            <option key={option.value} value={option.value}>
                                                                {option.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <button
                                                    onClick={updateLocale}
                                                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 whitespace-nowrap"
                                                >
                                                    更新语言
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* 隐私设置部分 */}
                            {activeSection === 'privacy' && (
                                <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                                    <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
                                        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">隐私设置</h2>
                                    </div>

                                    <div className="p-6 space-y-6">
                                        {/* 公开资料 */}
                                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                                            <div
                                                className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-800 dark:text-white mb-1">公开资料</h3>
                                                    <p className="text-gray-500 text-sm dark:text-gray-400">选择是否公开您的个人资料</p>
                                                </div>
                                                <div className="flex items-center mb-2 md:mb-0">
                                                    <label className="relative inline-flex items-center cursor-pointer">
                                                        <input
                                                            type="checkbox"
                                                            checked={!profileForm.profilePrivate}
                                                            onChange={(e) => handleProfileChange('profilePrivate', !e.target.checked)}
                                                            className="sr-only peer"
                                                        />
                                                        <div
                                                            className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                                                        <span
                                                            className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-300">
                                                            {profileForm.profilePrivate ? '私有' : '公开'}
                                                        </span>
                                                    </label>
                                                </div>
                                                <button
                                                    onClick={updatePrivacy}
                                                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 whitespace-nowrap"
                                                >
                                                    保存设置
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* 修改密码部分 */}
                            {activeSection === 'password' && (
                                <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                                    <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
                                        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">修改密码</h2>
                                    </div>

                                    <div className="p-6 max-w-md">
                                        <div className="space-y-4">
                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    当前密码
                                                </label>
                                                <input
                                                    type="password"
                                                    value={passwordForm.currentPassword}
                                                    onChange={(e) => handlePasswordChange('currentPassword', e.target.value)}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                                                    placeholder="输入当前密码"
                                                />
                                            </div>
                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    新密码
                                                </label>
                                                <input
                                                    type="password"
                                                    value={passwordForm.newPassword}
                                                    onChange={(e) => handlePasswordChange('newPassword', e.target.value)}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                                                    placeholder="输入新密码"
                                                />
                                            </div>
                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    确认新密码
                                                </label>
                                                <input
                                                    type="password"
                                                    value={passwordForm.confirmPassword}
                                                    onChange={(e) => handlePasswordChange('confirmPassword', e.target.value)}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-600 dark:border-gray-500 dark:text-white"
                                                    placeholder="确认新密码"
                                                />
                                            </div>
                                            <button
                                                onClick={updatePassword}
                                                className="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                                            >
                                                更新密码
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </WithAuthProtection>
    );
};

export default SettingsPage;