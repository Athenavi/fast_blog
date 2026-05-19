'use client';

import React from 'react';

interface SpacerBlockProps {
    attributes: {
        height?: number;
    };
    isSelected?: boolean;
}

/**
 * 间距 Block 组件
 */
const SpacerBlock: React.FC<SpacerBlockProps> = ({ attributes, isSelected }) => {
    const height = attributes.height || 50;

    return (
        <div 
            className={`${isSelected ? 'ring-2 ring-blue-500 rounded' : ''}`}
            style={{ height: `${height}px` }}
        >
            <div className="h-full flex items-center justify-center">
                <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    间距: {height}px
                </span>
            </div>
        </div>
    );
};

export default SpacerBlock;
