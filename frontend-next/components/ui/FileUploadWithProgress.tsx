import React, {useCallback, useState} from 'react';
import {MediaService} from '@/lib/api';
import UploadProgress from './UploadProgress';

interface FileUploadWithProgressProps {
  onUploadComplete?: (result: any) => void;
  onUploadError?: (error: Error) => void;
  accept?: string;
  multiple?: boolean;
}

const FileUploadWithProgress: React.FC<FileUploadWithProgressProps> = ({
  onUploadComplete,
  onUploadError,
  accept = '*',
  multiple = false
}) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = useCallback(async (file: File) => {
    setUploading(true);
    setProgress(0);
    setStatus(`开始上传: ${file.name}`);

    try {
      const result = await MediaService.uploadMediaFileWithProgress(file, (percent, statusText) => {
        setProgress(percent);
        setStatus(statusText);
      });

      if (result.success) {
        setStatus('上传完成!');
        if (onUploadComplete) {
          onUploadComplete(result);
        }
      } else {
        // 更完善的错误处理
        let errorMsg = '未知错误';
        let fullErrorMsg = '';
        
        // 处理不同的错误格式
        if (typeof result === 'object' && result !== null) {
          if (result.error) {
            errorMsg = typeof result.error === 'string' ? result.error : JSON.stringify(result.error);
          } else if (result.message) {
            errorMsg = typeof result.message === 'string' ? result.message : JSON.stringify(result.message);
          } else if (Object.keys(result).length === 0) {
            errorMsg = '服务器返回空响应';
          } else {
            errorMsg = `上传失败: ${JSON.stringify(result)}`;
          }
          
          if (result.message && typeof result.message === 'string' && result.message !== errorMsg) {
            fullErrorMsg = `${errorMsg}: ${result.message}`;
          } else {
            fullErrorMsg = errorMsg;
          }
        } else {
          errorMsg = typeof result === 'string' ? result : '上传失败';
          fullErrorMsg = errorMsg;
        }
        
        console.error('文件上传失败:', result);
        setStatus(`上传失败: ${fullErrorMsg}`);
        if (onUploadError) {
          onUploadError(new Error(fullErrorMsg));
        }
      }
    } catch (error) {
      setStatus(`上传失败: ${error instanceof Error ? error.message : '未知错误'}`);
      if (onUploadError) {
        onUploadError(error instanceof Error ? error : new Error(String(error)));
      }
    } finally {
      setTimeout(() => {
        setUploading(false);
        setProgress(0);
        setStatus('');
      }, 2000);
    }
  }, [onUploadComplete, onUploadError]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]); // 只处理第一个文件，如果是多文件则需要循环
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
  };

  return (
    <div 
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
        dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
    >
      <i className="fas fa-cloud-upload-alt text-5xl text-gray-400 mb-4"></i>
      <p className="text-lg text-gray-600 mb-2">拖拽文件到此处上传</p>
      <p className="text-sm text-gray-400 mb-4">或点击下方按钮选择文件</p>
      
      <label className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center mx-auto cursor-pointer">
        <i className="fas fa-folder-open mr-2"></i>
        选择文件
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileChange}
          className="hidden"
        />
      </label>

      {uploading && (
        <div className="mt-4">
          <UploadProgress percent={progress} status={status} visible={true} />
        </div>
      )}
    </div>
  );
};

export default FileUploadWithProgress;