/**
 * Slider UI Component
 * 基于原生 input range 的滑块组件
 */

'use client';

import * as React from 'react';
import {cn} from '@/lib/utils';

export interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
    min?: number;
    max?: number;
    step?: number;
    value?: number | readonly number[];
    onValueChange?: (value: number[]) => void;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
    ({className, min = 0, max = 100, step = 1, value, onValueChange, ...props}, ref) => {
        const currentValue = Array.isArray(value) ? value[0] : (value ?? min);

        const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const newValue = parseFloat(e.target.value);
            if (onValueChange) {
                onValueChange([newValue]);
            }
        };

        return (
            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={currentValue}
                onChange={handleChange}
                ref={ref}
                className={cn(
                    "w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700",
                    "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                    className
                )}
                {...props}
            />
        );
    }
);

Slider.displayName = "Slider";

export {Slider};
