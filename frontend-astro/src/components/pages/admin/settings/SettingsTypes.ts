import React from 'react';
import {
  Copyright, ExternalLink, FileText, Film, Globe, Hash, Home, Image, Layers,
  Link2, Lock, Mail, Menu, Settings as SettingsIcon, Shield, Type, Zap
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────
export interface SiteMenu {id: number; name: string; slug: string; description: string; is_active: boolean; created_at?: string; updated_at?: string;}
export interface MenuItem {id: number; title: string; url: string; target: string; parent_id: number | null; order_index: number; is_active?: boolean; created_at?: string;}
export interface Page {id: number; title: string; slug: string; content: string; excerpt: string; template: string; status: number; parent_id: number | null; order_index: number; meta_title?: string; meta_description?: string; meta_keywords?: string; created_at?: string;}

// ─── Tab configuration ────────────────────────────────
export const TABS = [
  {
    key: 'basic',
    label: '基本设置',
    icon: SettingsIcon,
    desc: '站点基本信息配置',
    gradient: 'from-blue-500 to-cyan-500'
  },
  {key: 'home', label: '首页配置', icon: Home, desc: '首页展示与布局', gradient: 'from-purple-500 to-pink-500'},
  {key: 'system', label: '系统选项', icon: Shield, desc: '系统功能开关', gradient: 'from-emerald-500 to-teal-500'},
  {key: 'menus', label: '菜单管理', icon: Menu, desc: '导航菜单配置', gradient: 'from-amber-500 to-orange-500'},
  {key: 'pages', label: '页面管理', icon: FileText, desc: '独立页面管理', gradient: 'from-rose-500 to-red-500'},
];

// ─── Settings field registry ──────────────────────────
export interface FieldDef {
  key: string;
  label: string;
  type?: string;
  placeholder?: string;
  category: string;
  options?: { label: string; value: string }[];
  rows?: number;
  icon?: any;
  desc?: string;
}
export const SETTINGS_FIELDS: FieldDef[] = [
  // basic
  {
    key: 'site_title',
    label: '站点标题',
    category: 'basic',
    placeholder: 'FastBlog',
    icon: Type,
    desc: '显示在浏览器标签和搜索引擎结果中'
  },
  {
    key: 'site_description',
    label: '站点描述',
    category: 'basic',
    type: 'textarea',
    rows: 2,
    placeholder: '一个快速的博客系统',
    icon: FileText,
    desc: '用于SEO和社交分享'
  },
  {
    key: 'site_domain',
    label: '站点域名',
    category: 'basic',
    placeholder: 'example.com',
    icon: Globe,
    desc: '当前站点的访问域名'
  },
  {
    key: 'site_img',
    label: '站点Logo URL',
    category: 'basic',
    placeholder: 'https://...',
    icon: Image,
    desc: '站点Logo图片地址'
  },
  {
    key: 'site_beian',
    label: '备案号',
    category: 'basic',
    placeholder: '京ICP备...',
    icon: Shield,
    desc: 'ICP备案号（如适用）'
  },
  {
    key: 'site_keywords',
    label: '站点关键词',
    category: 'basic',
    placeholder: '博客, 技术, ...',
    icon: Hash,
    desc: '用于SEO优化，逗号分隔'
  },
  {
    key: 'site_icon',
    label: '站点图标 (Favicon)',
    category: 'basic',
    type: 'media',
    placeholder: 'https://... 或上传图片',
    icon: Image,
    desc: '浏览器标签和书签中显示的图标，推荐 32x32px'
  },
  {
    key: 'copyright',
    label: '版权信息',
    category: 'basic',
    type: 'textarea',
    rows: 2,
    placeholder: '© 2026 FastBlog. All rights reserved.',
    icon: Copyright,
    desc: '显示在页脚的版权文字'
  },
  {
    key: 'footer_menu_slug',
    label: '页脚菜单',
    category: 'basic',
    placeholder: 'footer',
    icon: Menu,
    desc: '指定页脚导航使用的菜单标识'
  },
  // home
  {key: 'home_hero_title', label: 'Hero 标题', category: 'home', placeholder: '欢迎来到我的博客', icon: Type},
  {key: 'home_hero_subtitle', label: 'Hero 副标题', category: 'home', placeholder: '分享知识与见解', icon: FileText},
  {key: 'home_hero_cta_text', label: 'CTA 按钮文本', category: 'home', placeholder: '开始阅读', icon: Zap},
  {key: 'home_hero_cta_link', label: 'CTA 按钮链接', category: 'home', placeholder: '/articles', icon: Link2},
  {
    key: 'home_cta_target',
    label: 'CTA 跳转方式',
    type: 'select',
    category: 'home',
    options: [{label: '当前窗口', value: '_self'}, {label: '新窗口', value: '_blank'}],
    icon: ExternalLink
  },
  {
    key: 'home_hero_background_image',
    label: 'Hero 背景媒体',
    type: 'media',
    category: 'home',
    placeholder: '输入媒体 URL 或上传图片/视频',
    icon: Film
  },
  {key: 'home_featured_title', label: '精选区域标题', category: 'home', placeholder: '精选文章', icon: Layers},
  {key: 'home_main_title', label: '主内容区标题', category: 'home', placeholder: '最新文章', icon: Type},
  {key: 'home_newsletter_title', label: '订阅区标题', category: 'home', placeholder: '订阅更新', icon: Mail},
  {
    key: 'home_newsletter_subtitle',
    label: '订阅区副标题',
    category: 'home',
    placeholder: '获取最新文章推送',
    icon: Mail
  },
  {key: 'home_newsletter_button_text', label: '订阅按钮文本', category: 'home', placeholder: '订阅', icon: Zap},
  {key: 'home_no_summary_msg', label: '无摘要消息', category: 'home', placeholder: '暂无摘要', icon: FileText},
  // system
  {
    key: 'user_registration',
    label: '允许用户注册',
    category: 'system',
    type: 'select',
    options: [{label: '开启', value: 'true'}, {label: '关闭', value: 'false'}],
    icon: Shield,
    desc: '控制是否允许新用户注册'
  },
  {
    key: 'menu_slug',
    label: '当前使用菜单标识',
    category: 'system',
    placeholder: 'main',
    icon: Menu,
    desc: '指定前台导航使用的菜单'
  },
];
