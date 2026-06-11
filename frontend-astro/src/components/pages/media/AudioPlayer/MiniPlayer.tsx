import React, {useState, useEffect, useRef} from 'react';
import {motion} from 'framer-motion';
import {Music} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import {getConfig} from '@/lib/config';
import {formatTime} from './helpers';

/* ========== MiniPlayer (最小化播放) ========== */

interface MiniPlayerProps {
  media: MediaFile;
  fullUrl: string;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onRestore: () => void;
  onClose: () => void;
  coverImage: string | null;
  currentTime: number;
  duration: number;
  formatTimeFn: (t: number) => string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
}

const MiniPlayer: React.FC<MiniPlayerProps> = ({
  media, coverImage, isPlaying, onTogglePlay, onRestore, onClose,
  currentTime, duration, audioRef,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

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

interface MiniPlayerWrapperProps {
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
}

const MiniPlayerWrapper: React.FC<MiniPlayerWrapperProps> = ({
  media, fullUrl, onRestore, onClose, audioRef, isPlaying, currentTime, duration, togglePlay,
}) => {
  const [coverImage, setCoverImage] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${getConfig().API_BASE_URL}/api/v2/media/${media.id}/metadata`, {credentials: 'include'})
      .then(r => r.json())
      .then(result => {
        if (result.success && result.data?.cover_image) setCoverImage(result.data.cover_image);
      })
      .catch(() => {});
  }, [media.id]);

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
      formatTimeFn={formatTime}
      audioRef={audioRef}
    />
  );
};

export {MiniPlayer, MiniPlayerWrapper};
