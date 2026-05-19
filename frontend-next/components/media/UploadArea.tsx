'use client';

import React, {memo} from 'react';
import UploadProgress from '@/components/ui/UploadProgress';
import {Upload, Image as ImageIcon, Video, Music, FileText} from 'lucide-react';

interface UploadAreaProps {
  onUpload: (files: File[]) => void;
  uploading: boolean;
  uploadProgress: number;
  uploadStatus: string;
    collapsed?: boolean;
}

const UploadArea: React.FC<UploadAreaProps> = memo(({
  onUpload,
  uploading,
  uploadProgress,
                                                        uploadStatus,
                                                        collapsed = false
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
        {/* 如果折叠，只显示上传进度（如果有） */}
        {collapsed ? (
            uploading && (
                <div
                    className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-2xl p-6 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-900 dark:to-gray-800">
                    <UploadProgress percent={uploadProgress} status={uploadStatus} visible={true}/>
                </div>
            )
        ) : (
            <>
                <div
                    className="relative border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-2xl p-12 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-colors bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-900 dark:to-gray-800"
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                >
                    {/* 装饰性图标 */}
                    <div className="absolute inset-0 opacity-10 pointer-events-none">
                        <ImageIcon className="absolute top-8 left-8 w-12 h-12 text-blue-600"/>
                        <Video className="absolute top-12 right-12 w-10 h-10 text-purple-600"/>
                        <Music className="absolute bottom-12 left-16 w-8 h-8 text-pink-600"/>
                        <FileText className="absolute bottom-8 right-16 w-10 h-10 text-green-600"/>
                    </div>

                    <div className="relative z-10">
                        <div
                            className="w-20 h-20 bg-white dark:bg-gray-800 rounded-full shadow-lg mx-auto mb-6 flex items-center justify-center">
                            <Upload className="w-10 h-10 text-blue-600 dark:text-blue-400"/>
                        </div>

                        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                            拖放文件到此处
                        </h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            或点击下方按钮选择文件
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                            支持图片、视频、音频、文档等格式，单个文件最大 50MB
                        </p>

                        <label
                            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors cursor-pointer shadow-lg hover:shadow-xl">
                            <Upload className="w-5 h-5"/>
                            <span>选择文件</span>
                            <input
                                type="file"
                                multiple
                                accept="*/*"
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
                </div>

                {uploading && (
                    <div className="mt-4">
                        <UploadProgress percent={uploadProgress} status={uploadStatus} visible={true}/>
                    </div>
                )}
            </>
      )}
    </div>
  );
});

UploadArea.displayName = 'UploadArea';

export default UploadArea;