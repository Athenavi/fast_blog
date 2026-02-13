'use client';

import React, {memo} from 'react';
import UploadProgress from '@/components/ui/UploadProgress';

interface UploadAreaProps {
  onUpload: (files: File[]) => void;
  uploading: boolean;
  uploadProgress: number;
  uploadStatus: string;
}

const UploadArea: React.FC<UploadAreaProps> = memo(({
  onUpload,
  uploading,
  uploadProgress,
  uploadStatus
}) => {
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onUpload(files);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  return (
    <div className="mb-6">
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <i className="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-4"></i>
        <p className="text-gray-600 mb-2">拖放文件到此处或点击上传</p>
        <p className="text-sm text-gray-500 mb-4">支持图片、视频、音频、文档等格式</p>

        <label className="inline-block px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors cursor-pointer">
          选择文件
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = e.target.files;
              if (files && files.length > 0) {
                onUpload(Array.from(files));
              }
            }}
          />
        </label>
      </div>

      {uploading && (
        <div className="mt-4">
          <UploadProgress percent={uploadProgress} status={uploadStatus} visible={true} />
        </div>
      )}
    </div>
  );
});

UploadArea.displayName = 'UploadArea';

export default UploadArea;