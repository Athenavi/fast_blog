import React, {useCallback, useEffect, useRef, useState} from 'react';
import {motion} from 'framer-motion';
import {ChevronLeft, ChevronRight, ChevronDown, Music, X} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import {getConfig} from '@/lib/config';
import {getFullMediaUrl} from '@/lib/utils';
import DesktopLyrics from '@/components/audio/DesktopLyrics';


// ─── Lyrics helpers ──────────────────────────

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


// ─── Audio components ────────────────────────

const AudioPlayer: React.FC<{
  media: MediaFile;
  fullUrl: string;
  onMinimize?: () => void;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  togglePlay: () => void;
  handleSeek: (t: number) => void;
}> = ({media, fullUrl, onMinimize, audioRef, isPlaying, currentTime, duration, togglePlay, handleSeek}) => {
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

  // togglePlay 由父组件 AudioLayer 提供
  const handleSeekEvent = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleSeek(parseFloat(e.target.value));
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

        {/* ====== Main Content Area ====== */}
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
          {/* 最小化按钮 (桌面左上角) */}
          <button
              onClick={onMinimize}
              className="absolute top-4 left-4 z-20 w-8 h-8 rounded-full bg-white/5 hover:bg-white/15 backdrop-blur flex items-center justify-center transition-colors hidden lg:flex"
              aria-label="最小化播放"
              title="最小化 (Esc)"
          >
            <svg className="w-4 h-4 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

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

            {/* Vinyl + Tone arm container — 点击唱片可最小化 */}
            <div className="relative cursor-pointer" onClick={onMinimize}>
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
              <motion.button
                  className="shrink-0"
                  whileTap={{scale: 0.9}}
                  onClick={onMinimize}
                  aria-label="最小化"
              >
                <svg className="w-5 h-5 text-white/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
                </svg>
              </motion.button>
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
        <div className="flex-shrink-0 bg-black/90 backdrop-blur-2xl border-t border-white/10"
             style={{paddingBottom: 'env(safe-area-inset-bottom, 0px)'}}>
          {/* --- Progress Bar (touch-friendly, thin visual + large tap target) --- */}
          <div className="px-4 pt-3 pb-1">
            <div className="relative h-6 flex items-center -my-1">
              <input
                  type="range"
                  min="0"
                  max={duration || 100}
                  value={currentTime}
                  onChange={handleSeekEvent}
                  className="absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer z-10 opacity-0"
                  style={{touchAction: 'none'}}
                  aria-label="播放进度"
              />
              {/* 视觉进度条 */}
              <div className="w-full h-1 rounded-full bg-white/15 overflow-hidden pointer-events-none">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-75"
                    style={{width: `${duration ? (currentTime / duration) * 100 : 0}%`}}
                />
              </div>
            </div>
            <div className="flex justify-between text-[11px] text-white/30 mt-0.5 px-0.5">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* --- Controls Row --- */}
          <div className="flex items-center justify-between px-5 pb-3 gap-2">
            {/* Left: song info */}
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <motion.div
                  className="w-10 h-10 rounded-lg overflow-hidden shadow shrink-0 cursor-pointer"
                  whileTap={{scale: 0.9}}
                  onClick={onMinimize}
                  title="最小化播放 (Esc)"
                  aria-label="最小化播放"
              >
                {coverImage ? (
                    <img src={coverImage} alt="" className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                      <Music className="w-5 h-5 text-white/70"/>
                    </div>
                )}
              </motion.div>
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

            {/* Center: Playback controls — 标准三键布局 + 附加键 (桌面) */}
            <div className="flex items-center justify-center gap-1 sm:gap-3">
              {/* Rewind 10s (仅桌面) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => handleSeek(Math.max(0, currentTime - 10))}
                  className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] items-center justify-center hidden sm:flex"
                  aria-label="后退10秒"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
              </motion.button>

              {/* Prev (restart) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => handleSeek(0)}
                  className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                  aria-label="重新播放"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
              </motion.button>

              {/* Play/Pause (large) */}
              <motion.button
                  whileTap={{scale: 0.9}}
                  onClick={togglePlay}
                  className="w-12 h-12 sm:w-11 sm:h-11 bg-white rounded-full flex items-center justify-center shadow-lg hover:shadow-xl transition-all mx-1"
                  aria-label={isPlaying ? '暂停' : '播放'}
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

              {/* Next (skip 10s) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => handleSeek(Math.min(duration, currentTime + 10))}
                  className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                  aria-label="前进10秒"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
              </motion.button>

              {/* Forward 10s (仅桌面) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => handleSeek(Math.min(duration, currentTime + 10))}
                  className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] items-center justify-center hidden sm:flex"
                  aria-label="快进10秒"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M13 6v12l8.5-6L13 6zM4 18l8.5-6L4 6v12z"/></svg>
              </motion.button>
            </div>

            {/* Right: Volume & extras */}
            <div className="flex items-center justify-end gap-1 sm:gap-3 flex-1">
              {/* Repeat (hidden on mobile) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setRepeatMode(r => r === 'off' ? 'all' : r === 'all' ? 'one' : 'off')}
                  className="relative hidden sm:block p-2 min-w-[44px] min-h-[44px]"
                  aria-label={`循环模式: ${repeatMode === 'off' ? '关闭' : repeatMode === 'all' ? '全部循环' : '单曲循环'}`}
              >
                <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none" stroke={repeatMode !== 'off' ? '#a855f7' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                {repeatMode === 'one' && (
                    <span className="absolute top-0 right-0 w-3 h-3 bg-purple-500 rounded-full flex items-center justify-center text-[8px] font-bold text-white">1</span>
                )}
              </motion.button>

              {/* Volume (hidden on mobile) */}
              <div className="relative hidden sm:flex items-center">
                <motion.button
                    whileTap={{scale: 0.85}}
                    onClick={() => setShowVolumeSlider(v => !v)}
                    className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                    aria-label="音量"
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
                          className="w-24 h-1.5 bg-white/20 rounded-full appearance-none cursor-pointer accent-purple-500"
                          style={{
                            background: `linear-gradient(to right, #a855f7 ${volume * 100}%, rgba(255,255,255,0.15) ${volume * 100}%)`,
                          }}
                          aria-label="音量滑块"
                      />
                    </div>
                )}
              </div>

              {/* Mobile: 歌词快捷切换 */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setShowLyrics(!showLyrics)}
                  className="sm:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                  aria-label={showLyrics ? '隐藏歌词' : '显示歌词'}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke={showLyrics ? '#a855f7' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                </svg>
              </motion.button>

              {/* Playlist toggle (hidden on mobile) */}
              <motion.button
                  whileTap={{scale: 0.85}}
                  onClick={() => setShowPlaylist(!showPlaylist)}
                  className="hidden sm:block p-2 min-w-[44px] min-h-[44px]"
                  aria-label="播放列表"
              >
                <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
                </svg>
              </motion.button>
            </div>
          </div>
        </div>
      </div>
  );
};

/* ========== MiniPlayer (最小化播放) ========== */
const MiniPlayer: React.FC<{
  media: MediaFile;
  fullUrl: string;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onRestore: () => void;
  onClose: () => void;
  coverImage: string | null;
  currentTime: number;
  duration: number;
  formatTime: (t: number) => string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
}> = ({media, fullUrl, isPlaying, onTogglePlay, onRestore, onClose, coverImage, currentTime, duration, formatTime, audioRef}) => {
  const [showMenu, setShowMenu] = useState(false);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 长按处理（移动端）
  const handleTouchStart = () => {
    longPressTimer.current = setTimeout(() => setShowMenu(true), 500);
  };
  const handleTouchEnd = () => {
    if (longPressTimer.current) clearTimeout(longPressTimer.current);
  };

  // 点击外部关闭菜单
  useEffect(() => {
    if (!showMenu) return;
    const handler = () => setShowMenu(false);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [showMenu]);

  return (
      <>
        {/* 桌面端：左下角迷你卡片 */}
        <motion.div
            initial={{x: -100, opacity: 0}}
            animate={{x: 0, opacity: 1}}
            exit={{x: -100, opacity: 0}}
            className="hidden sm:flex fixed bottom-4 left-4 z-[60] bg-black/90 backdrop-blur-2xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden"
            style={{paddingBottom: 'env(safe-area-inset-bottom, 0px)'}}
        >
          <div className="flex items-center gap-3 p-3 min-w-[260px] max-w-[320px]">
            {/* 封面 */}
            <motion.div
                className="w-12 h-12 rounded-xl overflow-hidden shrink-0 cursor-pointer"
                whileTap={{scale: 0.9}}
                onClick={onRestore}
                animate={isPlaying ? {rotate: 360} : {rotate: 0}}
                transition={isPlaying ? {duration: 8, ease: 'linear', repeat: Infinity} : {duration: 0.4}}
            >
              {coverImage ? (
                  <img src={coverImage} alt="" className="w-full h-full object-cover"/>
              ) : (
                  <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                    <Music className="w-6 h-6 text-white/70"/>
                  </div>
              )}
            </motion.div>

            {/* 歌名 + 进度条 */}
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate cursor-pointer" onClick={onRestore}>{media.original_filename}</p>
              <div className="w-full h-0.5 rounded-full bg-white/10 mt-1.5 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-200"
                     style={{width: `${duration ? (currentTime / duration) * 100 : 0}%`}}
                />
              </div>
            </div>

            {/* 控制按钮 */}
            <div className="flex items-center gap-1">
              <motion.button whileTap={{scale: 0.85}} onClick={onTogglePlay}
                             className="w-9 h-9 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition-colors"
                             aria-label={isPlaying ? '暂停' : '播放'}>
                {isPlaying ? (
                    <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                ) : (
                    <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                )}
              </motion.button>
              <motion.button whileTap={{scale: 0.85}} onClick={onClose}
                             className="w-9 h-9 bg-white/5 hover:bg-white/15 rounded-full flex items-center justify-center transition-colors"
                             aria-label="关闭">
                <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* 移动端：右上角黑胶迷你播放器 */}
        <motion.div
            initial={{y: -80, opacity: 0}}
            animate={{y: 0, opacity: 1}}
            exit={{y: -80, opacity: 0}}
            className="sm:hidden fixed top-4 right-4 z-[60]"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            onClick={onTogglePlay}
        >
          <motion.div
              className="w-16 h-16 rounded-full overflow-hidden shadow-2xl border-2 border-white/20 cursor-pointer relative"
              animate={isPlaying ? {rotate: 360} : {rotate: 0}}
              transition={isPlaying ? {duration: 8, ease: 'linear', repeat: Infinity} : {duration: 0.4}}
          >
            {coverImage ? (
                <img src={coverImage} alt="" className="w-full h-full object-cover"/>
            ) : (
                <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                  <Music className="w-8 h-8 text-white/80"/>
                </div>
            )}

            {/* 底部半透明条显示歌名 */}
            <div className="absolute inset-x-0 bottom-0 h-5 bg-black/50 backdrop-blur flex items-center justify-center px-1">
              <p className="text-[9px] text-white font-medium truncate leading-none">{media.original_filename}</p>
            </div>
          </motion.div>
        </motion.div>

        {/* 长按菜单 (移动端) */}
        {showMenu && (
            <div className="sm:hidden fixed z-[70] inset-0 bg-black/40 flex items-end justify-center pb-20"
                 onClick={() => setShowMenu(false)}>
              <motion.div
                  initial={{y: 100, opacity: 0}}
                  animate={{y: 0, opacity: 1}}
                  className="bg-neutral-900/95 backdrop-blur-2xl rounded-2xl w-64 p-4 border border-white/10 shadow-2xl"
                  onClick={e => e.stopPropagation()}
              >
                <p className="text-white font-semibold text-center mb-4 truncate">{media.original_filename}</p>
                <div className="space-y-2">
                  <button onClick={() => { setShowMenu(false); onRestore(); }}
                          className="w-full py-3 px-4 bg-white/10 hover:bg-white/20 rounded-xl text-white text-sm font-medium transition-colors flex items-center gap-3">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                    </svg>
                    展开播放器
                  </button>
                  <button onClick={() => { setShowMenu(false); onClose(); }}
                          className="w-full py-3 px-4 bg-red-500/20 hover:bg-red-500/30 rounded-xl text-red-400 text-sm font-medium transition-colors flex items-center gap-3">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                    关闭播放
                  </button>
                </div>
              </motion.div>
            </div>
        )}

      </>
  );
};

/* ========== MiniPlayerWrapper (使用共享 audioRef) ========== */
const MiniPlayerWrapper: React.FC<{
  media: MediaFile;
  fullUrl: string;
  onRestore: () => void;
  onClose: () => void;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  togglePlay: () => void;
  handleSeek?: (t: number) => void;
}> = ({media, fullUrl, onRestore, onClose, audioRef, isPlaying, currentTime, duration, togglePlay}) => {
  const [coverImage, setCoverImage] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${getConfig().API_BASE_URL}/api/v2/media/${media.id}/metadata`, {credentials: 'include'})
        .then(r => r.json())
        .then(result => {
          if (result.success && result.data?.cover_image) setCoverImage(result.data.cover_image);
        })
        .catch(() => {});
  }, [media.id]);

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
      <MiniPlayer
          media={media}
          fullUrl={fullUrl}
          isPlaying={isPlaying}
          onTogglePlay={togglePlay}
          onRestore={onRestore}
          onClose={onClose}
          coverImage={coverImage}
          currentTime={currentTime}
          duration={duration}
          formatTime={formatTime}
          audioRef={audioRef}
      />
  );
};

/* ========== DesktopLyrics (桌面歌词浮动窗口) ========== */
/* ========== AudioLayer (持久音频层) ========== */
export const AudioLayer: React.FC<{ media: MediaFile; onClose: () => void }> = ({media, onClose}) => {
  const fullUrl = getFullMediaUrl(media.url);
  const [minimized, setMinimized] = useState(false);

  // 共享 audio 元素 — 全程由 AudioLayer 持有
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [lyrics, setLyrics] = useState<Array<{ time: number; text: string }>>([]);

  // 歌词高亮状态
  const [activeLineIndex, setActiveLineIndex] = useState(-1);
  const [karaokeProgress, setKaraokeProgress] = useState(0);

  // 桌面歌词设置
  const [showDesktopLyrics, setShowDesktopLyrics] = useState(false);

  // audio 事件监听
  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    const onTime = () => setCurrentTime(a.currentTime);
    const onDur = () => setDuration(a.duration);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnd = () => setIsPlaying(false);
    a.addEventListener('timeupdate', onTime);
    a.addEventListener('loadedmetadata', onDur);
    a.addEventListener('play', onPlay);
    a.addEventListener('pause', onPause);
    a.addEventListener('ended', onEnd);
    return () => { a.removeEventListener('timeupdate', onTime); a.removeEventListener('loadedmetadata', onDur); a.removeEventListener('play', onPlay); a.removeEventListener('pause', onPause); a.removeEventListener('ended', onEnd); };
  }, []);

  const togglePlay = () => {
    const a = audioRef.current;
    if (!a) return;
    if (isPlaying) a.pause(); else a.play();
  };

  const handleSeek = (time: number) => {
    const a = audioRef.current;
    if (a) a.currentTime = time;
  };

  // 加载元数据
  useEffect(() => {
    fetch(`${getConfig().API_BASE_URL}/api/v2/media/${media.id}/metadata`, {credentials: 'include'})
        .then(r => r.json())
        .then(result => {
          if (result.success && result.data) {
            if (result.data.lyrics?.length) setLyrics(result.data.lyrics);
          }
        })
        .catch(() => {});
  }, [media.id]);

  // 桌面歌词默认关闭，用户通过按钮开启
  useEffect(() => {
    // 不再从 localStorage 读取 visible 状态，由用户主动触发
  }, [lyrics]);

  // 更新歌词高亮
  useEffect(() => {
    if (!lyrics.length) return;
    const idx = lyrics.findIndex((l, i) => {
      const next = lyrics[i + 1];
      return currentTime >= l.time && (!next || currentTime < next.time);
    });
    setActiveLineIndex(idx);
    if (idx >= 0) {
      const line = lyrics[idx];
      const nextTime = lyrics[idx + 1]?.time ?? line.time + 3;
      const progress = Math.max(0, Math.min(1, (currentTime - line.time) / (nextTime - line.time)));
      setKaraokeProgress(progress);
    }
  }, [currentTime, lyrics]);

  // ESC 切换最小化
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMinimized(m => !m);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // 共享给子组件
  const sharedAudioProps = {
    audioRef,
    isPlaying,
    currentTime,
    duration,
    togglePlay,
    handleSeek,
  };

  return (
      <>
        {/* audio 永远在这个位置，不被条件分支卸载 */}
        <audio ref={audioRef} src={fullUrl} preload="auto"/>

        {minimized ? (
            <>
              <DesktopLyrics
                  lyrics={lyrics}
                  activeLineIndex={activeLineIndex}
                  karaokeProgress={karaokeProgress}
                  visible={showDesktopLyrics}
                  onVisibilityChange={setShowDesktopLyrics}
              />
              {/* 桌面歌词开关（stopPropagation 防止误触 MiniPlayer 的 togglePlay） */}
              {lyrics.length > 0 && (
                  <button
                      onClick={(e) => { e.stopPropagation(); setShowDesktopLyrics(v => !v); }}
                      onPointerDown={(e) => e.stopPropagation()}
                      className="fixed bottom-24 right-4 z-[66] w-9 h-9 rounded-full bg-black/60 backdrop-blur border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors"
                      aria-label="桌面歌词"
                      title="桌面歌词"
                  >
                    <svg className="w-4 h-4 text-white/70" fill="none" viewBox="0 0 24 24" stroke={showDesktopLyrics ? '#a855f7' : 'currentColor'} strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                    </svg>
                  </button>
              )}
              <MiniPlayerWrapper
                  media={media}
                  fullUrl={fullUrl}
                  onRestore={() => setMinimized(false)}
                  onClose={onClose}
                  {...sharedAudioProps}
              />
            </>
        ) : (
            <div className="fixed inset-0 z-50 flex flex-col bg-black">
              <AudioPlayer
                  media={media}
                  fullUrl={fullUrl}
                  onMinimize={() => setMinimized(true)}
                  {...sharedAudioProps}
              />
            </div>
        )}
      </>
  );
};

/* ---------- PreviewModal (仅非音频) ---------- */
/* ---------- Upload hook ---------- */
