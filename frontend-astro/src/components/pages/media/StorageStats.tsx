'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';

interface StorageStatsProps {
  stats: {
    storage_used?: string;
    storage_percentage?: number;
    total_storage?: string;
  };
  loading: boolean;
}

/** 根据使用率返回配色方案 */
function getUsageColors(pct: number) {
  if (pct >= 90) return { liquid: '#ef4444', glow: '#ef444480', bg: '#450a0a', text: '#fca5a5' };
  if (pct >= 80) return { liquid: '#f97316', glow: '#f9731680', bg: '#431407', text: '#fdba74' };
  if (pct >= 60) return { liquid: '#eab308', glow: '#eab30880', bg: '#422006', text: '#fde047' };
  return { liquid: '#22c55e', glow: '#22c55e80', bg: '#052e16', text: '#86efac' };
}

/**
 * 液态球存储指示器 — 360 风格内部流动液体动画
 *
 * 特性：
 * - 内部液体流动动画，双层波浪方向相反产生立体感
 * - 配色随使用率变化：绿(<60%) → 黄(60-80%) → 橙(80-90%) → 红(>90%)
 * - 可拖拽吸附到左右边缘
 * - 默认缩在边缘只露出弧形手柄，悬停展开
 */
export const StorageStats: React.FC<StorageStatsProps> = ({ stats, loading }) => {
  const percentage = stats.storage_percentage ?? 0;
  const used = stats.storage_used || '0 B';
  const clampedPct = Math.min(100, Math.max(0, percentage));
  const colors = getUsageColors(clampedPct);
  const fullSize = 68;

  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [side, setSide] = useState<'left' | 'right'>('right');
  const [offsetX, setOffsetX] = useState(0);
  const ballRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef({ x: 0, side: 'right' as 'left' | 'right' });

  // ── 拖拽 ──
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const el = ballRef.current;
    if (!el) return;
    el.setPointerCapture(e.pointerId);
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, side };
  }, [side]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    setOffsetX(e.clientX - dragStartRef.current.x);
  }, [isDragging]);

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
    const el = ballRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    setSide(centerX < window.innerWidth / 2 ? 'left' : 'right');
    setOffsetX(0);
  }, []);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: PointerEvent) => setOffsetX(e.clientX - dragStartRef.current.x);
    const onUp = () => { setIsDragging(false); setOffsetX(0); };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => { window.removeEventListener('pointermove', onMove); window.removeEventListener('pointerup', onUp); };
  }, [isDragging]);

  const hiddenOffset = fullSize - 10;
  const currentOffset = isHovered || isDragging ? 0 : hiddenOffset;

  const fillHeight = (clampedPct / 100) * fullSize;

  const waveStyle = (delay: number, dir: number): React.CSSProperties => ({
    position: 'absolute',
    bottom: fillHeight - 8,
    left: 0,
    width: '200%',
    height: 16,
    borderRadius: '50%',
    background: colors.liquid,
    opacity: 0.55,
    animation: `storageWave ${3 + delay}s ease-in-out infinite alternate`,
    animationDelay: `${delay}s`,
    transform: `translateX(${dir * -25}%)`,
    pointerEvents: 'none',
    willChange: 'transform',
  });

  return (
    <>
      {/* wave keyframes injected once */}
      <style>{`
        @keyframes storageWave {
          0%   { transform: translateX(-30%) scaleY(1); }
          50%  { transform: translateX(10%) scaleY(1.6); }
          100% { transform: translateX(-30%) scaleY(1); }
        }
        @keyframes storageWave2 {
          0%   { transform: translateX(20%) scaleY(1.2); }
          50%  { transform: translateX(-20%) scaleY(0.8); }
          100% { transform: translateX(20%) scaleY(1.2); }
        }
        @keyframes storagePulse {
          0%, 100% { opacity: 0.8; }
          50% { opacity: 1; }
        }
      `}</style>

      <div
        ref={ballRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => { if (!isDragging) setIsHovered(false); }}
        style={{
          position: 'fixed',
          top: '50%',
          [side]: 0,
          translate: side === 'right'
            ? `calc(${currentOffset - fullSize}px + ${offsetX}px)`
            : `calc(100% - ${currentOffset}px + ${offsetX}px)`,
          transform: 'translateY(-50%)',
          zIndex: 40,
          cursor: isDragging ? 'grabbing' : 'pointer',
          touchAction: 'none',
          userSelect: 'none',
          transition: isDragging ? 'none' : 'translate 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
        title={loading ? '加载中...' : `已用 ${used} (${clampedPct}%)`}
      >
        {/* 主体容器 */}
        <div
          style={{
            width: fullSize,
            height: fullSize,
            borderRadius: '50%',
            position: 'relative',
            overflow: 'hidden',
            background: colors.bg,
            boxShadow: `0 0 0 2px ${colors.liquid}44, 0 0 20px ${colors.glow}`,
            transition: 'box-shadow 0.3s, background 0.6s',
          }}
        >
          {/* 液体填充（从底部往上） */}
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: `${fillHeight}px`,
              background: `linear-gradient(180deg, ${colors.liquid}dd, ${colors.liquid}99)`,
              transition: 'height 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.6s',
            }}
          />

          {/* 波浪层 1 */}
          <div
            style={{
              ...waveStyle(0, -1),
              animationName: 'storageWave',
            }}
          />
          {/* 波浪层 2（反向） */}
          <div
            style={{
              ...waveStyle(0.5, 1),
              animationName: 'storageWave2',
              opacity: 0.35,
              height: 14,
            }}
          />

          {/* 高光反射 */}
          <div
            style={{
              position: 'absolute',
              top: '8%',
              left: '18%',
              width: '35%',
              height: '25%',
              borderRadius: '50%',
              background: 'linear-gradient(180deg, rgba(255,255,255,0.3), transparent)',
              pointerEvents: 'none',
            }}
          />

          {/* 外圈扫描环 */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              border: `2px solid ${colors.liquid}66`,
              animation: 'storagePulse 2.5s ease-in-out infinite',
              pointerEvents: 'none',
            }}
          />

          {/* 百分比文字 */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: colors.text,
              textShadow: '0 1px 4px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
              transition: 'color 0.6s',
            }}
          >
            <span style={{ fontSize: 18, fontWeight: 800, lineHeight: 1 }}>
              {loading ? '..' : clampedPct}
            </span>
            <span style={{ fontSize: 8, opacity: 0.8, marginTop: -1 }}>%</span>
          </div>
        </div>

        {/* 拖拽手柄 */}
        {!isHovered && !isDragging && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              [side === 'right' ? 'left' : 'right']: -3,
              transform: 'translateY(-50%)',
              width: 4,
              height: 22,
              borderRadius: 2,
              background: `${colors.liquid}66`,
              transition: 'background 0.6s',
            }}
          />
        )}

        {/* 悬浮详情 */}
        {isHovered && !loading && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              [side === 'right' ? 'right' : 'left']: '100%',
              transform: 'translateY(-50%)',
              marginLeft: side === 'right' ? 10 : 0,
              marginRight: side === 'left' ? 10 : 0,
              background: 'rgba(0,0,0,0.85)',
              backdropFilter: 'blur(10px)',
              color: '#fff',
              padding: '8px 14px',
              borderRadius: 10,
              fontSize: 12,
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              border: `1px solid ${colors.liquid}44`,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 2, color: colors.text }}>
              存储使用
            </div>
            <div style={{ opacity: 0.7 }}>{used} · {clampedPct}%</div>
          </div>
        )}
      </div>
    </>
  );
};

export default StorageStats;
