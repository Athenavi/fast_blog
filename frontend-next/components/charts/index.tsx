// Charts 组件导出文件
// 这是一个占位文件，实际的图表组件可以根据需要实现

import React from 'react';

interface ChartData {
    label: string;
    value: number;
}

interface ChartProps {
    data: ChartData[];
    title?: string;
}

export const LineChart: React.FC<ChartProps> = ({data, title}) => {
    return (
        <div className="w-full h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded">
            <div className="text-center">
                {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
                <p className="text-sm text-gray-500">LineChart 组件待实现</p>
                <p className="text-xs text-gray-400 mt-2">数据点数: {data.length}</p>
            </div>
        </div>
    );
};

export const BarChart: React.FC<ChartProps> = ({data, title}) => {
    return (
        <div className="w-full h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded">
            <div className="text-center">
                {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
                <p className="text-sm text-gray-500">BarChart 组件待实现</p>
                <p className="text-xs text-gray-400 mt-2">数据点数: {data.length}</p>
            </div>
        </div>
    );
};

export const PieChart: React.FC<ChartProps> = ({data, title}) => {
    return (
        <div className="w-full h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded">
            <div className="text-center">
                {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
                <p className="text-sm text-gray-500">PieChart 组件待实现</p>
                <p className="text-xs text-gray-400 mt-2">数据点数: {data.length}</p>
            </div>
        </div>
    );
};
