import React, {useRef, useEffect} from 'react';
import {motion} from 'framer-motion';
import {Music} from 'lucide-react';
import type {MediaFile} from '@/lib/api';
import {LyricLine, tokenizeText, calcKaraokeProgress} from './helpers';

interface LyricsPanelProps {
  media: MediaFile;
  coverImage: string | null;
  lyrics: LyricLine[];
  showLyrics: boolean;
  onToggleLyrics: () => void;
  activeLineIndex: number;
  karaokeProgress: number;
  onMinimize?: () => void;
}

const LyricsPanel: React.FC<LyricsPanelProps> = ({
  media, coverImage, lyrics, showLyrics, onToggleLyrics,
  activeLineIndex, karaokeProgress, onMinimize,
}) => {
  const lyricsContainerRef = useRef<HTMLDivElement>(null);

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

  return (
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
          onClick={onToggleLyrics}
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
  );
};

export default LyricsPanel;
