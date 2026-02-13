'use client';

import React, {useEffect, useState} from 'react';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';

interface HydratableSelectProps {
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
  defaultValue?: string;
  className?: string;
}

export function HydratableSelect({ 
  children, 
  value, 
  onValueChange, 
  defaultValue,
  className 
}: HydratableSelectProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    // 在服务端渲染期间或客户端尚未挂载时，返回一个基本的原生select
    return (
      <select 
        value={value || defaultValue} 
        onChange={onValueChange ? (e) => onValueChange(e.target.value) : undefined}
        className={className}
        disabled
      >
        {React.Children.map(children, (child: React.ReactNode) => {
          if (React.isValidElement<{value: string, children: React.ReactNode}>(child) && child.type === SelectItem) {
            return <option value={(child as React.ReactElement<{value: string}>).props.value}>{(child as React.ReactElement<{children: React.ReactNode}>).props.children}</option>;
          }
          return null;
        })}
      </select>
    );
  }

  // 客户端挂载后，返回正常的Radix UI Select组件
  return (
    <Select value={value} onValueChange={onValueChange} defaultValue={defaultValue}>
      <SelectTrigger className={className}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {children}
      </SelectContent>
    </Select>
  );
}