'use client';
import React from 'react';

export class ErrorBoundary extends React.Component<
  {children: React.ReactNode; fallback?: React.ReactNode},
  {hasError: boolean; error: Error | null}
> {
  constructor(props: any) {
    super(props);
    this.state = {hasError: false, error: null};
  }
  static getDerivedStateFromError(error: Error) {
    return {hasError: true, error};
  }
  componentDidCatch(error: Error, info: any) {
    console.error('[PageBuilder Error]', error.message, error.stack);
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 m-4 border border-red-300 bg-red-50 dark:bg-red-900/20 rounded-xl text-sm text-red-700 dark:text-red-400">
          <p className="font-medium mb-1">渲染错误</p>
          <p className="font-mono text-xs break-all">{this.state.error?.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
