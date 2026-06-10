import {useState} from 'react';
import {MediaService} from '@/lib/api';

export const useMediaUpload = (onComplete?: () => void) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true); setUploadProgress(0); setUploadStatus(`开始上传 ${files.length} 个文件...`);
    try {
      for (let i = 0; i < files.length; i++) {
        await MediaService.uploadMediaFileWithProgress(files[i], (p) => { setUploadProgress(((i/files.length)*100)+(p/files.length)); });
        setUploadStatus(`已上传: ${files[i].name} (${i+1}/${files.length})`);
      }
      setUploadStatus('上传完成!'); if (onComplete) onComplete();
    } catch (e: unknown) { setUploadStatus(`上传失败: ${(e as Error).message}`); }
    finally { setTimeout(()=>{setUploading(false);setUploadProgress(0);setUploadStatus('');},2000); }
  };
  return {uploading, uploadProgress, uploadStatus, uploadFiles};
};
