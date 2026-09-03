/**
 * ProfilerDevWrapper - 开发环境性能分析器
 * 仅在开发模式下渲染 React Profiler，生产模式下直接渲染子组件
 *
 * 使用方式:
 * ```tsx
 * <ProfilerDevWrapper id="article-list">
 *   <ArticleList />
 * </ProfilerDevWrapper>
 * ```
 */

'use client';

import React, {Profiler} from 'react';
import {profilerOnRender} from '@/lib/perf-monitor';

interface Props {
  id: string;
  children: React.ReactNode;
}

const ProfilerDevWrapper: React.FC<Props> = ({id, children}) => {
  if (import.meta.env.DEV) {
    return (
      <Profiler id={id} onRender={profilerOnRender}>
        {children}
      </Profiler>
    );
  }
  return <>{children}</>;
};

export default ProfilerDevWrapper;
