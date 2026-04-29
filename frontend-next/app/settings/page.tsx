'use client';

import React, {useEffect, useRef, useState} from 'react';
import {useRouter} from 'next/navigation';
import Image from 'next/image';
import {motion} from 'framer-motion';
import {
    User,
    Shield,
    Bell,
    Palette,
    Globe,
    Lock,
    Mail,
    Upload,
    Camera,
    Check,
    X,
    LogOut,
    Save,
    Eye,
    EyeOff,
    Smartphone,
    Moon,
    Sun
} from 'lucide-react';
import WithAuthProtection from '@/components/WithAuthProtection';
import {apiClient} from "@/lib/api";

// 动画配置
const fadeInUp = {
    initial: {opacity: 0, y: 20},
    animate: {opacity: 1, y: 0},
    transition: {duration: 0.5}
};

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

type TabType = 'profile' | 'account' | 'appearance' | 'notifications';

const SettingsPage = () => {
    const router = useRouter();
    const [userProfile, setUserProfile] = useState<any>(null);
    const [activeTab, setActiveTab] = useState<TabType>('profile');
    const [avatarUrl, setAvatarUrl] = useState('');
    const [loading, setLoading] = useState(true);
    const avatarInputRef = useRef<HTMLInputElement>(null);

    // 表单状态
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
    const [showPassword, setShowPassword] = useState(false);
    const [saving, setSaving] = useState(false);

    // 加载用户资料
    useEffect(() => {
        const loadUserProfile = async () => {
            try {
                setLoading(true);
                const response = await apiClient.get('/management/me/profile');

                if (response.success && response.data) {
                    let userData = (response.data as any).user || response.data;
                    setUserProfile(userData);

                    setProfileForm({
                        username: userData.username || '',
                        bio: userData.bio || '',
                        locale: userData.locale || 'zh_CN',
                        profilePrivate: userData.profile_private || false
                    });

                    // 获取头像 URL
                    let avatarUrl = userData.avatar_url;
                    if (!avatarUrl && userData.avatar) {
                        try {
                            const config = await import('@/lib/config');
                            const apiConfig = config.getConfig();
                            const avatarResponse = await fetch(
                                `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/user/avatar?user_id=${userData.id}`,
                                {credentials: 'include'}
                            );
                            if (avatarResponse.ok) {
                                const text = await avatarResponse.text();
                                avatarUrl = text.replace(/^"|"$/g, '');
                            }
                        } catch (error) {
                            console.error('获取头像 URL 失败:', error);
                        }
                    }

                    setAvatarUrl(avatarUrl || `https://ui-avatars.com/api/?name=${userData.username || 'User'}&background=random`);
                }
            } catch (error) {
                console.error('获取用户资料时发生错误:', error);
            } finally {
                setLoading(false);
            }
        };

        loadUserProfile();
    }, []);

    // 更新头像
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
            setSaving(true);
            const config = await import('@/lib/config');
            const apiConfig = config.getConfig();

            const response = await fetch(
                `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/user-settings/profile/avatar`,
                {
                    method: 'PUT',
                    body: formData,
                    credentials: "include",
                }
            );

            const result = await response.json();

            if (response.ok && result.success) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    setAvatarUrl(e.target?.result as string);
                };
                reader.readAsDataURL(file);
            } else {
                alert(result.error || '头像更新失败');
            }
        } catch (error) {
            console.error('上传头像时发生错误:', error);
            alert('头像更新失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 更新用户名
    const updateUsername = async () => {
        if (!profileForm.username.trim()) {
            alert('用户名不能为空');
            return;
        }

        try {
            setSaving(true);
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'username',
                form_data: {username: profileForm.username},
            });

            if (response.success) {
                setUserProfile({...userProfile, username: profileForm.username});
            } else {
                alert(response.error || '更新用户名失败');
            }
        } catch (error) {
            console.error('更新用户名时发生错误:', error);
            alert('更新用户名失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 更新简介
    const updateBio = async () => {
        try {
            setSaving(true);
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'bio',
                form_data: {bio: profileForm.bio}
            });

            if (response.success) {
                setUserProfile({...userProfile, bio: profileForm.bio});
            } else {
                alert(response.error || '保存个人简介失败');
            }
        } catch (error) {
            console.error('保存个人简介时发生错误:', error);
            alert('保存个人简介失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 更新语言
    const updateLocale = async () => {
        try {
            setSaving(true);
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'locale',
                locale: profileForm.locale,
            });

            if (response.success) {
                setUserProfile({...userProfile, locale: profileForm.locale});
            } else {
                alert(response.error || '更新语言设置失败');
            }
        } catch (error) {
            console.error('更新语言设置时发生错误:', error);
            alert('更新语言设置失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 更新隐私设置
    const updatePrivacy = async () => {
        try {
            setSaving(true);
            const response = await apiClient.put('/user-settings/profiles', {
                change_type: 'privacy',
                profile_private: profileForm.profilePrivate,
            });

            if (response.success) {
                setUserProfile({...userProfile, profile_private: profileForm.profilePrivate});
            } else {
                alert(response.error || '保存隐私设置失败');
            }
        } catch (error) {
            console.error('保存隐私设置时发生错误:', error);
            alert('保存隐私设置失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 更新密码
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
            setSaving(true);
            const config = await import('@/lib/config');
            const apiConfig = config.getConfig();
            const formData = new FormData();
            formData.append('current_password', passwordForm.currentPassword);
            formData.append('new_password', passwordForm.newPassword);
            formData.append('confirm_password', passwordForm.confirmPassword);

            const response = await fetch(
                `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/users/me/security/change-password`,
                {
                    method: 'PUT',
                    body: formData,
                    credentials: 'include',
                }
            );

            const result = await response.json();

            if (response.ok && result.success) {
                alert('密码已更新，请重新登录');
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                router.push('/login');
            } else {
                alert(result.error || '更新密码失败');
            }
        } catch (error) {
            console.error('更新密码时发生错误:', error);
            alert('更新密码失败，请稍后重试');
        } finally {
            setSaving(false);
        }
    };

    // 注销登录
    const logout = async () => {
        if (confirm('确定要注销登录吗？')) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            router.push('/login');
        }
    };

    if (loading) {
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

    const tabs = [
        {id: 'profile', label: '个人资料', icon: User},
        {id: 'account', label: '账户安全', icon: Shield},
        {id: 'appearance', label: '外观设置', icon: Palette},
        {id: 'notifications', label: '通知设置', icon: Bell},
    ];

    return (
        <WithAuthProtection loadingMessage="正在加载设置页面...">
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
                {/* 头部 */}
                <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
                    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <h1 className="text-3xl font-black text-gray-900 dark:text-white">设置</h1>
                        <p className="text-gray-600 dark:text-gray-400 mt-1">管理你的账户和个人信息</p>
                    </div>
                </header>

                <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="flex flex-col lg:flex-row gap-8">
                        {/* 侧边栏导航 */}
                        <nav className="lg:w-64 flex-shrink-0">
                            <div
                                className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 sticky top-8">
                                <div className="space-y-1">
                                    {tabs.map((tab) => {
                                        const Icon = tab.icon;
                                        return (
                                            <button
                                                key={tab.id}
                                                onClick={() => setActiveTab(tab.id as TabType)}
                                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${
                                                    activeTab === tab.id
                                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                                                }`}
                                            >
                                                <Icon className="w-5 h-5"/>
                                                <span>{tab.label}</span>
                                            </button>
                                        );
                                    })}

                                    <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-800">
                                        <button
                                            onClick={logout}
                                            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                                        >
                                            <LogOut className="w-5 h-5"/>
                                            <span>注销登录</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </nav>

                        {/* 主内容区 */}
                        <main className="flex-1">
                            {/* 个人资料 */}
                            {activeTab === 'profile' && (
                                <motion.div
                                    variants={fadeInUp}
                                    initial="initial"
                                    animate="animate"
                                    className="space-y-6"
                                >
                                    {/* 头像卡片 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">头像</h2>

                                        <div className="flex items-center gap-6">
                                            <div className="relative">
                                                <div
                                                    className="w-24 h-24 rounded-2xl overflow-hidden border-2 border-gray-200 dark:border-gray-700">
                                                    <Image
                                                        src={avatarUrl}
                                                        alt="Avatar"
                                                        width={96}
                                                        height={96}
                                                        className="w-full h-full object-cover"
                                                    />
                                                </div>
                                                <button
                                                    onClick={() => avatarInputRef.current?.click()}
                                                    className="absolute -bottom-2 -right-2 w-8 h-8 bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center justify-center shadow-lg transition-colors"
                                                >
                                                    <Camera className="w-4 h-4"/>
                                                </button>
                                            </div>

                                            <div>
                                                <button
                                                    onClick={() => avatarInputRef.current?.click()}
                                                    className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-xl transition-colors"
                                                >
                                                    <Upload className="w-4 h-4"/>
                                                    更换头像
                                                </button>
                                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                                                    支持 JPG、PNG 或 WEBP，最大 5MB
                                                </p>
                                            </div>

                                            <input
                                                ref={avatarInputRef}
                                                type="file"
                                                accept="image/jpeg,image/png,image/webp"
                                                onChange={handleAvatarChange}
                                                className="hidden"
                                            />
                                        </div>
                                    </div>

                                    {/* 用户名 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">用户名</h2>

                                        <div className="flex gap-4">
                                            <input
                                                type="text"
                                                value={profileForm.username}
                                                onChange={(e) => setProfileForm({
                                                    ...profileForm,
                                                    username: e.target.value
                                                })}
                                                className="flex-1 px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                                placeholder="输入用户名"
                                            />
                                            <button
                                                onClick={updateUsername}
                                                disabled={saving}
                                                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                {saving ? '保存中...' : (
                                                    <>
                                                        <Save className="w-4 h-4"/>
                                                        保存
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </div>

                                    {/* 个人简介 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">个人简介</h2>

                                        <textarea
                                            value={profileForm.bio}
                                            onChange={(e) => setProfileForm({...profileForm, bio: e.target.value})}
                                            rows={4}
                                            className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white resize-none"
                                            placeholder="介绍一下自己..."
                                        />

                                        <div className="flex justify-end mt-4">
                                            <button
                                                onClick={updateBio}
                                                disabled={saving}
                                                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                {saving ? '保存中...' : (
                                                    <>
                                                        <Save className="w-4 h-4"/>
                                                        保存
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </div>

                                    {/* 语言和隐私 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">偏好设置</h2>

                                        <div className="space-y-6">
                                            {/* 语言选择 */}
                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    语言
                                                </label>
                                                <select
                                                    value={profileForm.locale}
                                                    onChange={(e) => {
                                                        setProfileForm({...profileForm, locale: e.target.value});
                                                        setTimeout(updateLocale, 0);
                                                    }}
                                                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                                >
                                                    <option value="zh_CN">简体中文</option>
                                                    <option value="en_US">English</option>
                                                    <option value="ja_JP">日本語</option>
                                                </select>
                                            </div>

                                            {/* 隐私设置 */}
                                            <div
                                                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                                                <div>
                                                    <div
                                                        className="font-medium text-gray-900 dark:text-white">私密账户
                                                    </div>
                                                    <div
                                                        className="text-sm text-gray-500 dark:text-gray-400">开启后，只有关注者可以看到你的内容
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => {
                                                        setProfileForm({
                                                            ...profileForm,
                                                            profilePrivate: !profileForm.profilePrivate
                                                        });
                                                        setTimeout(updatePrivacy, 0);
                                                    }}
                                                    className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                                                        profileForm.profilePrivate ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                                                    }`}
                                                >
                                                    <span
                                                        className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                                                            profileForm.profilePrivate ? 'translate-x-6' : 'translate-x-1'
                                                        }`}
                                                    />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {/* 账户安全 */}
                            {activeTab === 'account' && (
                                <motion.div
                                    variants={fadeInUp}
                                    initial="initial"
                                    animate="animate"
                                    className="space-y-6"
                                >
                                    {/* 修改密码 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">修改密码</h2>
                                        
                                        <div className="space-y-4">
                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    当前密码
                                                </label>
                                                <div className="relative">
                                                    <input
                                                        type={showPassword ? "text" : "password"}
                                                        value={passwordForm.currentPassword}
                                                        onChange={(e) => setPasswordForm({
                                                            ...passwordForm,
                                                            currentPassword: e.target.value
                                                        })}
                                                        className="w-full px-4 py-3 pr-12 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                                        placeholder="输入当前密码"
                                                    />
                                                    <button
                                                        type="button"
                                                        onClick={() => setShowPassword(!showPassword)}
                                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                                    >
                                                        {showPassword ? <EyeOff className="w-5 h-5"/> :
                                                            <Eye className="w-5 h-5"/>}
                                                    </button>
                                                </div>
                                            </div>

                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    新密码
                                                </label>
                                                <input
                                                    type="password"
                                                    value={passwordForm.newPassword}
                                                    onChange={(e) => setPasswordForm({
                                                        ...passwordForm,
                                                        newPassword: e.target.value
                                                    })}
                                                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                                    placeholder="输入新密码（至少6位）"
                                                />
                                            </div>

                                            <div>
                                                <label
                                                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    确认新密码
                                                </label>
                                                <input
                                                    type="password"
                                                    value={passwordForm.confirmPassword}
                                                    onChange={(e) => setPasswordForm({
                                                        ...passwordForm,
                                                        confirmPassword: e.target.value
                                                    })}
                                                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                                                    placeholder="再次输入新密码"
                                                />
                                            </div>

                                            <div className="flex justify-end pt-4">
                                                <button
                                                    onClick={updatePassword}
                                                    disabled={saving}
                                                    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                                                >
                                                    {saving ? '保存中...' : (
                                                        <>
                                                            <Save className="w-4 h-4"/>
                                                            更新密码
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* 邮箱 */}
                                    <div
                                        className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">邮箱地址</h2>
                                                <p className="text-gray-600 dark:text-gray-400">{userProfile?.email || '未设置'}</p>
                                            </div>
                                            <button
                                                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-xl transition-colors">
                                                换绑邮箱
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {/* 外观设置 */}
                            {activeTab === 'appearance' && (
                                <motion.div
                                    variants={fadeInUp}
                                    initial="initial"
                                    animate="animate"
                                    className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8"
                                >
                                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">主题设置</h2>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <button className="p-6 border-2 border-blue-600 rounded-2xl bg-white">
                                            <Sun className="w-8 h-8 text-yellow-500 mx-auto mb-3"/>
                                            <div className="font-medium text-gray-900">浅色模式</div>
                                        </button>
                                        <button
                                            className="p-6 border-2 border-gray-200 dark:border-gray-700 rounded-2xl bg-gray-900">
                                            <Moon className="w-8 h-8 text-blue-400 mx-auto mb-3"/>
                                            <div className="font-medium text-white">深色模式</div>
                                        </button>
                                        <button
                                            className="p-6 border-2 border-gray-200 dark:border-gray-700 rounded-2xl bg-gradient-to-br from-white to-gray-900">
                                            <Smartphone
                                                className="w-8 h-8 text-gray-600 dark:text-gray-400 mx-auto mb-3"/>
                                            <div className="font-medium text-gray-900 dark:text-white">跟随系统</div>
                                        </button>
                                    </div>

                                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-6 text-center">
                                        更多主题设置将在后续版本中提供
                                    </p>
                                </motion.div>
                            )}

                            {/* 通知设置 */}
                            {activeTab === 'notifications' && (
                                <motion.div
                                    variants={fadeInUp}
                                    initial="initial"
                                    animate="animate"
                                    className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-8"
                                >
                                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">通知偏好</h2>

                                    <div className="space-y-4">
                                        {[
                                            {label: '文章评论', desc: '当有人评论你的文章时通知你'},
                                            {label: '新粉丝', desc: '当有人关注你时通知你'},
                                            {label: '点赞提醒', desc: '当有人点赞你的文章时通知你'},
                                            {label: '系统公告', desc: '接收平台重要通知和更新'},
                                        ].map((item, index) => (
                                            <div key={index}
                                                 className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                                                <div>
                                                    <div
                                                        className="font-medium text-gray-900 dark:text-white">{item.label}</div>
                                                    <div
                                                        className="text-sm text-gray-500 dark:text-gray-400">{item.desc}</div>
                                                </div>
                                                <button
                                                    className="relative inline-flex h-7 w-12 items-center rounded-full bg-blue-600">
                                                    <span
                                                        className="inline-block h-5 w-5 transform rounded-full bg-white translate-x-6"/>
                                                </button>
                                            </div>
                                        ))}
                                    </div>

                                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-6 text-center">
                                        通知设置将在后续版本中完善
                                    </p>
                                </motion.div>
                            )}
                        </main>
                    </div>
                </div>

                {/* 底部间距 */}
                <div className="h-20"/>
            </div>
        </WithAuthProtection>
    );
};

export default SettingsPage;
