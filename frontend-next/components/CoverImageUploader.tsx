'use client';

import React, {useCallback, useState} from 'react';
import {useMediaUpload} from '@/hooks/useMediaUpload';
import {MediaFile, MediaService} from '@/lib/api';
import {Button} from '@/components/ui/button';
import {Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger} from '@/components/ui/dialog';
import MediaGrid from '@/components/media/MediaGrid';
import SearchAndFilter from '@/components/media/SearchAndFilter';
import Pagination from '@/components/media/Pagination';
import UploadArea from '@/components/media/UploadArea';
import {Image, Link, X} from 'lucide-react';

interface CoverImageUploaderProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onValidationChange?: (isValid: boolean) => void;
}

const CoverImageUploader: React.FC<CoverImageUploaderProps> = ({
  value,
  onChange,
  placeholder = '点击上传或选择图片作为封面',
  onValidationChange
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [validationStatus, setValidationStatus] = useState<'valid' | 'invalid' | 'loading' | null>(null);
  const [validationMessage, setValidationMessage] = useState('');

  // 使用媒体上传hook
  const {uploading, uploadProgress, uploadStatus, uploadFiles} = useMediaUpload(() => {
    // 上传完成后刷新媒体库
    loadMediaFiles();
  });

  // 加载媒体文件
  const loadMediaFiles = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: { media_type?: string; page?: number; search?: string } = {};
      
      // 设置过滤参数
      params.media_type = 'image';
      params.page = currentPage;
      
      if (searchTerm) {
        params.search = searchTerm;
      }

      const result = await MediaService.getMediaFiles(params);
      
      if (result.success && result.data) {
        // 根据 MediaSelectorModal 的实现，使用 media_items 而不是 media
        setMediaFiles(result.data.media_items || []);
        setTotalPages(result.data.pagination?.pages || 1);
      } else {
        setMediaFiles([]);
        setTotalPages(1);
      }
    } catch (error) {
      console.error('加载媒体文件失败:', error);
      setMediaFiles([]);
      setTotalPages(1);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm]);

  // 处理文件上传
  const handleUpload = async (files: File[]) => {
    try {
      await uploadFiles(files);
      // 上传成功后自动验证第一张图片
      if (files.length > 0) {
        setTimeout(() => {
          loadMediaFiles();
        }, 1000);
      }
    } catch (error) {
      console.error('上传失败:', error);
      setValidationStatus('invalid');
      setValidationMessage('上传失败');
      onValidationChange?.(false);
    }
  };

  // 验证图片URL
  const validateImageUrl = async (url: string) => {
    if (!url) {
      setValidationStatus(null);
      setValidationMessage('');
      onValidationChange?.(true);
      return;
    }

    setValidationStatus('loading');
    setValidationMessage('正在验证图片...');

    try {
      const response = await fetch(url, { method: 'HEAD' });
      const contentType = response.headers.get('content-type');
      
      if (response.ok && contentType && contentType.startsWith('image/')) {
        setValidationStatus('valid');
        setValidationMessage('图片验证成功');
        onValidationChange?.(true);
      } else {
        setValidationStatus('invalid');
        setValidationMessage('URL不是有效的图片地址');
        onValidationChange?.(false);
      }
    } catch (error) {
      setValidationStatus('invalid');
      setValidationMessage('无法访问该图片URL');
      onValidationChange?.(false);
    }
  };

  // 移除封面图片
  const handleRemoveCover = () => {
    onChange('');
    setValidationStatus(null);
    setValidationMessage('');
    onValidationChange?.(true);
  };

  // 手动输入URL
  const handleUrlInput = (url: string) => {
    onChange(url);
    validateImageUrl(url);
  };

  // 处理媒体文件选择
  const handleMediaSelect = (media: MediaFile) => {
    const imageUrl = `/api/v1/media/${media.id}`;
    onChange(imageUrl);
    setIsOpen(false);
    setValidationStatus('valid');
    setValidationMessage('已选择媒体库中的图片');
    onValidationChange?.(true);
  };

  // 当对话框打开时加载媒体文件
  React.useEffect(() => {
    if (isOpen) {
      loadMediaFiles();
    }
  }, [isOpen, currentPage, searchTerm, loadMediaFiles]);

  // 当value改变时进行验证
  React.useEffect(() => {
    if (value) {
      validateImageUrl(value);
    } else {
      setValidationStatus(null);
      setValidationMessage('');
      onValidationChange?.(true);
    }
  }, [value]);

  return (
    <div className="space-y-4">
      {/* 封面预览区域 */}
      {(value || uploading) && (
        <div className="relative group">
          <div className="relative h-48 rounded-lg overflow-hidden border-2 border-dashed border-gray-300">
            {uploading ? (
              <div className="absolute inset-0 bg-gray-100 flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                  <p className="text-sm text-gray-600">{uploadStatus}</p>
                  <p className="text-xs text-gray-500">{Math.round(uploadProgress)}%</p>
                </div>
              </div>
            ) : value ? (
              <>
                <img
                  src={value}
                  alt="封面预览"
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.src = '/placeholder-image.jpg';
                    setValidationStatus('invalid');
                    setValidationMessage('图片加载失败');
                    onValidationChange?.(false);
                  }}
                  onLoad={() => {
                    setValidationStatus('valid');
                    setValidationMessage('图片加载成功');
                    onValidationChange?.(true);
                  }}
                />
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={handleRemoveCover}
                    className="mr-2"
                  >
                    <X className="w-4 h-4 mr-1" />
                    移除
                  </Button>
                </div>
              </>
            ) : null}
          </div>
          
          {/* 状态指示器 */}
          {validationStatus && (
            <div className={`absolute top-2 right-2 flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium shadow-lg ${
              validationStatus === 'valid' ? 'bg-green-500 text-white' :
              validationStatus === 'invalid' ? 'bg-red-500 text-white' :
              'bg-blue-500 text-white'
            }`}>
              <div className="flex items-center gap-1">
                {validationStatus === 'valid' && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {validationStatus === 'invalid' && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                {validationStatus === 'loading' && (
                  <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                )}
                <span>{validationMessage}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 上传选项 */}
      <div className="flex flex-col sm:flex-row gap-2">
        {/* 从媒体库选择 */}
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger asChild>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              disabled={uploading}
            >
              <Image className="w-4 h-4 mr-2" />
              {value ? '更换图片' : '从媒体库选择'}
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle>选择封面图片</DialogTitle>
            </DialogHeader>
            
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* 搜索和上传区域 */}
              <div className="mb-4">
                <SearchAndFilter
                  filterMediaType="image"
                  setFilterMediaType={() => {}} // 在封面选择器中固定为图片类型
                  searchQuery={searchTerm}
                  handleSearchChange={setSearchTerm}
                  totalItems={mediaFiles.length}
                  setCurrentPage={setCurrentPage}
                  onUploadRequest={handleUpload}
                />
                
                <UploadArea
                  onUpload={handleUpload}
                  uploading={uploading}
                  uploadProgress={uploadProgress}
                  uploadStatus={uploadStatus}
                />
              </div>

              {/* 媒体网格 */}
              <div className="flex-1 overflow-y-auto">
                <MediaGrid
                  mediaFiles={mediaFiles}
                  loading={isLoading}
                  onPreview={handleMediaSelect}
                  onDelete={() => {}}
                  totalItems={mediaFiles.length}
                />
              </div>

              {/* 分页 */}
              <div className="mt-4 pt-4 border-t">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalItems={mediaFiles.length}
                  perPage={20}
                  goToPage={setCurrentPage}
                  startIndex={(currentPage - 1) * 20 + 1}
                  endIndex={currentPage * 20}
                />
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* 手动输入URL */}
        <Dialog>
          <DialogTrigger asChild>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              disabled={uploading}
            >
              <Link className="w-4 h-4 mr-2" />
              输入图片链接
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>输入图片链接</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <input
                type="url"
                value={value}
                onChange={(e) => handleUrlInput(e.target.value)}
                placeholder="https://example.com/image.jpg"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex justify-end gap-2">
                <DialogTrigger asChild>
                  <Button variant="outline">取消</Button>
                </DialogTrigger>
                <DialogTrigger asChild>
                  <Button>确定</Button>
                </DialogTrigger>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* 提示信息 */}
      {!value && !uploading && (
        <p className="text-sm text-gray-500 text-center">
          {placeholder}
        </p>
      )}
    </div>
  );
};

export default CoverImageUploader;