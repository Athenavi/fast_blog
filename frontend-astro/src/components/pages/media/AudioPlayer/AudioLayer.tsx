import React, {useRef, useState, useEffect} from 'react';
import type {MediaFile} from '@/lib/api';
import {getConfig} from '@/lib/config';
import {getFullMediaUrl} from '@/lib/utils';
import {LyricLine} from './helpers';
import PlayerView from './PlayerView';
import {MiniPlayerWrapper} from './MiniPlayer';
import DesktopLyrics from '@/components/audio/DesktopLyrics';

/* ========== AudioLayer (持久音频层) ========== */

const AudioLayer: React.FC<{ media: MediaFile; onClose: () => void }> = ({media, onClose}) => {
  const fullUrl = getFullMediaUrl(media.url);
  const [minimized, setMinimized] = useState(false);

  // 共享 audio 元素 — 全程由 AudioLayer 持有
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [lyrics, setLyrics] = useState<LyricLine[]>([]);

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
    return () => {
      a.removeEventListener('timeupdate', onTime);
      a.removeEventListener('loadedmetadata', onDur);
      a.removeEventListener('play', onPlay);
      a.removeEventListener('pause', onPause);
      a.removeEventListener('ended', onEnd);
    };
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
          <PlayerView
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

export default AudioLayer;
