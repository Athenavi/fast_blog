/**
 * 响应式图片 hook - useResponsiveImage
 * 根据屏幕断点、DPR 和网络状态自动选择最优图片尺寸
 * 支持 srcset/sizes 自动生成、懒加载和占位图
 */

import {useCallback, useMemo, useState} from 'react';
import {BREAKPOINTS, useBreakpoint, useIsMobile} from './useMediaQuery';
import {useNetworkState} from './useNetworkState';

export interface ResponsiveImageOptions {
  /** 基础图片 URL (不含尺寸后缀) */
  src: string;
  /** 图片最大显示宽度 (px) */
  maxWidth?: number;
  /** 是否启用懒加载 */
  lazy?: boolean;
  /** 低质量占位图 (可选) */
  placeholder?: string;
  /** 网络较差时降级 */
  degradeOnSlowNetwork?: boolean;
}

export interface ResponsiveImageResult {
  /** 优化后的 src */
  src: string;
  /** srcset 属性值 */
  srcset: string;
  /** sizes 属性值 */
  sizes: string;
  /** 是否移动端 */
  isMobile: boolean;
  /** 当前断点 */
  breakpoint: keyof typeof BREAKPOINTS;
  /** 加载状态 */
  loading: boolean;
  /** 错误状态 */
  error: boolean;
  /** onLoad 回调 */
  onLoad: () => void;
  /** onError 回调 */
  onError: () => void;
}

/**
 * 从图片URL生成不同尺寸的变体
 * 支持常见 CDN 图片处理参数
 */
function generateSrcsetVariants(
  baseUrl: string,
  widths: number[],
  quality?: number
): string {
  return widths
    .map(width => {
      let url = baseUrl;
      // 支持阿里云OSS / Cloudinary 等常见格式
      if (url.includes('.aliyuncs.com') || url.includes('oss-cn')) {
        url = `${url}?x-oss-process=image/resize,w_${width}`;
      } else if (url.includes('cloudinary.com')) {
        url = url.replace('/upload/', `/upload/w_${width}/`);
      } else {
        // 通用格式: 在扩展名前加 -{width}w
        const parts = url.split('.');
        if (parts.length > 1) {
          const ext = parts.pop();
          url = `${parts.join('.')}-${width}w.${ext}`;
        }
      }

      if (quality) {
        if (url.includes('?')) {
          url = `${url}&q=${quality}`;
        } else {
          url = `${url}?q=${quality}`;
        }
      }

      return `${url} ${width}w`;
    })
    .join(', ');
}

/**
 * 根据断点生成 sizes 属性
 */
function generateSizes(maxWidth: number, breakpoint: keyof typeof BREAKPOINTS): string {
  const size = Math.min(maxWidth, BREAKPOINTS[breakpoint]);
  return `(max-width: ${BREAKPOINTS.sm}px) 100vw, (max-width: ${BREAKPOINTS.lg}px) 50vw, ${size}px`;
}

/**
 * 根据网络状态调整图片质量
 */
function getQualityForNetwork(online: boolean, saveData: boolean): number {
  if (!online) return 0; // 离线不加载
  if (saveData) return 60; // 省流模式低质量
  return 80; // 默认质量
}

export function useResponsiveImage({
                                     src,
                                     maxWidth = 800,
                                     lazy = true,
                                     placeholder,
                                     degradeOnSlowNetwork = true,
                                   }: ResponsiveImageOptions): ResponsiveImageResult {
  const breakpoint = useBreakpoint();
  const isMobile = useIsMobile();
  const {online, saveData} = useNetworkState();
  const [loading, setLoading] = useState(!lazy);
  const [error, setError] = useState(false);

  // 根据网络状态决定图片质量
  const quality = useMemo(
    () => (degradeOnSlowNetwork ? getQualityForNetwork(online, saveData) : 80),
    [online, saveData, degradeOnSlowNetwork]
  );

  // 根据断点决定加载的宽度范围
  const widths = useMemo(() => {
    if (isMobile) return [320, 480, 640];
    if (breakpoint === 'md') return [480, 640, 768];
    if (breakpoint === 'lg') return [640, 768, 1024];
    return [768, 1024, 1280, 1536];
  }, [isMobile, breakpoint]);

  // 生成 srcset
  const srcset = useMemo(() => {
    if (quality === 0) return ''; // 离线不加载
    return generateSrcsetVariants(src, widths, quality);
  }, [src, widths, quality]);

  // 生成 sizes
  const sizes = useMemo(
    () => generateSizes(maxWidth, breakpoint),
    [maxWidth, breakpoint]
  );

  // 最终 src (离线时使用 placeholder)
  const finalSrc = useMemo(() => {
    if (quality === 0 && placeholder) return placeholder;
    return src;
  }, [src, quality, placeholder]);

  const onLoad = useCallback(() => {
    setLoading(false);
  }, []);

  const onError = useCallback(() => {
    setLoading(false);
    setError(true);
  }, []);

  return {
    src: error && placeholder ? placeholder : finalSrc,
    srcset,
    sizes,
    isMobile,
    breakpoint,
    loading,
    error,
    onLoad,
    onError,
  };
}

export default useResponsiveImage;
