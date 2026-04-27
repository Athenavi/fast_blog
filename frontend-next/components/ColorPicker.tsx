/**
 * ColorPicker Component
 * 颜色选择器组件
 */

'use client';

import * as React from 'react';
import {cn} from '@/lib/utils';

export interface ColorPickerProps {
    value: string;
    onChange: (value: string) => void;
    className?: string;
}

export const ColorPicker: React.FC<ColorPickerProps> = ({value, onChange, className}) => {
    return (
        <div className={cn("flex items-center gap-2", className)}>
            <input
                type="color"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer border border-gray-300"
            />
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="#000000"
            />
        </div>
    );
};
