'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import type {MediaFile, MediaResponse} from '@/lib/api';
import {apiClient, MediaService} from '@/lib/api';
import {AuthGuard} from '@/components/AuthGuard';
import {motion} from 'framer-motion';
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderClosed,
  FolderOpen,
  Grid3X3,
  Image as ImageIcon,
  List,
  Music,
  Plus,
  Trash2,
  Upload,
  Video,
  X
} from 'lucide-react';
import {getConfig} from '@/lib/config';

// Helper function to build full media URL
const getFullMediaUrl = (url: string | null | undefined): string => {
  if (!url) return '';
  // If already absolute URL, return as is
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  // Otherwise, prepend API base URL
  const config = getConfig();
  return `${config.API_BASE_URL}${url}`;
};

/* ---------- Shared icons ---------- */
const Minus: React.FC<{className?: string}> = p => <svg className={p.className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4"/></svg>;
const File: React.FC<{className?: string}> = p => <svg className={p.className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>;

/* ---------- FolderTree ---------- */
interface FolderNode {
  id: number; name: string; children?: FolderNode[];
}

const FolderTree: React.FC<{
  folders: FolderNode[]; selectedId: number | null; onSelect: (f: FolderNode | null) => void;
  onCreate: () => void; onDelete: (id: number) => void; loading: boolean;
}> = ({folders, selectedId, onSelect, onCreate, onDelete, loading}) => {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) => {
    const s = new Set(expanded);
    s.has(id) ? s.delete(id) : s.add(id);
    setExpanded(s);
  };

  const renderNode = (node: FolderNode, depth: number = 0) => (
    <div key={node.id}>
      <div className={`group flex items-center gap-1 px-2 py-1.5 rounded-lg cursor-pointer text-sm transition-colors ${
        selectedId === node.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
      }`} style={{paddingLeft: `${12 + depth * 16}px`}}>
        <button onClick={() => toggle(node.id)} className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
          {node.children?.length ? (expanded.has(node.id) ? <ChevronDown className="w-3.5 h-3.5"/> : <ChevronRight className="w-3.5 h-3.5"/>) : <span className="w-3.5"/>}
        </button>
        <div className="flex-1 flex items-center gap-1.5" onClick={() => onSelect(node)}>
          {expanded.has(node.id) ? <FolderOpen className="w-4 h-4 text-yellow-500"/> : <FolderClosed className="w-4 h-4 text-yellow-600"/>}
          <span className="truncate">{node.name}</span>
        </div>
        <button onClick={e => {e.stopPropagation(); onDelete(node.id);}} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-gray-400 hover:text-red-500"><X className="w-3 h-3"/></button>
      </div>
      {expanded.has(node.id) && node.children?.map(child => renderNode(child, depth + 1))}
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">文件夹</h3>
        <button onClick={onCreate} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-400 hover:text-blue-600"><Plus className="w-4 h-4"/></button>
      </div>
      {loading ? (
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <div className="space-y-0.5">
          <div onClick={() => onSelect(null)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer text-sm transition-colors ${selectedId === null ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
            <Grid3X3 className="w-4 h-4"/><span>全部文件</span>
          </div>
          {folders.map(n => renderNode(n))}
        </div>
      )}
    </div>
  );
};

/* ---------- StorageStats ---------- */
const StorageStats: React.FC<{ stats: any; loading: boolean }> = ({stats, loading}) => {
  const items = [
    {label: '图片', count: stats.image_count || 0, color: 'from-blue-500 to-cyan-500', icon: ImageIcon},
    {label: '视频', count: stats.video_count || 0, color: 'from-purple-500 to-pink-500', icon: Video},
    {label: '已用空间', count: stats.storage_used || '0 MB', color: 'from-green-500 to-emerald-500', icon: Upload},
  ];
  return (<div className="space-y-3">
    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">存储</h3>
    {items.map(item => {const Icon = item.icon; return (
      <div key={item.label} className={`p-4 rounded-xl bg-gradient-to-br ${item.color} text-white`}>
        <div className="flex items-center gap-2 text-sm opacity-80"><Icon className="w-4 h-4"/>{item.label}</div>
        <p className="text-xl font-bold mt-1">{loading ? '...' : item.count}</p>
      </div>
    );})}
    {!loading && stats.storage_percentage !== undefined && (<div><div className="flex justify-between text-xs text-gray-500 mb-1"><span>存储</span><span>{stats.storage_percentage}%</span></div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2"><div className="bg-blue-600 h-2 rounded-full" style={{width: `${stats.storage_percentage}%`}}/></div></div>)}
  </div>);
};

/* ---------- UploadArea ---------- */
const UploadArea: React.FC<{onUpload: (files: File[]) => void; uploading: boolean; progress: number; status: string; collapsed: boolean; onToggle: () => void}> = ({onUpload, uploading, progress, status, collapsed, onToggle}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  return (<div className="mb-6">
    <button onClick={onToggle} className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
      {collapsed ? <ChevronRight className="w-4 h-4"/> : <ChevronDown className="w-4 h-4"/>} 上传文件
    </button>
    {!collapsed && (<div onDragOver={e => {e.preventDefault(); setDragOver(true);}} onDragLeave={() => setDragOver(false)} onDrop={e => {e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) onUpload(Array.from(e.dataTransfer.files));}}
      className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors cursor-pointer ${dragOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700 hover:border-blue-400'}`}
      onClick={() => inputRef.current?.click()}>
      <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3"/>
      <p className="text-gray-600 dark:text-gray-400 font-medium">{uploading ? '上传中...' : '拖拽文件到此处或点击上传'}</p>
      <input ref={inputRef} type="file" multiple onChange={e => {if (e.target.files?.length) onUpload(Array.from(e.target.files));}} className="hidden"/>
      {uploading && <div className="mt-4"><div className="w-full bg-gray-200 rounded-full h-2"><div className="bg-blue-600 h-2 rounded-full transition-all" style={{width: `${progress}%`}}/></div><p className="text-sm text-gray-500 mt-1">{status}</p></div>}
    </div>)}
  </div>);
};

/* ---------- MediaGrid ---------- */
const MediaGrid: React.FC<{files: MediaFile[]; loading: boolean; viewMode: 'grid'|'list'; selected: number[]; onSelect: (id: number) => void; onPreview: (m: MediaFile) => void; onDelete: (m: MediaFile) => void}> = ({files, loading, viewMode, selected, onSelect, onPreview, onDelete}) => {
  if (loading) return <div className="p-12 text-center"><div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"/></div>;
  if (!files.length) return <div className="p-12 text-center text-gray-400"><ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-50"/><p>暂无媒体文件</p></div>;
  const getIcon = (m: string) => m?.startsWith('video/') ? Video : m?.startsWith('audio/') ? Music : FileText;

  // List View
  if (viewMode === 'list') return (<div className="bg-white dark:bg-gray-900 rounded-xl border overflow-hidden"><table className="w-full"><thead className="bg-gray-50 dark:bg-gray-800"><tr><th className="w-10 px-4 py-3"/><th className="text-left text-sm font-medium text-gray-500 py-3">文件</th><th className="text-left text-sm font-medium text-gray-500 py-3 hidden sm:table-cell">类型</th><th className="text-right text-sm font-medium text-gray-500 py-3 pr-4">操作</th></tr></thead><tbody className="divide-y">
  {files.map(f => {
    const isPDF = f.mime_type === 'application/pdf';
    const Icon = f.mime_type?.startsWith('image/') ? ImageIcon : getIcon(f.mime_type || '');
    return (
      <tr key={f.id} className={`hover:bg-gray-50 dark:hover:bg-gray-800 ${selected.includes(f.id)?'bg-blue-50 dark:bg-blue-900/20':''}`}>
        <td className="px-4"><input type="checkbox" checked={selected.includes(f.id)} onChange={() => onSelect(f.id)} className="h-4 w-4 text-blue-600 rounded"/></td>
        <td className="py-3 cursor-pointer" onClick={() => onPreview(f)}><div className="flex items-center gap-3">
          {f.mime_type?.startsWith('image/') && f.url ? (
              <img
                  src={getFullMediaUrl(f.url)}
                  alt={f.original_filename}
                  className="w-10 h-10 rounded-lg object-cover"
                  loading="lazy"
                  decoding="async"
              />
          ) : f.mime_type?.startsWith('video/') && f.url ? (
                  <div className="w-10 h-10 rounded-lg bg-gray-900 flex items-center justify-center relative">
                    <Video className="w-5 h-5 text-white"/>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-4 h-4 bg-white/80 rounded-full flex items-center justify-center">
                        <div
                            className="w-0 h-0 border-t-[3px] border-t-transparent border-l-[6px] border-l-black border-b-[3px] border-b-transparent ml-0.5"/>
                      </div>
                    </div>
                  </div>
          ) : isPDF ? (
                  // PDF 特殊图标
                  <div className="w-10 h-10 rounded-lg bg-red-50 dark:bg-red-900/10 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-red-500"/>
                  </div>
              ) :
              <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center"><Icon
                  className="w-5 h-5 text-gray-400"/></div>}
          <div><p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{f.original_filename}</p><p className="text-xs text-gray-500">{f.file_size ? `${(f.file_size/1024).toFixed(1)} KB` : ''}</p></div>
        </div></td>
        <td className="text-sm text-gray-500 hidden sm:table-cell">{f.mime_type?.split('/')[0]||'-'}</td>
        <td className="pr-4 text-right"><button onClick={() => onDelete(f)} className="p-1 text-gray-400 hover:text-red-500"><Trash2 className="w-4 h-4"/></button></td>
      </tr>
    );})}</tbody></table></div>);

  // Grid View
  return (<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
    {files.map(f => {
      const isVideo = f.mime_type?.startsWith('video/');
      const isImage = f.mime_type?.startsWith('image/');
      const isPDF = f.mime_type === 'application/pdf';
      const isAudio = f.mime_type?.startsWith('audio/');
      const Icon = getIcon(f.mime_type || '');

      return (
          <div key={f.id}
               className={`relative group aspect-square rounded-xl overflow-hidden border ${selected.includes(f.id) ? 'border-blue-500 ring-2 ring-blue-500' : 'border-gray-200 dark:border-gray-700'} bg-gray-50 dark:bg-gray-800`}>
      <input type="checkbox" checked={selected.includes(f.id)} onChange={() => onSelect(f.id)} className="absolute top-2 left-2 z-10 h-4 w-4 text-blue-600 rounded"/>
            {isImage && f.url ? (
                <img
                    src={getFullMediaUrl(f.url)}
                    alt={f.original_filename}
                    className="w-full h-full object-cover cursor-pointer"
                    onClick={() => onPreview(f)}
                    loading="lazy"
                    decoding="async"
                />
            ) : isVideo && f.url ? (
                    <div className="w-full h-full relative cursor-pointer bg-gray-900" onClick={() => onPreview(f)}>
                      {/* 视频缩略图 - 只加载元数据和首帧 */}
                      <video
                          src={getFullMediaUrl(f.url)}
                          className="w-full h-full object-cover"
                          preload="metadata"
                          muted
                          playsInline
                      />
                      {/* 播放按钮覆盖层 */}
                      <div
                          className="absolute inset-0 bg-black/30 flex items-center justify-center group-hover:bg-black/40 transition-colors">
                        <div
                            className="w-12 h-12 bg-white/90 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                          <div
                              className="w-0 h-0 border-t-[8px] border-t-transparent border-l-[14px] border-l-black border-b-[8px] border-b-transparent ml-1"/>
                        </div>
                      </div>
                    </div>
            ) : isPDF ? (
                    // PDF 文件显示特殊图标
                    <div
                        className="w-full h-full flex flex-col items-center justify-center cursor-pointer bg-red-50 dark:bg-red-900/10"
                        onClick={() => onPreview(f)}>
                      <FileText className="w-12 h-12 text-red-500 mb-2"/>
                      <span className="text-xs text-red-600 dark:text-red-400 font-medium">PDF</span>
                    </div>
            ) : isAudio ? (
                    // 音频文件显示特殊图标
                    <div
                        className="w-full h-full flex flex-col items-center justify-center cursor-pointer bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/10 dark:to-pink-900/10"
                        onClick={() => onPreview(f)}>
                      <Music className="w-12 h-12 text-purple-500 mb-2"/>
                      <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">AUDIO</span>
                    </div>
                ) :
                <div className="w-full h-full flex items-center justify-center cursor-pointer"
                     onClick={() => onPreview(f)}>{React.createElement(Icon, {className: 'w-10 h-10 text-gray-400'})}</div>}
      <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"><p className="text-xs text-white truncate">{f.original_filename}</p></div>
      <button onClick={() => onDelete(f)} className="absolute top-2 right-2 z-10 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100"><X className="w-3 h-3"/></button>
          </div>
      );
    })}
  </div>);
};

/* ---------- Audio Player with Vinyl Animation & Karaoke Lyrics ---------- */

// 将歌词行拆分为逐字/逐词 token（中文按字，英文按单词）
function tokenizeText(text: string): string[] {
  const tokens: string[] = [];
  let buf = '';
  for (const ch of text) {
    const isCJK = /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/.test(ch);
    if (isCJK) {
      if (buf) { tokens.push(buf); buf = ''; }
      tokens.push(ch);
    } else if (ch === ' ') {
      if (buf) { tokens.push(buf); buf = ''; }
      tokens.push(' ');
    } else {
      buf += ch;
    }
  }
  if (buf) tokens.push(buf);
  return tokens;
}

// 计算当前行的逐字高亮进度 (0..1)
function calcKaraokeProgress(
  currentTime: number,
  lineStart: number,
  nextLineStart: number | null,
): number {
  const end = nextLineStart ?? lineStart + 3;
  const duration = end - lineStart;
  if (duration <= 0) return 1;
  return Math.max(0, Math.min(1, (currentTime - lineStart) / duration));
}

const AudioPlayer: React.FC<{ media: MediaFile; fullUrl: string }> = ({media, fullUrl}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showLyrics, setShowLyrics] = useState(false);
  const lyricsContainerRef = useRef<HTMLDivElement>(null);
  const vinylRef = useRef<HTMLDivElement>(null);

  // 音频元数据
  const [coverImage, setCoverImage] = useState<string | null>(null);
  const [lyrics, setLyrics] = useState<Array<{ time: number; text: string }>>([]);
  const [loadingMetadata, setLoadingMetadata] = useState(true);

  // 当前高亮行索引
  const activeLineIndex = lyrics.findIndex((l, i) => {
    const next = lyrics[i + 1];
    return currentTime >= l.time && (!next || currentTime < next.time);
  });

  // 当前行的逐字进度
  const activeLine = activeLineIndex !== -1 ? lyrics[activeLineIndex] : null;
  const karaokeProgress = activeLine
    ? calcKaraokeProgress(
        currentTime,
        activeLine.time,
        lyrics[activeLineIndex + 1]?.time ?? null,
      )
    : 0;

  // 加载音频元数据
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        setLoadingMetadata(true);
        const response = await fetch(`${getConfig().API_BASE_URL}/api/v2/media/${media.id}/metadata`, {
          credentials: 'include'
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success && result.data) {
            if (result.data.cover_image) {
              setCoverImage(result.data.cover_image);
            }
            if (result.data.lyrics && result.data.lyrics.length > 0) {
              setLyrics(result.data.lyrics);
              setShowLyrics(true);
            }
          }
        }
      } catch (error) {
        console.error('加载音频元数据失败:', error);
      } finally {
        setLoadingMetadata(false);
      }
    };

    loadMetadata();
  }, [media.id]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const onEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', onEnded);
    };
  }, []);

  // 歌词自动滚动
  useEffect(() => {
    if (!showLyrics || !lyricsContainerRef.current || activeLineIndex === -1) return;
    const container = lyricsContainerRef.current;
    const el = container.children[activeLineIndex] as HTMLElement | undefined;
    if (el) {
      const target = el.offsetTop - container.clientHeight / 2 + el.clientHeight / 2;
      container.scrollTo({top: target, behavior: 'smooth'});
    }
  }, [activeLineIndex, showLyrics]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const time = parseFloat(e.target.value);
    audio.currentTime = time;
    setCurrentTime(time);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const vol = parseFloat(e.target.value);
    audio.volume = vol;
    setVolume(vol);
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
      <div className="flex flex-col lg:flex-row h-full">
        {/* Left: Vinyl Record Animation (Framer Motion) */}
        <div className="flex-1 bg-gradient-to-br from-gray-900 via-purple-900 to-black p-8 flex items-center justify-center relative overflow-hidden">
          {/* Background glow — pulsing with play state */}
          <motion.div
              className="absolute inset-0"
              animate={{opacity: isPlaying ? 0.35 : 0.08}}
              transition={{duration: 1}}
          >
            <motion.div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full blur-3xl"
                style={{background: 'radial-gradient(circle, rgba(147,51,234,0.6), rgba(236,72,153,0.3))'}}
                animate={isPlaying ? {
                  scale: [1, 1.15, 1],
                  opacity: [0.4, 0.7, 0.4],
                } : {scale: 1, opacity: 0.3}}
                transition={isPlaying ? {
                  duration: 2.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                } : {duration: 0.5}}
            />
          </motion.div>

          {/* Vinyl Record */}
          <div className="relative">
            {/* 唱臂 (Tone arm) — 播放时摆入，暂停时摆出 */}
            <motion.div
                className="absolute -top-6 -right-6 z-10 origin-bottom-left"
                style={{transformOrigin: 'left 100%'}}
                animate={{rotate: isPlaying ? 15 : -30}}
                transition={{type: 'spring', stiffness: 100, damping: 15}}
            >
              <svg width="100" height="40" viewBox="0 0 100 40" fill="none">
                <rect x="10" y="8" width="90" height="4" rx="2" fill="url(#armGrad)" />
                <circle cx="10" cy="10" r="8" fill="#555" stroke="#333" strokeWidth="1.5" />
                <circle cx="10" cy="10" r="3" fill="#222" />
                <rect x="85" y="2" width="16" height="16" rx="2" fill="#666" />
                <defs>
                  <linearGradient id="armGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#888" />
                    <stop offset="100%" stopColor="#444" />
                  </linearGradient>
                </defs>
              </svg>
            </motion.div>

            {/* 黑胶唱片 */}
            <motion.div
                ref={vinylRef}
                className="w-64 h-64 md:w-80 md:h-80 rounded-full bg-gradient-to-br from-gray-800 via-gray-900 to-black shadow-2xl flex items-center justify-center relative"
                style={{
                  boxShadow: isPlaying
                    ? '0 0 80px rgba(147, 51, 234, 0.4), inset 0 0 60px rgba(0,0,0,0.5)'
                    : '0 0 40px rgba(147, 51, 234, 0.15), inset 0 0 60px rgba(0,0,0,0.5)',
                }}
                animate={{rotate: isPlaying ? 360 : 0}}
                transition={isPlaying
                  ? {duration: 2, ease: 'linear', repeat: Infinity}
                  : {duration: 0.5, ease: 'easeOut'}
                }
            >
              {/* 唱片纹路 */}
              {[4, 8, 12, 16, 20, 24].map(i => (
                  <div key={i}
                       className="absolute rounded-full border border-gray-700 opacity-20"
                       style={{inset: `${i * 4}px`}}
                  />
              ))}

              {/* 唱片反光效果 */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/5 via-transparent to-transparent pointer-events-none" />

              {/* 中心标签 */}
              <div className="w-24 h-24 md:w-32 md:h-32 rounded-full overflow-hidden shadow-lg relative z-10">
                {coverImage ? (
                    <img
                        src={coverImage}
                        alt="Album Cover"
                        className="w-full h-full object-cover"
                    />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                      {loadingMetadata ? (
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>
                      ) : (
                          <div className="w-10 h-10 bg-gray-900 rounded-full flex items-center justify-center">
                            <Music className="w-5 h-5 text-purple-400"/>
                          </div>
                      )}
                    </div>
                )}
              </div>

              {/* 中心孔 */}
              <div className="absolute w-3 h-3 bg-gray-900 rounded-full z-20 border border-gray-700" />
            </motion.div>
          </div>
        </div>

        {/* Right: Controls & Lyrics */}
        <div className="flex-1 bg-white dark:bg-gray-900 flex flex-col min-h-0">
          <audio ref={audioRef} src={fullUrl} preload="auto"/>

          {/* Song Info */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 truncate">{media.original_filename}</h3>
            <p className="text-sm text-gray-500">
              {media.file_size ? `${(media.file_size / 1024 / 1024).toFixed(2)} MB` : ''} · {formatTime(duration)}
            </p>
          </div>

          {/* Progress Bar */}
          <div className="px-6 py-4">
            <input
                type="range"
                min="0"
                max={duration || 100}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="px-6 py-3 flex items-center justify-center gap-4">
            <motion.button
                whileTap={{scale: 0.9}}
                onClick={() => {
                  const audio = audioRef.current;
                  if (audio) audio.currentTime = Math.max(0, audio.currentTime - 10);
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
            >
              <svg className="w-6 h-6 text-gray-700 dark:text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/>
              </svg>
            </motion.button>

            <motion.button
                whileTap={{scale: 0.9}}
                onClick={togglePlay}
                className="w-16 h-16 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center shadow-lg hover:shadow-xl transition-shadow"
            >
              {isPlaying ? (
                  <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                  </svg>
              ) : (
                  <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
              )}
            </motion.button>

            <motion.button
                whileTap={{scale: 0.9}}
                onClick={() => {
                  const audio = audioRef.current;
                  if (audio) audio.currentTime = Math.min(duration, audio.currentTime + 10);
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
            >
              <svg className="w-6 h-6 text-gray-700 dark:text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                <path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/>
              </svg>
            </motion.button>
          </div>

          {/* Volume Control */}
          <div className="px-6 py-2 flex items-center gap-3">
            <svg className="w-5 h-5 text-gray-500 shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={volume}
                onChange={handleVolumeChange}
                className="flex-1 h-1 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
            />
          </div>

          {/* Lyrics Toggle */}
          <div className="px-6 pb-3">
            <button
                onClick={() => setShowLyrics(!showLyrics)}
                className={`w-full py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                    showLyrics
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                        : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
            >
              {showLyrics ? '🎤 隐藏歌词' : '📄 显示歌词'}
            </button>
          </div>

          {/* Lyrics Display with Karaoke Highlighting */}
          {showLyrics && (
              <div
                  ref={lyricsContainerRef}
                  className="flex-1 overflow-y-auto px-6 pb-6 space-y-4 scrollbar-thin"
                  style={{maxHeight: '320px'}}
              >
                {lyrics.length > 0 ? (
                    lyrics.map((lyric, index) => {
                      const isActive = index === activeLineIndex;
                      const tokens = tokenizeText(lyric.text);
                      const highlightCount = isActive
                          ? Math.floor(tokens.length * karaokeProgress)
                          : (index < activeLineIndex ? tokens.length : 0);

                      return (
                          <motion.div
                              key={index}
                              className={`text-center leading-relaxed ${
                                  isActive
                                      ? 'text-lg font-semibold'
                                      : index < activeLineIndex
                                          ? 'text-sm text-gray-500 dark:text-gray-400'
                                          : 'text-sm text-gray-400 dark:text-gray-500'
                              }`}
                              animate={isActive ? {scale: 1.02} : {scale: 1}}
                              transition={{duration: 0.2}}
                          >
                            {tokens.map((token, ti) => {
                              const isHighlighted = ti < highlightCount;
                              const isPartial = isActive && ti === highlightCount - 1 && karaokeProgress < 1;
                              // 计算单个 token 的渐变动画进度
                              const tokenProgress = isPartial
                                  ? (karaokeProgress * tokens.length - ti)
                                  : (isHighlighted ? 1 : 0);

                              return token === ' ' ? (
                                  <span key={ti}>&nbsp;</span>
                              ) : (
                                  <span
                                      key={ti}
                                      className="relative inline-block transition-colors duration-100"
                                  >
                            {/* 已高亮部分 */}
                                    <span
                                        className={`transition-all duration-150 ${
                                            isHighlighted
                                                ? 'text-purple-600 dark:text-purple-400'
                                                : 'text-gray-400 dark:text-gray-500'
                                        }`}
                                    >
                              {token}
                            </span>
                                    {/* 逐字渐变覆盖 — 用于当前正在高亮的字 */}
                                    {isPartial && tokenProgress > 0 && tokenProgress < 1 && (
                                        <span
                                            className="absolute inset-0 overflow-hidden"
                                            style={{color: 'transparent'}}
                                        >
                                  <span
                                      className="absolute inset-0 text-purple-600 dark:text-purple-400"
                                      style={{
                                        clipPath: `inset(0 ${(1 - tokenProgress) * 100}% 0 0)`,
                                      }}
                                  >
                                    {token}
                                  </span>
                                </span>
                                    )}
                          </span>
                              );
                            })}
                          </motion.div>
                      );
                    })
                ) : (
                    <div className="text-center text-gray-400 py-8">
                      <Music className="w-12 h-12 mx-auto mb-3 opacity-50"/>
                      <p>暂无歌词</p>
                      <p className="text-xs mt-2">支持在音频文件同目录下放置 .lrc 文件</p>
                    </div>
                )}
              </div>
          )}
        </div>
      </div>
  );
};

/* ---------- Modals ---------- */
const PreviewModal: React.FC<{media: MediaFile|null; onClose: ()=>void}> = ({media, onClose}) => {
  if(!media) return null;
  const fullUrl = getFullMediaUrl(media.url);
  
  return (<div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={onClose}>
    <div
        className="w-[90vw] max-w-7xl max-h-[95vh] bg-white dark:bg-gray-900 rounded-2xl overflow-hidden shadow-2xl flex flex-col"
         onClick={e => e.stopPropagation()}>
      {/* Audio Player with Vinyl Animation */}
      {media.mime_type?.startsWith('audio/') && fullUrl ? (
          <AudioPlayer media={media} fullUrl={fullUrl}/>
      ) : media.mime_type === 'application/pdf' && fullUrl ? (
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 min-h-[80vh]">
            <embed
                src={fullUrl}
                type="application/pdf"
                className="w-full h-full"
                style={{minHeight: '80vh', maxHeight: '85vh'}}
            />
          </div>
      ) : media.mime_type?.startsWith('video/') && fullUrl ? (
          // Video Player - 流式播放
          <div className="bg-black">
            <video
                src={fullUrl}
                controls
                autoPlay
                preload="auto"
                className="max-w-full max-h-[70vh] w-full"
                style={{maxHeight: '70vh'}}
                playsInline
            >
              您的浏览器不支持视频播放
            </video>
          </div>
      ) : media.mime_type?.startsWith('image/') && fullUrl ? (
          // 图片完整加载
          <img
              src={fullUrl}
              alt={media.original_filename}
              className="max-w-full max-h-[70vh] object-contain"
              loading="eager"
              decoding="async"
          />
      ) : (
          <div className="p-16 text-center"><FileText className="w-16 h-16 text-gray-400 mx-auto mb-4"/><p
              className="text-gray-600">{media.original_filename}</p></div>
      )}
      <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
        <h3 className="font-bold text-gray-900 dark:text-white">{media.original_filename}</h3>
        <p className="text-sm text-gray-500 mt-1">
          {media.file_size ? `${(media.file_size / 1024).toFixed(1)} KB` : ''} · {media.mime_type}
        </p>
      </div>
    </div>
  </div>);
};

const DeleteConfirm: React.FC<{item: MediaFile; onCancel: ()=>void; onConfirm: ()=>void}> = ({item, onCancel, onConfirm}) => (
  <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onCancel}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">确认删除</h3>
      <p className="text-sm text-gray-500 mb-6">确定要删除 <span className="font-medium">{item.original_filename}</span> 吗？</p>
      <div className="flex justify-end gap-3"><button onClick={onCancel} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button><button onClick={onConfirm} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700">删除</button></div>
    </div>
  </div>
);

const MoveDialog: React.FC<{open: boolean; onClose: ()=>void; folders: FolderNode[]; mediaCount: number; onMove: (folderPath: string|null)=>void}> = ({open, onClose, folders, mediaCount, onMove}) => {
  if(!open) return null;
  const renderNode = (node: FolderNode, depth=0) => (
    <button key={node.id} onClick={()=>onMove(node.name)} className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors" style={{paddingLeft:`${16+depth*20}px`}}>
      <FolderClosed className="w-5 h-5 text-yellow-600"/> <span className="font-medium">{node.name}</span>
    </button>
  );
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-md w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-2">移动文件</h3>
      <p className="text-sm text-gray-500 mb-4">将选中的 {mediaCount} 个文件移动到：</p>
      <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
        <button onClick={()=>onMove(null)} className="w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-500 transition-colors">
          <Grid3X3 className="w-5 h-5 text-gray-500"/><span className="font-medium">根目录</span>
        </button>
        {folders.map(n=>renderNode(n))}
      </div>
      <div className="flex justify-end"><button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button></div>
    </div>
  </div>);
};

const CreateFolderDialog: React.FC<{open: boolean; onClose: ()=>void; onCreate: (name: string)=>void}> = ({open, onClose, onCreate}) => {
  const [name, setName] = useState('');
  if(!open) return null;
  return (<div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl" onClick={e=>e.stopPropagation()}>
      <h3 className="text-lg font-bold mb-4">新建文件夹</h3>
      <input type="text" value={name} onChange={e=>setName(e.target.value)} placeholder="文件夹名称" className="w-full px-4 py-3 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white mb-4" autoFocus onKeyDown={e=>{if(e.key==='Enter' && name.trim()) {onCreate(name.trim()); setName('');}}}/>
      <div className="flex justify-end gap-3"><button onClick={onClose} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium">取消</button><button onClick={()=>{if(name.trim()){onCreate(name.trim()); setName('');}}} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">创建</button></div>
    </div>
  </div>);
};

/* ---------- Upload hook ---------- */
const useMediaUpload = (onComplete?: () => void) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true); setUploadProgress(0); setUploadStatus(`开始上传 ${files.length} 个文件...`);
    try {
      for (let i = 0; i < files.length; i++) {
        await MediaService.uploadMediaFileWithProgress(files[i], (p) => { setUploadProgress(((i/files.length)*100)+(p/files.length)); });
        setUploadStatus(`已上传: ${files[i].name} (${i+1}/${files.length})`);
      }
      setUploadStatus('上传完成!'); if (onComplete) onComplete();
    } catch (e: any) { setUploadStatus(`上传失败: ${e.message}`); }
    finally { setTimeout(()=>{setUploading(false);setUploadProgress(0);setUploadStatus('');},2000); }
  };
  return {uploading, uploadProgress, uploadStatus, uploadFiles};
};

/* ========== Main MediaPage ========== */
const MediaPage: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterType, setFilterType] = useState('');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid'|'list'>('grid');
  const [selected, setSelected] = useState<number[]>([]);
  const [previewMedia, setPreviewMedia] = useState<MediaFile|null>(null);
  const [deleteItem, setDeleteItem] = useState<MediaFile|null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uploadCollapsed, setUploadCollapsed] = useState(true);
  const [stats, setStats] = useState<any>({});
  // Folder state
  const [folders, setFolders] = useState<FolderNode[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<number|null>(null);
  const [folderLoading, setFolderLoading] = useState(true);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showMoveDialog, setShowMoveDialog] = useState(false);

  const loadFolders = useCallback(async () => {
    setFolderLoading(true);
    try {
      const res = await apiClient.get('/media/folders/tree');
      if (res.success && res.data) setFolders((res.data as any).tree || []);
    } catch {} finally { setFolderLoading(false); }
  }, []);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {page, per_page: 20, media_type: filterType||undefined, q: search||undefined};
      // Get folder name from selected folder
      if (selectedFolder !== null) {
        const findName = (nodes: FolderNode[], id: number): string|null => {
          for (const n of nodes) { if (n.id===id) return n.name; if (n.children) {const r=findName(n.children,id); if(r) return r;}} return null;
        };
        const fn = findName(folders, selectedFolder);
        if (fn) params.folder_name = fn;
      }
      const res = await MediaService.getMediaFiles(params);
      if (res.success && res.data) {
        const d = res.data as MediaResponse;
        setFiles(d.media_items || []); setTotalPages(d.pagination?.pages||1);
        if (d.stats) setStats(d.stats);
      }
    } catch {} finally { setLoading(false); }
  }, [page, filterType, search, selectedFolder, folders]);

  useEffect(() => { loadFiles(); }, [loadFiles]);
  useEffect(() => { loadFolders(); }, []);

  const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => loadFiles());

  const handleDelete = async (id: number) => {
    const res = await MediaService.deleteMediaFile([id]);
    if (res.success) { setDeleteItem(null); loadFiles(); } else alert(res.error||'删除失败');
  };

  const handleCreateFolder = async (name: string) => {
    const res = await apiClient.post('/media/folders/', {name});
    if (res.success) { setShowCreateFolder(false); loadFolders(); }
    else alert(res.error||'创建失败');
  };

  const handleMoveToFolder = async (folderPath: string|null) => {
    if (!selected.length) return;
    const res = await apiClient.post('/media/folders/move-media', {media_ids: selected, folder_path: folderPath});
    if (res.success) { setSelected([]); setShowMoveDialog(false); loadFiles(); }
    else alert(res.error||'移动失败');
  };

  const handleDeleteFolder = async (id: number) => {
    if (!confirm('确定删除此文件夹？')) return;
    const res = await apiClient.delete(`/media/folders/${id}`);
    if (res.success) { if (selectedFolder===id) setSelectedFolder(null); loadFolders(); }
    else alert(res.error||'删除失败');
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 pt-24 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">媒体库</h1>
          <div className="flex items-center gap-2">
            <button onClick={()=>setSidebarCollapsed(!sidebarCollapsed)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">{sidebarCollapsed?<ChevronRight className="w-5 h-5"/>:<ChevronLeft className="w-5 h-5"/>}</button>
            <button onClick={()=>setViewMode('grid')} className={`p-2 rounded-lg ${viewMode==='grid'?'bg-blue-100 text-blue-600':'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><Grid3X3 className="w-5 h-5"/></button>
            <button onClick={()=>setViewMode('list')} className={`p-2 rounded-lg ${viewMode==='list'?'bg-blue-100 text-blue-600':'hover:bg-gray-100 dark:hover:bg-gray-800'}`}><List className="w-5 h-5"/></button>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          <aside className={`${sidebarCollapsed?'hidden':'lg:w-56'} flex-shrink-0 space-y-6`}>
            <StorageStats stats={stats} loading={loading}/>
            <FolderTree folders={folders} selectedId={selectedFolder} onSelect={f=>{setSelectedFolder(f?.id??null);setPage(1)}} onCreate={()=>setShowCreateFolder(true)} onDelete={handleDeleteFolder} loading={folderLoading}/>
          </aside>

          <main className="flex-1">
            <UploadArea onUpload={uploadFiles} uploading={uploading} progress={uploadProgress} status={uploadStatus} collapsed={uploadCollapsed} onToggle={()=>setUploadCollapsed(!uploadCollapsed)}/>

            <div className="flex flex-wrap items-center gap-3 mb-4">
              <input type="text" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}} placeholder="搜索文件..." className="flex-1 min-w-[200px] px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"/>
              {selected.length>0 && (<div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-blue-600 font-medium">{selected.length} 已选</span>
                <button onClick={()=>setSelected([])} className="px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 rounded-lg">取消</button>
                <button onClick={()=>{if(selected.length)setShowMoveDialog(true);}} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"><FolderClosed className="w-4 h-4 inline mr-1"/>移动</button>
                <button onClick={async()=>{if(!confirm(`删除 ${selected.length} 个文件？`))return;const r=await MediaService.deleteMediaFile(selected);if(r.success){setSelected([]);loadFiles();}}} className="px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"><Trash2 className="w-4 h-4 inline mr-1"/>删除</button>
              </div>)}
            </div>

            <MediaGrid files={files} loading={loading} viewMode={viewMode} selected={selected} onSelect={id=>setSelected(s=>s.includes(id)?s.filter(x=>x!==id):[...s,id])} onPreview={setPreviewMedia} onDelete={setDeleteItem}/>

            {totalPages>1 && (<div className="flex items-center justify-center gap-2 mt-8">
              <button disabled={page<=1} onClick={()=>setPage(p=>p-1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100"><ChevronLeft className="w-4 h-4"/></button>
              {Array.from({length:totalPages},(_,i)=>i+1).map(p=><button key={p} onClick={()=>setPage(p)} className={`px-3 py-1.5 rounded-lg text-sm ${p===page?'bg-blue-600 text-white':'border hover:bg-gray-100 dark:hover:bg-gray-800'}`}>{p}</button>)}
              <button disabled={page>=totalPages} onClick={()=>setPage(p=>p+1)} className="p-2 rounded-lg border disabled:opacity-30 hover:bg-gray-100"><ChevronRight className="w-4 h-4"/></button>
            </div>)}
          </main>
        </div>
      </div>

      <PreviewModal media={previewMedia} onClose={()=>setPreviewMedia(null)}/>
      {deleteItem && <DeleteConfirm item={deleteItem} onCancel={()=>setDeleteItem(null)} onConfirm={()=>handleDelete(deleteItem.id)}/>}
      <CreateFolderDialog open={showCreateFolder} onClose={()=>setShowCreateFolder(false)} onCreate={handleCreateFolder}/>
      <MoveDialog open={showMoveDialog} onClose={()=>setShowMoveDialog(false)} folders={folders} mediaCount={selected.length} onMove={handleMoveToFolder}/>
    </div>
  );
};

const MediaPageGuard: React.FC = () => <AuthGuard><MediaPage /></AuthGuard>;
export default MediaPageGuard;
