import {useState} from 'react';
import {MediaService} from '@/lib/api';

interface UseMediaUploadReturn {
  uploading: boolean;
  uploadProgress: number;
  uploadStatus: string;
  uploadFiles: (files: File[]) => Promise<void>;
}

export const useMediaUpload = (onComplete?: () => void): UseMediaUploadReturn => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');

  const uploadFiles = async (files: File[]): Promise<void> => {
    if (files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadStatus(`开始上传 ${files.length} 个文件...`);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 上传单个文件并跟踪进度
        await MediaService.uploadMediaFileWithProgress(
          file,
          (percent, status) => {
            // 计算整体进度
            const overallPercent = ((i / files.length) * 100) + (percent / files.length);
            setUploadProgress(overallPercent);
            setUploadStatus(status);
          }
        );

        // 更新进度状态
        const overallProgress = ((i + 1) / files.length) * 100;
        setUploadStatus(`已上传: ${file.name} (${i + 1}/${files.length})`);
      }

      setUploadStatus('上传完成!');
      
      // 调用完成回调
      if (onComplete) {
        onComplete();
      }
    } catch (error) {
      console.error('上传失败:', error);
      setUploadStatus(`上传失败: ${error instanceof Error ? error.message : '未知错误'}`);
      throw error;
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        setUploadStatus('');
      }, 2000);
    }
  };

  return {
    uploading,
    uploadProgress,
    uploadStatus,
    uploadFiles
  };
};