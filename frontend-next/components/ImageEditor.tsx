'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import Cropper from 'cropperjs';

interface ImageEditorProps {
  imageUrl: string;
  onSave?: (editedImage: Blob) => void;
  onClose?: () => void;
}

const ASPECT_RATIOS = [
  { label: '自由', value: NaN },
  { label: '1:1', value: 1 },
  { label: '16:9', value: 16 / 9 },
  { label: '4:3', value: 4 / 3 },
  { label: '3:2', value: 3 / 2 },
] as const;

const ImageEditor: React.FC<ImageEditorProps> = ({ imageUrl, onSave, onClose }) => {
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cropperRef = useRef<Cropper | null>(null);

  const [editMode, setEditMode] = useState<'crop' | 'adjust'>('crop');
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [scale, setScale] = useState(100);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [cropperReady, setCropperReady] = useState(false);

  // 初始化 / 销毁 Cropper
  useEffect(() => {
    const img = imageRef.current;
    if (!img) return;

    const initCropper = () => {
      if (cropperRef.current) {
        cropperRef.current.destroy();
      }
      try {
        cropperRef.current = new Cropper(img, {
          viewMode: 2,               // 裁剪框限制在画布内，画布自适应容器
          dragMode: 'move',
          autoCropArea: 0.9,
          responsive: true,          // 容器大小变化时自动调整
          restore: false,
          guides: true,
          center: true,
          highlight: false,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
          minCropBoxWidth: 50,
          minCropBoxHeight: 50,
          ready() {
            setCropperReady(true);
            setImageError(false);
          },
        });
      } catch {
        setImageError(true);
      }
    };

    const handleLoad = () => {
      setImageError(false);
      initCropper();
    };

    const handleError = () => setImageError(true);

    if (img.complete) {
      handleLoad();
    } else {
      img.addEventListener('load', handleLoad);
      img.addEventListener('error', handleError);
    }

    // 强制刷新（避免缓存导致的加载问题）
    img.src = `${imageUrl}${imageUrl.includes('?') ? '&' : '?'}_t=${Date.now()}`;

    return () => {
      img.removeEventListener('load', handleLoad);
      img.removeEventListener('error', handleError);
      cropperRef.current?.destroy();
      cropperRef.current = null;
    };
  }, [imageUrl]);

  // 应用调整效果到 Canvas
  const applyAdjustments = useCallback(() => {
    const img = imageRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    setIsProcessing(true);

    // 使用 requestAnimationFrame 避免阻塞
    requestAnimationFrame(() => {
      try {
        const { naturalWidth: w, naturalHeight: h } = img;
        const ratio = scale / 100;
        let width = w * ratio;
        let height = h * ratio;

        // 旋转后交换宽高
        const isRotated = rotation % 180 !== 0;
        canvas.width = isRotated ? height : width;
        canvas.height = isRotated ? width : height;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.scale(flipH ? -1 : 1, flipV ? -1 : 1);
        ctx.rotate((rotation * Math.PI) / 180);
        ctx.filter = `brightness(${brightness}%) contrast(${contrast}%)`;
        ctx.drawImage(img, -width / 2, -height / 2, width, height);
        ctx.restore();
      } catch (error) {
        console.error('调整图片失败:', error);
      } finally {
        setIsProcessing(false);
      }
    });
  }, [brightness, contrast, rotation, scale, flipH, flipV]);

  // 调整参数变化时重绘
  useEffect(() => {
    if (editMode === 'adjust') {
      applyAdjustments();
    }
  }, [applyAdjustments, editMode]);

  // 保存处理后的图片
  const handleSave = useCallback(async () => {
    try {
      let blob: Blob | null = null;
      if (editMode === 'crop' && cropperRef.current) {
        const croppedCanvas = cropperRef.current.getCroppedCanvas({ fillColor: '#fff' });
        blob = await new Promise<Blob | null>((resolve) =>
          croppedCanvas.toBlob(resolve, 'image/jpeg', 0.9)
        );
      } else if (canvasRef.current) {
        blob = await new Promise<Blob | null>((resolve) =>
          canvasRef.current!.toBlob(resolve, 'image/jpeg', 0.9)
        );
      }
      if (blob) onSave?.(blob);
    } catch (error) {
      console.error('保存失败:', error);
    }
  }, [editMode, onSave]);

  // 重置所有调整参数 + Cropper 状态
  const handleReset = useCallback(() => {
    if (editMode === 'crop' && cropperRef.current && imageRef.current) {
      // 销毁并重建，设置为自由比例
      cropperRef.current.destroy();
      setCropperReady(false);
      
      cropperRef.current = new Cropper(imageRef.current, {
        viewMode: 1,
        dragMode: 'move',
        autoCropArea: 0.9,
        aspectRatio: NaN,
        restore: false,
        guides: true,
        center: true,
        highlight: false,
        cropBoxMovable: true,
        cropBoxResizable: true,
        toggleDragModeOnDblclick: false,
        minCropBoxWidth: 50,
        minCropBoxHeight: 50,
        ready() {
          setCropperReady(true);
        },
      });
    }
    setBrightness(100);
    setContrast(100);
    setRotation(0);
    setScale(100);
    setFlipH(false);
    setFlipV(false);
  }, [editMode]);

  // 纵横比切换（销毁并重建 Cropper 实例）
  const handleAspectRatioChange = (ratio: number) => {
    if (!cropperRef.current || !imageRef.current) return;
    
    // 保存当前裁剪数据
    const data = cropperRef.current.getData();
    
    // 销毁旧实例
    cropperRef.current.destroy();
    setCropperReady(false);
    
    // 重新创建，设置新的纵横比
    cropperRef.current = new Cropper(imageRef.current, {
      viewMode: 1,
      dragMode: 'move',
      autoCropArea: 0.9,
      aspectRatio: ratio,
      restore: false,
      guides: true,
      center: true,
      highlight: false,
      cropBoxMovable: true,
      cropBoxResizable: true,
      toggleDragModeOnDblclick: false,
      minCropBoxWidth: 50,
      minCropBoxHeight: 50,
      ready() {
        setCropperReady(true);
        // 恢复之前的裁剪区域
        if (data) {
          try {
            cropperRef.current?.setData(data);
          } catch (e) {
            console.log('无法恢复裁剪数据');
          }
        }
      },
    });
  };

  // 旋转按钮快捷操作
  const rotateLeft = () => setRotation((r) => (r - 90 + 360) % 360);
  const rotateRight = () => setRotation((r) => (r + 90) % 360);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl">
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-semibold">图片编辑器</h3>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReset}>重置</Button>
          <Button onClick={handleSave} disabled={isProcessing}>保存</Button>
          {onClose && <Button variant="ghost" onClick={onClose}>关闭</Button>}
        </div>
      </div>

      <div className="flex flex-col md:flex-row">
        {/* 左侧控制面板 */}
        <div className="w-full md:w-80 border-r p-4">
          <Tabs value={editMode} onValueChange={(v) => setEditMode(v as 'crop' | 'adjust')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="crop">裁剪</TabsTrigger>
              <TabsTrigger value="adjust">调整</TabsTrigger>
            </TabsList>

            <TabsContent value="crop" className="space-y-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <p>拖动选框调整裁剪区域</p>
                <p className="mt-2">• 角点：调整大小</p>
                <p>• 内部：移动选区</p>
              </div>
              <div className="space-y-2">
                <Label>纵横比</Label>
                <div className="grid grid-cols-3 gap-2">
                  {ASPECT_RATIOS.map(({ label, value }) => (
                    <Button
                      key={label}
                      size="sm"
                      variant="outline"
                      disabled={!cropperReady}
                      onClick={() => handleAspectRatioChange(value)}
                    >
                      {label}
                    </Button>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="adjust" className="space-y-4">
              <div className="space-y-2">
                <Label>亮度: {brightness}%</Label>
                <Slider value={[brightness]} onValueChange={([v]) => setBrightness(v)} min={0} max={200} step={1} />
              </div>
              <div className="space-y-2">
                <Label>对比度: {contrast}%</Label>
                <Slider value={[contrast]} onValueChange={([v]) => setContrast(v)} min={0} max={200} step={1} />
              </div>
              <div className="space-y-2">
                <Label>旋转: {rotation}°</Label>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={rotateLeft}>左旋 -90°</Button>
                  <Button size="sm" variant="outline" onClick={rotateRight}>右旋 +90°</Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>翻转</Label>
                <div className="flex gap-2">
                  <Button size="sm" variant={flipH ? 'default' : 'outline'} onClick={() => setFlipH(!flipH)}>水平</Button>
                  <Button size="sm" variant={flipV ? 'default' : 'outline'} onClick={() => setFlipV(!flipV)}>垂直</Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>缩放: {scale}%</Label>
                <Slider value={[scale]} onValueChange={([v]) => setScale(v)} min={10} max={200} step={5} />
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* 右侧预览区域 */}
        <div className="flex-1 p-4 bg-gray-50 dark:bg-gray-800 flex items-center justify-center min-h-[400px]">
          {imageError ? (
            <div className="text-center text-red-500">
              <p className="text-lg">图片加载失败</p>
              <p className="text-xs mt-2 truncate max-w-md">{imageUrl}</p>
              <Button className="mt-4" onClick={() => window.location.reload()}>重试</Button>
            </div>
          ) : (
            <div className="relative max-w-full max-h-[70vh] overflow-hidden flex items-center justify-center">
              {editMode === 'crop' ? (
                <img
                  ref={imageRef}
                  alt="编辑图片"
                  className="block max-w-full max-h-[70vh] object-contain"
                  style={{ display: 'none' }} // Cropper.js 会处理显示，这里隐藏原始 img
                />
              ) : (
                <canvas ref={canvasRef} className="max-w-full max-h-[70vh] object-contain shadow-lg" />
              )}
              {isProcessing && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <span className="text-white">处理中...</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ImageEditor;