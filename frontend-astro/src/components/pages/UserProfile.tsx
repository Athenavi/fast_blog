'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api';
import {motion} from 'framer-motion';
import {
  Calendar, Edit3, Eye, FileText, Heart, Link as LinkIcon, Lock, Mail, MapPin, Settings, UserPlus, Users
} from 'lucide-react';

const fadeInUp = {initial: {opacity:0,y:20}, animate: {opacity:1,y:0}, transition: {duration:0.5}};
const staggerContainer = {animate: {transition: {staggerChildren:0.1}}};

interface ArticleItem { id: number; title: string; slug: string; excerpt?: string; cover_image?: string; views: number; likes: number; created_at: string; tags?: string[]; }
interface UserData { id: number; username: string; display_name?: string; email: string; bio?: string; location?: string; website?: string; locale?: string; avatar?: string; avatar_url?: string; profile_private: boolean; created_at: string; }
interface ProfileResponse { user: UserData; recent_articles?: ArticleItem[]; stats?: { articles_count: number; followers_count: number; following_count: number; }; }

const UserProfile: React.FC = () => {
  const [data, setData] = useState<ProfileResponse|null>(null);
  const [loading, setLoading] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [tab, setTab] = useState<'articles'|'about'>('articles');

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.get<ProfileResponse>('/users/me');
        if (!res.success || !res.data) return;
        const p = res.data;
        const u = p.user;
        setData(p);
        let av = u.avatar_url || u.avatar || '';
        if (av && !av.startsWith('http')) {
          const config = await import('@/lib/config').then(m => m.getConfig());
          av = av.startsWith('/') ? `${config.API_BASE_URL}${av}` : `${config.API_BASE_URL}/static/avatar/${av}.png`;
        }
        setAvatarUrl(av || `https://ui-avatars.com/api/?name=${encodeURIComponent(u.username||'User')}&background=random`);
      } catch {} finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"/></div>;
  if (!data) return <div className="min-h-screen flex items-center justify-center text-gray-500">请先登录</div>;

  const u = data.user;
  const articles = data.recent_articles || [];
  const stats = data.stats || {articles_count:0, followers_count:0, following_count:0};

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-16">
      {/* Cover */}
      <div className="relative h-64 bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600 overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2"/>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl translate-x-1/2 translate-y-1/2"/>
        </div>
        <div className="absolute inset-0 opacity-10" style={{backgroundImage:'radial-gradient(circle at 1px 1px, white 1px, transparent 0)', backgroundSize:'40px 40px'}}/>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 -mt-32 relative z-10">
        {/* Profile card */}
        <motion.div variants={fadeInUp} initial="initial" animate="animate"
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 p-8 mb-8">
          <div className="flex flex-col lg:flex-row gap-8">
            <div className="flex-shrink-0">
              <div className="relative">
                <div className="w-32 h-32 rounded-2xl overflow-hidden border-4 border-white dark:border-gray-900 shadow-lg">
                  <img src={avatarUrl} alt={u.username} className="w-full h-full object-cover"
                    onError={e => {(e.target as HTMLImageElement).src=`https://ui-avatars.com/api/?name=${encodeURIComponent(u.username||'U')}&background=random`}} />
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 border-4 border-white dark:border-gray-900 rounded-full"/>
              </div>
            </div>

            <div className="flex-1">
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-1">{u.display_name || u.username}</h1>
                  <p className="text-lg text-gray-500 dark:text-gray-400 mb-4">@{u.username}</p>
                  {u.bio && <p className="text-gray-700 dark:text-gray-300 mb-4 max-w-2xl">{u.bio}</p>}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    {u.location && <span className="flex items-center gap-1.5"><MapPin className="w-4 h-4"/>{u.location}</span>}
                    {u.website && <span className="flex items-center gap-1.5"><LinkIcon className="w-4 h-4"/><a href={u.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">{u.website.replace(/^https?:\/\//,'')}</a></span>}
                    <span className="flex items-center gap-1.5"><Calendar className="w-4 h-4"/>加入于 {u.created_at ? new Date(u.created_at).toLocaleDateString('zh-CN',{year:'numeric',month:'long'}) : ''}</span>
                  </div>
                </div>
                <div className="flex gap-3">
                  <a href="/settings" className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-xl transition-colors"><Settings className="w-4 h-4"/><span className="hidden sm:inline">编辑资料</span></a>
                  <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"><UserPlus className="w-4 h-4"/><span className="hidden sm:inline">关注</span></button>
                </div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-8 border-t border-gray-200 dark:border-gray-800">
            <div className="text-center"><div className="text-3xl font-black text-gray-900 dark:text-white">{stats.articles_count}</div><div className="text-sm text-gray-500 mt-1">文章</div></div>
            <div className="text-center"><div className="text-3xl font-black text-gray-900 dark:text-white">{stats.followers_count}</div><div className="text-sm text-gray-500 mt-1">粉丝</div></div>
            <div className="text-center"><div className="text-3xl font-black text-gray-900 dark:text-white">{stats.following_count}</div><div className="text-sm text-gray-500 mt-1">关注</div></div>
            <div className="text-center"><div className="text-3xl font-black text-gray-900 dark:text-white">{articles.reduce((s,a)=>s+(a.views||0),0)}</div><div className="text-sm text-gray-500 mt-1">总浏览</div></div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 mb-8">
          <div className="flex border-b border-gray-200 dark:border-gray-800">
            {(['articles','about'] as const).map(t => (
              <button key={t} onClick={()=>setTab(t)}
                className={`flex-1 px-6 py-4 font-medium transition-colors ${tab===t ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}`}>
                <div className="flex items-center justify-center gap-2">
                  {t==='articles' ? <FileText className="w-5 h-5"/> : <Users className="w-5 h-5"/>}
                  <span>{t==='articles' ? '文章' : '关于'}</span>
                  <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded-full text-xs">{(t==='articles' ? articles : 1).length}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Articles tab */}
        {tab === 'articles' && (
          <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-4">
            {articles.length > 0 ? articles.map((article,i) => (
              <motion.a key={article.id} variants={fadeInUp} href={`/articles/${article.slug}`}
                className="block group bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-all hover:shadow-lg">
                <div className="p-6"><div className="flex gap-6">
                  {article.cover_image && <div className="hidden sm:block relative w-40 h-28 flex-shrink-0 rounded-xl overflow-hidden"><img src={article.cover_image} alt={article.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"/></div>}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">{article.title}</h3>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">{article.excerpt||'暂无摘要'}</p>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1.5"><Calendar className="w-4 h-4"/>{article.created_at ? new Date(article.created_at).toLocaleDateString('zh-CN') : ''}</span>
                      <span className="flex items-center gap-1.5"><Eye className="w-4 h-4"/>{article.views||0}</span>
                      <span className="flex items-center gap-1.5"><Heart className="w-4 h-4"/>{article.likes||0}</span>
                    </div>
                    {article.tags && article.tags.length > 0 && <div className="flex flex-wrap gap-2 mt-4">{article.tags.slice(0,3).map(t=><span key={t} className="px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs font-medium rounded-full">#{t}</span>)}{article.tags.length>3 && <span className="text-xs text-gray-400">+{article.tags.length-3}</span>}</div>}
                  </div>
                </div></div>
              </motion.a>
            )) : (
              <motion.div variants={fadeInUp} className="bg-white dark:bg-gray-900 rounded-2xl border p-12 text-center">
                <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">暂无文章</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">开始创作你的第一篇文章吧</p>
                <a href="/admin/editor" className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"><Edit3 className="w-5 h-5"/>创建文章</a>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* About tab */}
        {tab === 'about' && (
          <motion.div variants={fadeInUp} initial="initial" animate="animate" className="bg-white dark:bg-gray-900 rounded-2xl border p-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">个人信息</h2>
            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-blue-50 dark:bg-blue-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
                </div>
                <div className="flex-1"><div className="text-sm text-gray-500 dark:text-gray-400 mb-1">邮箱</div><div className="text-gray-900 dark:text-white">{u.email}</div></div>
              </div>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-purple-50 dark:bg-purple-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-purple-600 dark:text-purple-400"/>
                </div>
                <div className="flex-1"><div className="text-sm text-gray-500 dark:text-gray-400 mb-1">位置</div><div className="text-gray-900 dark:text-white">{u.location||'未设置'}</div></div>
              </div>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-green-50 dark:bg-green-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <LinkIcon className="w-5 h-5 text-green-600 dark:text-green-400"/>
                </div>
                <div className="flex-1"><div className="text-sm text-gray-500 dark:text-gray-400 mb-1">网站</div>
                  {u.website ? <a href={u.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">{u.website}</a> :
                  <div className="text-gray-900 dark:text-white">未设置</div>}
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-orange-50 dark:bg-orange-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Lock className="w-5 h-5 text-orange-600 dark:text-orange-400"/>
                </div>
                <div className="flex-1"><div className="text-sm text-gray-500 dark:text-gray-400 mb-1">隐私设置</div><div className="text-gray-900 dark:text-white">{u.profile_private?'私密账户':'公开账户'}</div></div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
      <div className="h-20"/>
    </div>
  );
};

export default UserProfile;
