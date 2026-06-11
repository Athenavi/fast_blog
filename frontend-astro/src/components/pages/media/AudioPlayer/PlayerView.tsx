import React, {useState, useEffect} from 'react';
import {motion} from 'framer-motion';
import type {MediaFile} from '@/lib/api';
import {getConfig} from '@/lib/config';
import {LyricLine, calcKaraokeProgress} from './helpers';
import VinylRecord from './VinylRecord';
import LyricsPanel from './LyricsPanel';
import ControlsBar from './ControlsBar';

interface PlayerViewProps {
  media: MediaFile;
  fullUrl: string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  togglePlay: () => void;
  handleSeek: (t: number) => void;
  onMinimize?: () => void;
}

const PlayerView: React.FC<PlayerViewProps> = ({
  media, fullUrl, audioRef, isPlaying, currentTime, duration,
  togglePlay, handleSeek, onMinimize,
}) => {
  const [volume, setVolume] = useState(1);
  const [showLyrics, setShowLyrics] = useState(false);

  // 音频元数据
  const [coverImage, setCoverImage] = useState<string | null>(null);
  const [lyrics, setLyrics] = useState<LyricLine[]>([]);
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

  const handleVolumeChange = (vol: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = vol;
    setVolume(vol);
  };

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

        {/* Left: Vinyl */}
        <VinylRecord
          coverImage={coverImage}
          loadingMetadata={loadingMetadata}
          isPlaying={isPlaying}
          onMinimize={onMinimize}
        />

        {/* Right: Lyrics */}
        <LyricsPanel
          media={media}
          coverImage={coverImage}
          lyrics={lyrics}
          showLyrics={showLyrics}
          onToggleLyrics={() => setShowLyrics(v => !v)}
          activeLineIndex={activeLineIndex}
          karaokeProgress={karaokeProgress}
          onMinimize={onMinimize}
        />
      </div>

      {/* ====== Bottom Controls Bar ====== */}
      <ControlsBar
        media={media}
        coverImage={coverImage}
        currentTime={currentTime}
        duration={duration}
        volume={volume}
        isPlaying={isPlaying}
        onSeek={handleSeek}
        onTogglePlay={togglePlay}
        onVolumeChange={handleVolumeChange}
        onMinimize={onMinimize}
      />
    </div>
  );
};

export default PlayerView;
