import React, {useState} from 'react';
import {motion} from 'framer-motion';
import {Music} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import {formatTime} from './helpers';

interface ControlsBarProps {
  media: MediaFile;
  coverImage: string | null;
  currentTime: number;
  duration: number;
  volume: number;
  isPlaying: boolean;
  onSeek: (t: number) => void;
  onTogglePlay: () => void;
  onVolumeChange: (vol: number) => void;
  onMinimize?: () => void;
}

const ControlsBar: React.FC<ControlsBarProps> = ({
  media, coverImage, currentTime, duration, volume, isPlaying,
  onSeek, onTogglePlay, onVolumeChange, onMinimize,
}) => {
  const [repeatMode, setRepeatMode] = useState<'off' | 'one' | 'all'>('off');
  const [isLiked, setIsLiked] = useState(false);
  const [showPlaylist, setShowPlaylist] = useState(false);
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSeek(parseFloat(e.target.value));
  };

  const handleVolumeSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onVolumeChange(parseFloat(e.target.value));
  };

  return (
    <div className="flex-shrink-0 bg-black/90 backdrop-blur-2xl border-t border-white/10"
      style={{paddingBottom: 'env(safe-area-inset-bottom, 0px)'}}>

      {/* --- Progress Bar --- */}
      <div className="px-4 pt-3 pb-1">
        <div className="relative h-6 flex items-center -my-1">
          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={handleProgressChange}
            className="absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer z-10 opacity-0"
            style={{touchAction: 'none'}}
            aria-label="播放进度"
          />
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
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill={isLiked ? '#ec4899' : 'none'}
              stroke={isLiked ? '#ec4899' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
            </svg>
          </motion.button>
        </div>

        {/* Center: Playback controls */}
        <div className="flex items-center justify-center gap-1 sm:gap-3">
          {/* Rewind 10s (仅桌面) */}
          <motion.button
            whileTap={{scale: 0.85}}
            onClick={() => onSeek(Math.max(0, currentTime - 10))}
            className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] items-center justify-center hidden sm:flex"
            aria-label="后退10秒"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
          </motion.button>

          {/* Prev (restart) */}
          <motion.button
            whileTap={{scale: 0.85}}
            onClick={() => onSeek(0)}
            className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="重新播放"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
          </motion.button>

          {/* Play/Pause (large) */}
          <motion.button
            whileTap={{scale: 0.9}}
            onClick={onTogglePlay}
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
            onClick={() => onSeek(Math.min(duration, currentTime + 10))}
            className="text-white/50 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="前进10秒"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
          </motion.button>

          {/* Forward 10s (仅桌面) */}
          <motion.button
            whileTap={{scale: 0.85}}
            onClick={() => onSeek(Math.min(duration, currentTime + 10))}
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
            <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none"
              stroke={repeatMode !== 'off' ? '#a855f7' : 'rgba(255,255,255,0.4)'} strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
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
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
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
                  onChange={handleVolumeSliderChange}
                  className="w-24 h-1.5 bg-white/20 rounded-full appearance-none cursor-pointer accent-purple-500"
                  style={{
                    background: `linear-gradient(to right, #a855f7 ${volume * 100}%, rgba(255,255,255,0.15) ${volume * 100}%)`,
                  }}
                  aria-label="音量滑块"
                />
              </div>
            )}
          </div>

          {/* Playlist toggle (hidden on mobile) */}
          <motion.button
            whileTap={{scale: 0.85}}
            onClick={() => setShowPlaylist(!showPlaylist)}
            className="hidden sm:block p-2 min-w-[44px] min-h-[44px]"
            aria-label="播放列表"
          >
            <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
            </svg>
          </motion.button>
        </div>
      </div>
    </div>
  );
};

export default ControlsBar;
