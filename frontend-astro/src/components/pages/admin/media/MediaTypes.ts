import React from 'react';
import {
  ArrowRightLeft, Ban, CheckCircle2, Clock, Download, FileText, Grid,
  Image, Music, RotateCcw, Upload, Video
} from 'lucide-react';

export type TabKey = 'files' | 'upload-tasks' | 'download-tasks';
export const TABS: { key: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  {key: 'files', label: '媒体文件', icon: Image},
  {key: 'upload-tasks', label: '上传任务', icon: Upload},
  {key: 'download-tasks', label: '下载任务', icon: Download},
];

export interface MediaFileItem {
  id: number;
  original_filename: string;
  mime_type?: string;
  file_size?: number;
  url?: string;
  thumbnail_url?: string;
  folder_path?: string;
  created_at?: string;
  category?: string;
  tags?: string;
}

export interface DownloadTaskItem {
  id: number;
  source_url: string;
  resource_type: string;
  filename: string;
  status: string;
  progress: number;
  total_size?: number;
  downloaded_size?: number;
  error_message?: string;
  media_id?: number;
  retry_count: number;
  created_at?: string;
  completed_at?: string;
}

export interface FolderItem {
  id: number;
  name: string;
  path: string;
  parent_id?: number;
  media_count?: number;
}

export const TYPE_OPTIONS = [
  {value: '', label: '全部', icon: Grid},
  {value: 'images', label: '图片', icon: Image},
  {value: 'videos', label: '视频', icon: Video},
  {value: 'documents', label: '文档', icon: FileText},
  {value: 'audio', label: '音频', icon: Music},
] as const;

export const STATUS_CONFIG: Record<string, {
  label: string;
  color: string;
  icon: React.ComponentType<{ className?: string }>
}> = {
  pending: {
    label: '等待中',
    color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    icon: Clock
  },
  downloading: {
    label: '下载中',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    icon: Download
  },
  completed: {
    label: '已完成',
    color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    icon: CheckCircle2
  },
  failed: {label: '失败', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: Ban},
  cancelled: {label: '已取消', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400', icon: RotateCcw},
  processing: {
    label: '处理中',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    icon: ArrowRightLeft
  },
  initialized: {label: '已初始化', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400', icon: Clock},
};

/* ── 工具函数 ── */
export function getFileType(mime: string): 'image' | 'video' | 'audio' | 'document' {
  if (mime?.startsWith('image/')) return 'image';
  if (mime?.startsWith('video/')) return 'video';
  if (mime?.startsWith('audio/')) return 'audio';
  return 'document';
}

export function getFileColor(type: string) {
  switch (type) {
    case 'image':
      return {bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-600 dark:text-blue-400', dot: 'bg-blue-500'};
    case 'video':
      return {
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        text: 'text-purple-600 dark:text-purple-400',
        dot: 'bg-purple-500'
      };
    case 'audio':
      return {bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500'};
    default:
      return {bg: 'bg-gray-50 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400', dot: 'bg-gray-500'};
  }
}

export function timeAgo(iso: string): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
}

/* ── 骨架屏 ── */
