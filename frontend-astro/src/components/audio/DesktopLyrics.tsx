'use client';

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {motion, AnimatePresence} from 'framer-motion';

/* ---------- Types ---------- */

interface LyricLine {
  time: number;
  text: string;
}

interface LyricsSettings {
  x: number;
  y: number;
  fontSize: number;
  fontFamily: string;
  opacity: number;
  gradientId: string;
}

const GRADIENTS: { id: string; label: string; from: string; via: string; to: string; shadow: string }[] = [
  {id: 'purple-pink', label: '紫粉', from: '#a855f7', via: '#d946ef', to: '#ec4899', shadow: 'rgba(168,85,247,0.5)'},
  {id: 'cyan-blue', label: '青蓝', from: '#06b6d4', via: '#3b82f6', to: '#6366f1', shadow: 'rgba(59,130,246,0.5)'},
  {id: 'green-emerald', label: '翠绿', from: '#34d399', via: '#10b981', to: '#059669', shadow: 'rgba(16,185,129,0.5)'},
  {id: 'orange-rose', label: '暖橙', from: '#fb923c', via: '#f43f5e', to: '#e11d48', shadow: 'rgba(244,63,94,0.5)'},
  {id: 'white-glow', label: '白辉', from: '#ffffff', via: '#e2e8f0', to: '#94a3b8', shadow: 'rgba(255,255,255,0.4)'},
  {id: 'gold-amber', label: '金色', from: '#fbbf24', via: '#f59e0b', to: '#d97706', shadow: 'rgba(245,158,11,0.5)'},
];

const FONTS: { value: string; label: string }[] = [
  {value: 'system-ui, sans-serif', label: '系统'},
  {value: '"PingFang SC", "Microsoft YaHei", sans-serif', label: '雅黑'},
  {value: '"Noto Sans SC", sans-serif', label: 'Noto'},
  {value: '"Songti SC", "SimSun", serif', label: '宋体'},
  {value: '"STKaiti", "KaiTi", serif', label: '楷体'},
  {value: 'monospace', label: '等宽'},
];

const LS_KEY = 'fastblog_desktop_lyrics';
const DEFAULT_SETTINGS: LyricsSettings = {
  x: 50, y: 50, fontSize: 18, fontFamily: 'system-ui, sans-serif', opacity: 90, gradientId: 'purple-pink',
};

function loadSettings(): LyricsSettings {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? {...DEFAULT_SETTINGS, ...JSON.parse(raw)} : DEFAULT_SETTINGS;
  } catch { return DEFAULT_SETTINGS; }
}

function saveSettings(s: LyricsSettings) {
  localStorage.setItem(LS_KEY, JSON.stringify(s));
}

/* ---------- Tokenize ---------- */

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

/* ========== Settings Panel ========== */

const SettingsPanel: React.FC<{
  settings: LyricsSettings;
  onChange: (s: LyricsSettings) => void;
  onClose: () => void;
  prevLyric: string | null;
  nextLyric: string | null;
}> = ({settings, onChange, onClose, prevLyric, nextLyric}) => {
  const panelRef = useRef<HTMLDivElement>(null);

  return (
      <motion.div
          ref={panelRef}
          initial={{opacity: 0, y: 10, scale: 0.95}}
          animate={{opacity: 1, y: 0, scale: 1}}
          exit={{opacity: 0, y: 10, scale: 0.95}}
          className="fixed bottom-6 right-6 z-[70] bg-neutral-900/95 backdrop-blur-2xl rounded-2xl border border-white/10 shadow-2xl p-4 w-72"
          onClick={e => e.stopPropagation()}
      >
        {/* 标题 + 关闭 */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-white text-sm font-semibold">桌面歌词设置</span>
          <button onClick={onClose} className="w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/50 text-xs">✕</button>
        </div>

        {/* 字号 */}
        <div className="mb-3">
          <label className="text-white/50 text-xs block mb-1">字号</label>
          <div className="flex items-center gap-2">
            <button onClick={() => onChange({...settings, fontSize: Math.max(12, settings.fontSize - 1)})}
                    className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 text-sm font-bold">A−</button>
            <span className="text-white text-sm text-center w-10 tabular-nums">{settings.fontSize}</span>
            <button onClick={() => onChange({...settings, fontSize: Math.min(40, settings.fontSize + 1)})}
                    className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 text-sm font-bold">A+</button>
          </div>
        </div>

        {/* 字体 */}
        <div className="mb-3">
          <label className="text-white/50 text-xs block mb-1">字体</label>
          <div className="flex flex-wrap gap-1.5">
            {FONTS.map(f => (
                <button key={f.value}
                        onClick={() => onChange({...settings, fontFamily: f.value})}
                        className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                            settings.fontFamily === f.value
                                ? 'bg-purple-600/40 text-purple-300 border border-purple-500/40'
                                : 'bg-white/10 hover:bg-white/20 text-white/70 border border-transparent'
                        }`}
                        style={{fontFamily: f.value}}
                >{f.label}</button>
            ))}
          </div>
        </div>

        {/* 高亮颜色 */}
        <div className="mb-3">
          <label className="text-white/50 text-xs block mb-1">高亮颜色</label>
          <div className="flex flex-wrap gap-1.5">
            {GRADIENTS.map(g => (
                <button key={g.id}
                        onClick={() => onChange({...settings, gradientId: g.id})}
                        className={`w-7 h-7 rounded-full transition-all ${
                            settings.gradientId === g.id ? 'ring-2 ring-white scale-110' : ''
                        }`}
                        style={{background: `linear-gradient(135deg, ${g.from}, ${g.via}, ${g.to})`}}
                        title={g.label}
                />
            ))}
          </div>
        </div>

        {/* 透明度 */}
        <div className="mb-3">
          <label className="text-white/50 text-xs block mb-1">透明度 ({settings.opacity}%)</label>
          <input type="range" min={30} max={100} value={settings.opacity}
                 onChange={e => onChange({...settings, opacity: parseInt(e.target.value)})}
                 className="w-full h-1 bg-white/20 rounded-full appearance-none cursor-pointer accent-purple-500"
                 style={{background: `linear-gradient(to right, #a855f7 ${settings.opacity}%, rgba(255,255,255,0.15) ${settings.opacity}%)`}}
          />
        </div>

        {/* 歌词预览 */}
        <div className="border-t border-white/10 pt-3 mt-1">
          <label className="text-white/50 text-xs block mb-2">预览</label>
          <div className="space-y-2 text-center">
            {prevLyric && (
                <p className="text-white/30 text-xs truncate" style={{fontFamily: settings.fontFamily, fontSize: settings.fontSize - 4}}>
                  {prevLyric}
                </p>
            )}
            {nextLyric && (
                <p className="text-white/60 text-sm truncate" style={{fontFamily: settings.fontFamily, fontSize: settings.fontSize}}>
                  {nextLyric}
                </p>
            )}
          </div>
        </div>
      </motion.div>
  );
};

/* ========== DesktopLyrics Main Component ========== */

const DesktopLyrics: React.FC<{
  lyrics: LyricLine[];
  activeLineIndex: number;
  karaokeProgress: number;
  visible: boolean;
  onVisibilityChange: (v: boolean) => void;
}> = ({lyrics, activeLineIndex, karaokeProgress, visible, onVisibilityChange}) => {
  const [settings, setSettings] = useState<LyricsSettings>(loadSettings);
  const [showSettings, setShowSettings] = useState(false);
  const [prevActiveIndex, setPrevActiveIndex] = useState(-1);
  const dragRef = useRef<{
    startX: number; startY: number;
    origX: number; origY: number;
    dragging: boolean;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 持久化
  useEffect(() => { saveSettings(settings); }, [settings]);

  // 跟踪上一行索引用于动画
  useEffect(() => {
    if (activeLineIndex >= 0 && activeLineIndex !== prevActiveIndex) {
      setPrevActiveIndex(activeLineIndex);
    }
  }, [activeLineIndex, prevActiveIndex]);

  // ESC 关闭歌词
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showSettings) setShowSettings(false);
        else onVisibilityChange(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [showSettings, onVisibilityChange]);

  // 预览行
  const currentLyric = activeLineIndex >= 0 ? lyrics[activeLineIndex] : null;
  const prevLyric = activeLineIndex > 0 ? lyrics[activeLineIndex - 1] : null;
  const nextLyric = activeLineIndex >= 0 && activeLineIndex + 1 < lyrics.length ? lyrics[activeLineIndex + 1] : null;

  const gradient = GRADIENTS.find(g => g.id === settings.gradientId) ?? GRADIENTS[0];

  // ── 拖拽（pointer events 统一鼠标+触控）──
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragRef.current = {
      startX: e.clientX, startY: e.clientY,
      origX: settings.x, origY: settings.y,
      dragging: false,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [settings.x, settings.y]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.dragging = true;
    setSettings(s => ({
      ...s,
      x: Math.max(0, Math.min(95, dragRef.current!.origX + dx / window.innerWidth * 100)),
      y: Math.max(0, Math.min(90, dragRef.current!.origY + dy / window.innerHeight * 100)),
    }));
  }, []);

  const onPointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  if (!visible || !lyrics.length) return null;

  // 当前行的高亮 tokens
  const highlightedTokens = currentLyric ? (() => {
    const tokens = tokenizeText(currentLyric.text);
    const highlightCount = Math.floor(tokens.length * karaokeProgress);
    return tokens.map((t, i) => ({
      token: t,
      highlighted: i < highlightCount,
      transitioning: i === highlightCount - 1 && karaokeProgress < 1,
      clipProgress: i === highlightCount - 1 && karaokeProgress < 1
          ? (karaokeProgress * tokens.length - i)
          : (i < highlightCount ? 1 : 0),
    }));
  })() : [];

  return (
      <>
        {/* ── 歌词主窗口 ── */}
        <motion.div
            ref={containerRef}
            className="fixed z-[65] select-none touch-none"
            style={{
              left: `${settings.x}%`,
              top: `${settings.y}%`,
              transform: 'translate(-50%, -50%)',
              fontSize: `${settings.fontSize}px`,
              fontFamily: settings.fontFamily,
              maxWidth: 'min(70vw, 800px)',
              width: 'max-content',
            }}
            initial={{opacity: 0, scale: 0.9}}
            animate={{opacity: settings.opacity / 100, scale: 1}}
            transition={{duration: 0.25}}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onDoubleClick={() => onVisibilityChange(false)}
        >
          <div
              className="bg-black/55 backdrop-blur-2xl rounded-2xl px-8 py-5 border border-white/8 shadow-2xl text-center leading-relaxed cursor-grab active:cursor-grabbing transition-shadow hover:shadow-purple-500/5"
              style={{minWidth: '320px'}}
          >
            {/* 上一行（退场） */}
            <AnimatePresence mode="popLayout">
              {prevLyric && activeLineIndex > 0 && prevActiveIndex === activeLineIndex - 1 && (
                  <motion.p
                      key={`prev-${activeLineIndex}`}
                      initial={{opacity: 1, y: 0}}
                      animate={{opacity: 0.25, y: -8}}
                      exit={{opacity: 0, y: -20, scale: 0.95}}
                      transition={{duration: 0.35, ease: 'easeOut'}}
                      className="text-white/40 text-sm truncate mb-2"
                      style={{fontSize: Math.max(12, settings.fontSize - 4)}}
                  >
                    {prevLyric.text}
                  </motion.p>
              )}
            </AnimatePresence>

            {/* 当前行（入场 + 逐字高亮） */}
            {currentLyric && (
                <motion.div
                    key={`curr-${activeLineIndex}`}
                    initial={{opacity: 0, y: 16, filter: 'blur(4px)'}}
                    animate={{opacity: 1, y: 0, filter: 'blur(0px)'}}
                    exit={{opacity: 0, y: -16, filter: 'blur(4px)'}}
                    transition={{duration: 0.4, ease: [0.16, 1, 0.3, 1]}}
                    className="font-bold tracking-wide leading-relaxed"
                >
                  {highlightedTokens.map((item, ti) => {
                    if (item.token === ' ') return <span key={ti} className="inline-block" style={{width: '0.3em'}}>&nbsp;</span>;
                    return (
                        <span key={ti} className="relative inline-block mx-[0.5px]">
                      {/* 未高亮 */}
                      <span className={item.highlighted ? 'text-transparent' : 'text-white/60'}>
                        {item.token}
                      </span>
                          {/* 高亮渐变 */}
                          {item.highlighted && (
                              <span
                                  className="absolute inset-0 bg-clip-text text-transparent"
                                  style={{
                                    background: `linear-gradient(135deg, ${gradient.from}, ${gradient.via}, ${gradient.to})`,
                                    WebkitBackgroundClip: 'text',
                                    filter: `drop-shadow(0 0 ${settings.fontSize > 20 ? 12 : 8}px ${gradient.shadow})`,
                                  }}
                              >
                            {item.token}
                          </span>
                          )}
                          {/* 过渡 clipPath */}
                          {item.transitioning && (
                              <span className="absolute inset-0 overflow-hidden" style={{color: 'transparent'}}>
                            <span
                                className="absolute inset-0 bg-clip-text text-transparent"
                                style={{
                                  background: `linear-gradient(135deg, ${gradient.from}, ${gradient.via}, ${gradient.to})`,
                                  WebkitBackgroundClip: 'text',
                                  clipPath: `inset(0 ${(1 - item.clipProgress) * 100}% 0 0)`,
                                  filter: `drop-shadow(0 0 ${settings.fontSize > 20 ? 14 : 10}px ${gradient.shadow})`,
                                }}
                            >
                              {item.token}
                            </span>
                          </span>
                          )}
                    </span>
                    );
                  })}
                </motion.div>
            )}

            {/* 无歌词占位 */}
            {!currentLyric && (
                <p className="text-white/30 text-sm">等待播放...</p>
            )}

            {/* 下一行（入场预告） */}
            <AnimatePresence mode="popLayout">
              {nextLyric && activeLineIndex >= 0 && (
                  <motion.p
                      key={`next-${activeLineIndex}`}
                      initial={{opacity: 0, y: 12}}
                      animate={{opacity: 0.3, y: 6}}
                      exit={{opacity: 0, y: 20}}
                      transition={{duration: 0.4, delay: 0.15, ease: 'easeOut'}}
                      className="text-white/25 text-sm truncate mt-2"
                      style={{fontSize: Math.max(11, settings.fontSize - 6)}}
                  >
                    {nextLyric.text}
                  </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* ── 悬停控制条 ── */}
          <div
              className="flex items-center justify-center gap-2 mt-2 opacity-0 hover:opacity-100 transition-opacity duration-200"
              style={{pointerEvents: 'auto'}}
          >
            <button onClick={() => onVisibilityChange(false)}
                    className="w-7 h-7 rounded-full bg-black/50 backdrop-blur border border-white/10 hover:bg-white/15 flex items-center justify-center text-white/50 text-xs transition-colors"
                    title="关闭桌面歌词">✕</button>
            <button onClick={() => setShowSettings(v => !v)}
                    className={`w-7 h-7 rounded-full backdrop-blur border flex items-center justify-center text-xs transition-colors ${
                        showSettings ? 'bg-purple-600/40 border-purple-500/40 text-purple-300' : 'bg-black/50 border-white/10 hover:bg-white/15 text-white/50'
                    }`}
                    title="歌词设置">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </button>
          </div>
        </motion.div>

        {/* ── 设置面板 ── */}
        <AnimatePresence>
          {showSettings && (
              <SettingsPanel
                  settings={settings}
                  onChange={setSettings}
                  onClose={() => setShowSettings(false)}
                  prevLyric={prevLyric?.text ?? null}
                  nextLyric={nextLyric?.text ?? null}
              />
          )}
        </AnimatePresence>
      </>
  );
};

export default DesktopLyrics;
export {tokenizeText, GRADIENTS, FONTS};
export type {LyricsSettings, LyricLine};
