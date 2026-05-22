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

  // 扩展控制状态
  const [repeatMode, setRepeatMode] = useState<'off' | 'one' | 'all'>('off');
  const [isLiked, setIsLiked] = useState(false);
  const [showPlaylist, setShowPlaylist] = useState(false);
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);

  return (
      <div className="flex flex-col h-full bg-black select-none">
        <audio ref={audioRef} src={fullUrl} preload="auto"/>

        {/* ====== Main Content Area ====== */}
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
          {/* --- Left: Vinyl (hidden on mobile, shown lg+) --- */}
          <div className="hidden lg:flex w-[45%] items-center justify-center relative overflow-hidden">
            {/* Background glow */}
            <motion.div
                className="absolute inset-0"
                animate={{opacity: isPlaying ? 0.3 : 0.06}}
                transition={{duration: 1}}
            >
              <motion.div
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] aspect-square rounded-full blur-3xl"
                  style={{background: 'radial-gradient(circle, rgba(147,51,234,0.5), rgba(236,72,153,0.2), transparent)'}}
                  animate={isPlaying ? {
                    scale: [1, 1.1, 1],
                    opacity: [0.3, 0.6, 0.3],
                  } : {scale: 1, opacity: 0.2}}
                  transition={isPlaying ? {
                    duration: 4,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  } : {duration: 0.6}}
              />
            </motion.div>

            {/* Vinyl + Tone arm container */}
            <div className="relative">
              {/* 唱臂 */}
              <motion.div
                  className="absolute -top-8 -right-8 z-10"
                  style={{transformOrigin: '16px 100%'}}
                  animate={{rotate: isPlaying ? 18 : -35}}
                  transition={{type: 'spring', stiffness: 90, damping: 14}}
              >
                <svg width="110" height="48" viewBox="0 0 110 48" fill="none">
                  <rect x="16" y="10" width="94" height="4" rx="2" fill="url(#armGrad2)" />
                  <circle cx="16" cy="12" r="10" fill="#555" stroke="#333" strokeWidth="1.5" />
                  <circle cx="16" cy="12" r="4" fill="#222" />
                  <circle cx="16" cy="12" r="1.5" fill="#888" />
                  <rect x="92" y="2" width="18" height="20" rx="3" fill="#555" />
                  <circle cx="101" cy="12" r="3" fill="#777" />
                  <defs>
                    <linearGradient id="armGrad2" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#999" />
                      <stop offset="50%" stopColor="#666" />
                      <stop offset="100%" stopColor="#444" />
                    </linearGradient>
                  </defs>
                </svg>
              </motion.div>

              {/* 黑胶唱片 */}
              <motion.div
                  ref={vinylRef}
                  className="w-72 h-72 xl:w-80 xl:h-80 rounded-full bg-gradient-to-br from-gray-800 via-gray-900 to-black shadow-2xl flex items-center justify-center relative"
                  style={{
                    boxShadow: isPlaying
                      ? '0 0 100px rgba(147, 51, 234, 0.35), inset 0 0 80px rgba(0,0,0,0.6)'
                      : '0 0 50px rgba(147, 51, 234, 0.1), inset 0 0 80px rgba(0,0,0,0.6)',
                  }}
                  animate={{rotate: isPlaying ? 360 : 0}}
                  transition={isPlaying
                    ? {duration: 8, ease: 'linear', repeat: Infinity}
                    : {duration: 0.6, ease: 'easeOut'}
                  }
              >
                {/* 纹路 */}
                {[5, 10, 15, 20, 25, 30, 35].map(i => (
                    <div key={i}
                         className="absolute rounded-full border border-gray-700/20"
                         style={{inset: `${i * 4}px`}}
                    />
                ))}

                {/* 反光 */}
                <div className="absolute inset-2 rounded-full bg-gradient-to-br from-white/[0.06] via-transparent to-transparent pointer-events-none" />

                {/* 中心标签 */}
                <div className="w-28 h-28 xl:w-32 xl:h-32 rounded-full overflow-hidden shadow-lg relative z-10 ring-2 ring-white/10">
                  {coverImage ? (
                      <img
                          src={coverImage}
                          alt="cover"
                          className="w-full h-full object-cover"
                      />
                  ) : (
                      <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                        {loadingMetadata ? (
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"/>
                        ) : (
                            <Music className="w-7 h-7 text-white/80"/>
                        )}
                      </div>
                  )}
                </div>

                {/* 中心孔 */}
                <div className="absolute w-3 h-3 bg-black rounded-full z-20 border border-gray-700/50" />
              </motion.div>
            </div>
          </div>

          {/* --- Right: Lyrics Area (Apple Music style) --- */}
          <div className="flex-1 flex flex-col min-h-0 relative">
            {/* 手机版：顶部封面缩略 + 歌名 */}
            <div className="lg:hidden flex items-center gap-4 p-5 border-b border-white/10">
              <div className="w-14 h-14 rounded-xl overflow-hidden shadow-lg shrink-0">
                {coverImage ? (
                    <img src={coverImage} alt="cover" className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                      <Music className="w-6 h-6 text-white/80"/>
                    </div>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-white font-semibold truncate text-base">{media.original_filename}</p>
                <p className="text-white/50 text-xs truncate">FastBlog Audio</p>
              </div>
            </div>

            {/* 歌词标题 */}
            <div className="px-6 pt-5 pb-2 flex items-center justify-between">
              <button
                  onClick={() => setShowLyrics(!showLyrics)}
                  className="flex items-center gap-2 text-sm font-medium transition-colors"
                  style={{color: showLyrics ? '#a855f7' : 'rgba(255,255,255,0.4)'}}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                </svg>
                歌词
              </button>
              {showLyrics && lyrics.length > 0 && (
                  <span className="text-xs text-white/30">{lyrics.length} 行</span>
              )}
            </div>

            {/* 歌词内容 */}
            <div className="flex-1 overflow-hidden px-4">
              {showLyrics ? (
                  <div
                      ref={lyricsContainerRef}
                      className="h-full overflow-y-auto space-y-3 py-2 scrollbar-thin"
                      style={{scrollbarWidth: 'thin'}}
                  >
                    {lyrics.length > 0 ? (
                        lyrics.map((lyric, index) => {
                          const isActive = index === activeLineIndex;
                          const isPast = index < activeLineIndex;
                          const tokens = tokenizeText(lyric.text);
                          const highlightCount = isActive
                              ? Math.floor(tokens.length * karaokeProgress)
                              : (isPast ? tokens.length : 0);

                          return (
                              <div key={index} className="relative px-4 py-2 transition-all duration-300 min-h-[2.5rem]"
                                   style={{
                                     opacity: isPast ? 0.5 : (isActive ? 1 : 0.35),
                                     transform: isActive ? 'scale(1)' : 'scale(0.96)',
                                   }}
                              >
                                {/* 背景进度条 */}
                                {isActive && (
                                    <motion.div
                                        className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500/8 via-pink-500/8 to-transparent pointer-events-none"
                                        animate={{width: `${karaokeProgress * 100}%`}}
                                        transition={{duration: 0.08, ease: 'linear'}}
                                    />
                                )}

                                <div className={`text-center leading-relaxed ${isActive ? 'text-xl font-bold tracking-wide' : 'text-sm'}`}>
                                  {tokens.map((token, ti) => {
                                    const isHighlighted = ti < highlightCount;
                                    const isTransitioning = isActive && ti === highlightCount - 1 && karaokeProgress < 1;
                                    const isNextToken = isActive && ti === highlightCount;
                                    const tokenClipProgress = isTransitioning
                                        ? (karaokeProgress * tokens.length - ti)
                                        : (isHighlighted ? 1 : 0);

                                    return token === ' ' ? (
                                        <span key={ti} className="inline-block" style={{width: '0.3em'}}>&nbsp;</span>
                                    ) : (
                                        <span key={ti} className="relative inline-block mx-[0.5px]">
                                      {/* 未高亮层 */}
                                      <span className={`transition-all duration-150 ${isHighlighted ? 'text-transparent' : 'text-white/50'}`}>
                                        {token}
                                      </span>
                                          {/* 高亮渐变层 */}
                                          {isHighlighted && (
                                              <span className="absolute inset-0 bg-gradient-to-r from-purple-400 via-fuchsia-300 to-pink-300 bg-clip-text text-transparent"
                                                    style={{
                                                      WebkitBackgroundClip: 'text',
                                                      filter: isActive ? 'drop-shadow(0 0 10px rgba(168,85,247,0.5))' : 'none',
                                                    }}
                                              >
                                            {token}
                                          </span>
                                          )}
                                          {/* 过渡 clipPath */}
                                          {isTransitioning && (
                                              <span className="absolute inset-0 overflow-hidden" style={{color: 'transparent'}}>
                                            <span className="absolute inset-0 bg-gradient-to-r from-purple-400 via-fuchsia-300 to-pink-300 bg-clip-text text-transparent"
                                                  style={{
                                                    WebkitBackgroundClip: 'text',
                                                    clipPath: `inset(0 ${(1 - tokenClipProgress) * 100}% 0 0)`,
                                                    filter: 'drop-shadow(0 0 12px rgba(168,85,247,0.7))',
                                                  }}
                                            >
                                              {token}
                                            </span>
                                          </span>
                                          )}
                                          {/* 下一个字脉冲 */}
                                          {isNextToken && (
                                              <motion.span
                                                  className="absolute inset-0 text-white/50"
                                                  animate={{opacity: [0.3, 0.7, 0.3]}}
                                                  transition={{duration: 1.2, repeat: Infinity, ease: 'easeInOut'}}
                                              >
                                                {token}
                                              </motion.span>
                                          )}
                                    </span>
                                    );
                                  })}
                                </div>
                              </div>
                          );
                        })
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-white/30">
                          <Music className="w-12 h-12 mb-4 opacity-40"/>
                          <p className="text-sm">暂无歌词</p>
                          <p className="text-xs mt-1">支持在音频文件同目录下放置 .lrc 文件</p>
                        </div>
                    )}
                  </div>
              ) : (
                  <div className="flex flex-col items-center justify-center h-full text-white/20">
                    <svg className="w-16 h-16 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                    </svg>
                    <p className="text-sm">点击上方「歌词」查看逐字高亮</p>
                  </div>
              )}
            </div>
          </div>
        </div>

        {/* ====== Bottom Controls Bar (Apple Music style) ====== */}
        <div className="flex-shrink-0 bg-black/90 backdrop-blur-2xl border-t border-white/10">
          {/* --- Progress Bar --- */}
          <div className="px-4 pt-2 pb-1">
            <input
                type="range"
                min="0"
                max={duration || 100}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-1 bg-white/20 rounded-full appearance-none cursor-pointer accent-purple-500"
                style={{
                  background: `linear-gradient(to right, #a855f7 ${(currentTime / (duration || 1)) * 100}%, rgba(255,255,255,0.15) ${(currentTime / (duration || 1)) * 100}%)`,
                }}
            />
            <div className="flex justify-between text-[11px] text-white/30 mt-0.5 px-0.5">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* --- Controls Row --- */}
          <div className="flex items-center justify-between px-5 pb-3 gap-2">
            {/* Left: song info */}
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 rounded-lg overflow-hidden shadow shrink-0">
                {coverImage ? (
                    <img src={coverImage} alt="" className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                      <Music className="w-5 h-5 text-white/70"/>
                    </div>
                )}
              </div>
              <div className="min-w-0 max-w-[140px]">
                <p className="text-white text-sm font-medium truncate">{media.original_filename}</p>
                <p className="text-white/40 text-xs truncate">FastBlog</p>
              </div>
              {/* Like button */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setIsLiked(!isLiked)}
                  className="shrink-0"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill={isLiked ? '#ec4899' : 'none'} stroke={isLiked ? '#ec4899' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                </svg>
              </motion.button>
            </div>

            {/* Center: Playback controls */}
            <div className="flex items-center gap-3">
              {/* Rewind 10s */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => {const a = audioRef.current; if (a) a.currentTime = Math.max(0, a.currentTime - 10);}}
                  className="text-white/50 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
              </motion.button>

              {/* Prev (restart) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => {const a = audioRef.current; if (a) a.currentTime = 0;}}
                  className="text-white/50 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
              </motion.button>

              {/* Play/Pause (large) */}
              <motion.button
                  whileTap={{scale: 0.9}}
                  onClick={togglePlay}
                  className="w-11 h-11 bg-white rounded-full flex items-center justify-center shadow-lg hover:shadow-xl transition-all"
              >
                {isPlaying ? (
                    <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                ) : (
                    <svg className="w-5 h-5 text-black ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                )}
              </motion.button>

              {/* Next (forward 10s) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => {const a = audioRef.current; if (a) a.currentTime = Math.min(duration, a.currentTime + 10);}}
                  className="text-white/50 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
              </motion.button>

              {/* Forward 10s */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => {const a = audioRef.current; if (a) a.currentTime = Math.min(duration, a.currentTime + 10);}}
                  className="text-white/50 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M13 6v12l8.5-6L13 6zM4 18l8.5-6L4 6v12z"/></svg>
              </motion.button>
            </div>

            {/* Right: Volume & extras */}
            <div className="flex items-center gap-3 flex-1 justify-end">
              {/* Repeat */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setRepeatMode(r => r === 'off' ? 'all' : r === 'all' ? 'one' : 'off')}
                  className="relative"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke={repeatMode !== 'off' ? '#a855f7' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                {repeatMode === 'one' && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-purple-500 rounded-full flex items-center justify-center text-[8px] font-bold text-white">1</span>
                )}
              </motion.button>

              {/* Volume */}
              <div className="relative flex items-center">
                <motion.button
                    whileTap={{scale: 0.85}}
                    onClick={() => setShowVolumeSlider(v => !v)}
                    className="flex items-center"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
                  </svg>
                </motion.button>
                {showVolumeSlider && (
                    <div className="absolute bottom-full right-0 mb-2 p-3 bg-neutral-900/95 backdrop-blur-xl rounded-xl border border-white/10 shadow-xl">
                      <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={volume}
                          onChange={handleVolumeChange}
                          className="w-20 h-1 bg-white/20 rounded-full appearance-none cursor-pointer accent-purple-500 rotate-0"
                          style={{
                            background: `linear-gradient(to right, #a855f7 ${volume * 100}%, rgba(255,255,255,0.15) ${volume * 100}%)`,
                          }}
                      />
                    </div>
                )}
              </div>

              {/* Playlist toggle */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setShowPlaylist(!showPlaylist)}
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
                </svg>
              </motion.button>
            </div>
          </div>
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
