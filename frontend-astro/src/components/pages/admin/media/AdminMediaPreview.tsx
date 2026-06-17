'use client';

import React, { useEffect, useMemo } from 'react';
import FsLightbox from 'fslightbox-react';
import FileViewer from '@flyfish-group/file-viewer-react';
import type { MediaFileItem } from './MediaTypes';
import { getFullMediaUrl, formatBytes } from '@/lib/utils';
import {
  X,
  ChevronLeft,
  ChevronRight,
  Edit3,
  ExternalLink,
  Image as ImageIcon,
  Music,
  Video,
  FileText,
} from 'lucide-react';

interface AdminMediaPreviewProps {
  files: MediaFileItem[];
  activeFile: MediaFileItem;
  onClose: () => void;
  onNavigate?: (file: MediaFileItem) => void;
  onEdit?: (file: MediaFileItem) => void;
}

function getTypeIcon(mime: string) {
  if (mime.startsWith('image/')) return ImageIcon;
  if (mime.startsWith('video/')) return Video;
  if (mime.startsWith('audio/')) return Music;
  return FileText;
}

/**
 * AdminMediaPreview — 后台全类型预览组件
 *
 * - image/* → FsLightbox 全屏画廊
 * - 其他 → FileViewer 模态框（含底部缩略图导航）
 * - 图片额外提供 "编辑" 入口跳转 ImageEditorModal
 */
export function AdminMediaPreview({
  files,
  activeFile,
  onClose,
  onNavigate,
  onEdit,
}: AdminMediaPreviewProps) {
  const mime = activeFile?.mime_type || '';
  const isImage = mime.startsWith('image/');
  const isVideo = mime.startsWith('video/');
  const isAudio = mime.startsWith('audio/');
  const fullUrl = getFullMediaUrl(activeFile?.url);
  const currentIndex = files.findIndex((f) => f.id === activeFile?.id);
  const prevFile = currentIndex > 0 ? files[currentIndex - 1] : null;
  const nextFile =
    currentIndex < files.length - 1 ? files[currentIndex + 1] : null;

  // ESC 关闭
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // ← → 导航
  useEffect(() => {
    if (!onNavigate) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && prevFile) onNavigate(prevFile);
      if (e.key === 'ArrowRight' && nextFile) onNavigate(nextFile);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onNavigate, prevFile, nextFile]);

  // ── 图片：FsLightbox ──
  if (isImage) {
    const imageFiles = files.filter((f) =>
      f.mime_type?.startsWith('image/'),
    );
    const sources = imageFiles.map((f) =>
      getFullMediaUrl(f.thumbnail_url || f.url),
    );
    const srcIndex = imageFiles.findIndex((f) => f.id === activeFile.id);

    return (
      <FsLightbox
        key={`admin-image-${activeFile.id}`}
        openOnMount
        toggler={false}
        sources={sources}
        sourceIndex={Math.max(0, srcIndex)}
        onClose={onClose}
      />
    );
  }

  // ── 非图片：FileViewer 模态框 ──
  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 flex flex-col"
      onClick={onClose}
    >
      {/* 顶部信息栏 */}
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-black/50 backdrop-blur-sm flex-shrink-0 border-b border-white/5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 min-w-0">
          {React.createElement(getTypeIcon(mime), {
            className: 'w-4 h-4 text-white/50 flex-shrink-0',
          })}
          <span className="text-white/90 text-sm font-medium truncate max-w-xs sm:max-w-md">
            {activeFile.original_filename}
          </span>
          {files.length > 1 && (
            <span className="text-white/40 text-xs flex-shrink-0 hidden sm:inline">
              {currentIndex + 1} / {files.length}
            </span>
          )}
          <span className="text-white/30 text-[10px] flex-shrink-0 bg-white/10 px-1.5 py-0.5 rounded hidden sm:inline">
            {mime}
          </span>
          {activeFile.file_size ? (
            <span className="text-white/30 text-xs flex-shrink-0 hidden md:inline">
              {formatBytes(activeFile.file_size)}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-1">
          {/* 编辑图片按钮 — 仅图片类型 */}
          {isImage && onEdit && (
            <button
              onClick={() => onEdit(activeFile)}
              className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/80 transition-colors"
              title="编辑图片"
            >
              <Edit3 className="w-4 h-4" />
            </button>
          )}
          {/* 复制链接 */}
          <button
            onClick={() => navigator.clipboard.writeText(fullUrl)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/80 transition-colors"
            title="复制文件链接"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          {/* 关闭 */}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
            title="关闭 (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 预览内容区 */}
      <div
        className="flex-1 flex items-center justify-center min-h-0 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {prevFile && onNavigate && (
          <button
            onClick={() => onNavigate(prevFile)}
            className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-black/40 hover:bg-black/60 text-white/60 hover:text-white transition-all opacity-0 hover:opacity-100"
            title="上一个 (←)"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}

        <div className="w-full h-full">
          <FileViewer
            url={fullUrl}
            options={{
              theme: 'dark',
              toolbar: { position: 'bottom-right' },
            }}
          />
        </div>

        {nextFile && onNavigate && (
          <button
            onClick={() => onNavigate(nextFile)}
            className="absolute right-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-black/40 hover:bg-black/60 text-white/60 hover:text-white transition-all opacity-0 hover:opacity-100"
            title="下一个 (→)"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        )}
      </div>

      {/* 底部缩略图导航 */}
      {files.length > 1 && (
        <div
          className="h-16 sm:h-20 bg-black/40 backdrop-blur-sm border-t border-white/5 flex-shrink-0 flex items-center px-3 gap-2 overflow-x-auto"
          onClick={(e) => e.stopPropagation()}
          style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}
        >
          {files.map((f) => {
            const isActive = f.id === activeFile.id;
            const fMime = f.mime_type || '';
            const isImg = fMime.startsWith('image/');
            const thumbSrc =
              isImg && f.thumbnail_url
                ? getFullMediaUrl(f.thumbnail_url)
                : null;

            return (
              <button
                key={f.id}
                onClick={() => onNavigate?.(f)}
                className={`flex-shrink-0 w-12 h-10 sm:w-16 sm:h-14 rounded-lg overflow-hidden border-2 transition-all ${
                  isActive
                    ? 'border-blue-500 ring-2 ring-blue-500/30 scale-105'
                    : 'border-white/10 hover:border-white/30 opacity-50 hover:opacity-90'
                }`}
                title={f.original_filename}
              >
                {thumbSrc ? (
                  <img
                    src={thumbSrc}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-white/5">
                    {React.createElement(getTypeIcon(fMime), {
                      className: 'w-4 h-4 sm:w-5 sm:h-5 text-white/30',
                    })}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
