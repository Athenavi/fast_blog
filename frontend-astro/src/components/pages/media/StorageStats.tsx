'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { HardDrive } from 'lucide-react';

interface StorageStatsProps {
  stats: {
    storage_used?: string;
    storage_percentage?: number;
    total_storage?: string;
  };
  loading: boolean;
}

/**
 * 精灵球存储指示器 — 可拖拽、靠边自动隐藏
 *
 * 视觉风格：
 * - 上半球红色，下半球白色，中间黑色分隔线 + 圆形按钮
 * - 存储用量以百分比填充上半球（从分隔线向上）
 * - 悬浮时完全展开显示详情
 * - 可拖拽吸附到左右边缘，松手后自动回缩
 */
export const StorageStats: React.FC<StorageStatsProps> = ({ stats, loading }) => {
  const percentage = stats.storage_percentage ?? 0;
  const used = stats.storage_used || '0 B';

  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [side, setSide] = useState<'left' | 'right'>('right');
  const [offsetX, setOffsetX] = useState(0);
  const ballRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef({ x: 0, offsetX: 0, side: 'right' as 'left' | 'right' });

  // ── 拖拽逻辑 ──
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const el = ballRef.current;
    if (!el) return;
    el.setPointerCapture(e.pointerId);
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX,
      offsetX,
      side,
    };
  }, [offsetX, side]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    setOffsetX(dx);
  }, [isDragging]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    setIsDragging(false);
    const el = ballRef.current;
    if (!el) return;
    el.releasePointerCapture(e.pointerId);

    // 确定吸附边：根据当前位置判断
    const rect = el.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const viewportMid = window.innerWidth / 2;
    const newSide = centerX < viewportMid ? 'left' : 'right';

    setSide(newSide);
    setOffsetX(0);
  }, [isDragging]);

  // 全局 pointermove/up 确保拖拽不掉帧
  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: PointerEvent) => {
      const dx = e.clientX - dragStartRef.current.x;
      setOffsetX(dx);
    };
    const onUp = () => {
      setIsDragging(false);
      const newSide = dragStartRef.current.side;
      setSide(newSide);
      setOffsetX(0);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [isDragging]);

  // ── 计算位置 ──
  // 隐藏时只露出 ~8px 的弧形边缘；悬浮时完全展开
  const hiddenOffset = 52; // 隐藏时露出的像素
  const fullSize = 64;    // 完全展开的尺寸
  const currentOffset = isHovered || isDragging ? 0 : fullSize - hiddenOffset;

  const translateX = side === 'right'
    ? `calc(100% - ${currentOffset}px + ${offsetX}px)`
    : `calc(${currentOffset - fullSize}px + ${offsetX}px)`;

  const clampedPct = Math.min(100, Math.max(0, percentage));

  return (
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
        transform: `translateY(-50%)`,
        [side]: 0,
        translate: side === 'right' ? `calc(${currentOffset - fullSize}px + ${offsetX}px)` : `calc(100% - ${currentOffset}px + ${offsetX}px)`,
        zIndex: 40,
        cursor: isDragging ? 'grabbing' : 'pointer',
        touchAction: 'none',
        userSelect: 'none',
        transition: isDragging ? 'none' : 'translate 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
      }}
      className="select-none"
      title={loading ? '加载中...' : `已用 ${used} (${clampedPct}%)`}
    >
      <div
        style={{
          width: fullSize,
          height: fullSize,
          position: 'relative',
          filter: `drop-shadow(0 4px 12px rgba(0,0,0,0.3))`,
        }}
      >
        {/* 精灵球主体 */}
        <svg viewBox="0 0 64 64" style={{ width: '100%', height: '100%', display: 'block' }}>
          {/* 背景圆（外轮廓） */}
          <circle cx="32" cy="32" r="30" fill="#1a1a2e" stroke="#2a2a4a" strokeWidth="1.5" />

          {/* 上半球 — 红色，按百分比从中间向上填充 */}
          <defs>
            <clipPath id="topHalf">
              <rect x="2" y="2" width="60" height="30" rx="30" />
            </clipPath>
            <clipPath id="fillUp">
              <rect x="2" y={32 - (clampedPct / 100) * 30} width="60" height={(clampedPct / 100) * 30} />
            </clipPath>
          </defs>

          {/* 下半球 — 白色背景 */}
          <circle cx="32" cy="32" r="30" fill="#f0f0f0" />

          {/* 上半球红色填充 */}
          <circle cx="32" cy="32" r="30" fill="#e74c3c" clipPath="url(#topHalf)" />

          {/* 存储用量高光（从中间向上渐变填充） */}
          <circle cx="32" cy="32" r="30" fill="#c0392b" clipPath="url(#fillUp)" opacity="0.3" />

          {/* 中间分隔线 */}
          <line x1="2" y1="32" x2="62" y2="32" stroke="#2a2a4a" strokeWidth="2.5" />

          {/* 中心按钮 — 黑色圆 */}
          <circle cx="32" cy="32" r="8" fill="#2a2a4a" stroke="#1a1a2e" strokeWidth="1.5" />
          <circle cx="32" cy="32" r="5" fill="#f0f0f0" />
          <circle cx="32" cy="32" r="3" fill="#2a2a4a" />

          {/* 悬浮时显示百分比文字 */}
          {isHovered && !loading && (
            <text
              x="32" y="58" textAnchor="middle"
              fill="rgba(255,255,255,0.8)"
              fontSize="7"
              fontWeight="bold"
              fontFamily="system-ui"
            >
              {clampedPct}%
            </text>
          )}
        </svg>

        {/* 拖拽手柄提示 */}
        {!isHovered && !isDragging && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              [side === 'right' ? 'left' : 'right']: -2,
              transform: 'translateY(-50%)',
              width: 3,
              height: 20,
              borderRadius: 2,
              background: 'rgba(255,255,255,0.3)',
            }}
          />
        )}
      </div>

      {/* 悬浮详情浮层 */}
      {isHovered && !loading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            [side === 'right' ? 'right' : 'left']: '100%',
            transform: 'translateY(-50%)',
            marginLeft: side === 'right' ? 8 : 0,
            marginRight: side === 'left' ? 8 : 0,
            background: 'rgba(0,0,0,0.85)',
            backdropFilter: 'blur(8px)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: 8,
            fontSize: 12,
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 2 }}>已用存储</div>
          <div style={{ opacity: 0.7 }}>{used} ({clampedPct}%)</div>
        </div>
      )}
    </div>
  );
};

export default StorageStats;
