import React from 'react';

interface UploadProgressProps {
  percent: number;
  status: string;
  visible?: boolean;
}

const UploadProgress: React.FC<UploadProgressProps> = ({ 
  percent, 
  status, 
  visible = true 
}) => {
  if (!visible) return null;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">上传进度</span>
        <span className="text-sm font-medium text-gray-700">{Math.round(percent)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out"
          style={{ width: `${percent}%` }}
        ></div>
      </div>
      <p className="text-sm text-gray-500 mt-1">{status}</p>
    </div>
  );
};

export default UploadProgress;