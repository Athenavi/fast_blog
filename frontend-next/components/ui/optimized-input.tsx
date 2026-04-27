'use client';

import React, {forwardRef, useCallback} from 'react';

interface OptimizedInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  debounceDelay?: number;
}

interface OptimizedTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  debounceDelay?: number;
}

// 高性能输入框组件
export const OptimizedInput = forwardRef<HTMLInputElement, OptimizedInputProps>(
  ({ onChange, debounceDelay = 300, ...props }, ref) => {
    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
      if (onChange) {
        onChange(e);
      }
    }, [onChange]);

    return (
      <input
        ref={ref}
        onChange={handleChange}
        {...props}
        className={`transition-all duration-200 ${props.className || ''}`}
      />
    );
  }
);

OptimizedInput.displayName = 'OptimizedInput';

// 高性能文本域组件
export const OptimizedTextarea = forwardRef<HTMLTextAreaElement, OptimizedTextareaProps>(
  ({ onChange, debounceDelay = 300, ...props }, ref) => {
    const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
      if (onChange) {
        onChange(e);
      }
    }, [onChange]);

    return (
      <textarea
        ref={ref}
        onChange={handleChange}
        {...props}
        className={`transition-all duration-200 resize-none ${props.className || ''}`}
      />
    );
  }
);

OptimizedTextarea.displayName = 'OptimizedTextarea';