'use client';

import React from 'react';

interface SeparatorBlockProps {
    attributes: {
        style?: 'solid' | 'dashed' | 'dotted';
    };
    isSelected?: boolean;
}

/**
 * 分隔线 Block 组件
 */
const SeparatorBlock: React.FC<SeparatorBlockProps> = ({ attributes, isSelected }) => {
    const borderStyle = attributes.style || 'solid';
    
    const styleMap: Record<string, string> = {
        solid: 'border-solid',
        dashed: 'border-dashed',
        dotted: 'border-dotted',
    };

    return (
        <div className={`py-4 ${isSelected ? 'ring-2 ring-blue-500 rounded' : ''}`}>
            <hr className={`border-t-2 ${styleMap[borderStyle]} border-gray-300 dark:border-gray-600`} />
        </div>
    );
};

export default SeparatorBlock;
