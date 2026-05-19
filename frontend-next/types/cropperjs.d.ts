/**
 * Cropper.js 类型声明补充
 * 用于解决 cropperjs 包中缺失的类型定义问题
 */

declare module 'cropperjs' {
    interface CropperOptions {
        // 视图模式 (0-3)
        viewMode?: number;
        // 拖拽模式
        dragMode?: 'crop' | 'move' | 'none';
        // 初始裁剪区域大小
        initialAspectRatio?: number;
        // 纵横比
        aspectRatio?: number;
        // 自动裁剪区域
        autoCropArea?: number;
        // 是否响应式
        responsive?: boolean;
        // 恢复
        restore?: boolean;
        // 显示网格线
        guides?: boolean;
        // 显示中心指示器
        center?: boolean;
        // 高亮显示裁剪框
        highlight?: boolean;
        // 裁剪框可移动
        cropBoxMovable?: boolean;
        // 裁剪框可调整大小
        cropBoxResizable?: boolean;
        // 双击切换拖拽模式
        toggleDragModeOnDblclick?: boolean;
        // 最小裁剪框宽度
        minCropBoxWidth?: number;
        // 最小裁剪框高度
        minCropBoxHeight?: number;
        // 背景色
        background?: boolean;
        // 检查图像方向
        checkOrientation?: boolean;
        // 模态模式
        modal?: boolean;
        // 缩放选项
        zoomable?: boolean;
        zoomOnTouch?: boolean;
        zoomOnWheel?: boolean;
        wheelZoomRatio?: number;
        // 移动选项
        movable?: boolean;
        rotatable?: boolean;
        scalable?: boolean;
        // 数据选项
        data?: CropperData;

        // 事件回调
        ready?(event: CustomEvent): void;

        cropstart?(event: CustomEvent): void;

        cropmove?(event: CustomEvent): void;

        cropend?(event: CustomEvent): void;

        crop?(event: CustomEvent): void;

        zoom?(event: CustomEvent): void;
    }

    interface CropperData {
        x: number;
        y: number;
        width: number;
        height: number;
        rotate: number;
        scaleX: number;
        scaleY: number;
    }

    interface CropperCanvasData {
        left: number;
        top: number;
        width: number;
        height: number;
        naturalWidth: number;
        naturalHeight: number;
    }

    interface CropperCropBoxData {
        left: number;
        top: number;
        width: number;
        height: number;
    }

    class Cropper {
        constructor(element: HTMLImageElement, options?: CropperOptions);

        // 静态属性
        static noConflict(): Cropper;

        static setDefaults(options: CropperOptions): void;

        // 方法
        clear(): Cropper;

        replace(url: string, onlyColorChanged?: boolean): Cropper;

        enable(): Cropper;

        disable(): Cropper;

        destroy(): Cropper;

        move(offsetX: number, offsetY?: number): Cropper;

        moveTo(x: number, y?: number): Cropper;

        zoom(ratio: number): Cropper;

        zoomTo(ratio: number, pivot?: { x: number; y: number }): Cropper;

        rotate(degree: number): Cropper;

        rotateTo(degree: number): Cropper;

        scale(scaleX: number, scaleY?: number): Cropper;

        scaleX(scaleX: number): Cropper;

        scaleY(scaleY: number): Cropper;

        getData(rounded?: boolean): CropperData;

        setData(data: CropperData): Cropper;

        getContainerData(): { width: number; height: number };

        getImageData(): {
            left: number;
            top: number;
            width: number;
            height: number;
            naturalWidth: number;
            naturalHeight: number;
            aspectRatio: number;
        };

        getCanvasData(): CropperCanvasData;

        setCanvasData(data: Partial<CropperCanvasData>): Cropper;

        getCropBoxData(): CropperCropBoxData;

        setCropBoxData(data: Partial<CropperCropBoxData>): Cropper;

        getCroppedCanvas(options?: {
            width?: number;
            height?: number;
            minWidth?: number;
            minHeight?: number;
            maxWidth?: number;
            maxHeight?: number;
            fillColor?: string;
            imageSmoothingEnabled?: boolean;
            imageSmoothingQuality?: 'low' | 'medium' | 'high';
        }): HTMLCanvasElement;

        setAspectRatio(aspectRatio: number): Cropper;

        setDragMode(dragMode: 'crop' | 'move' | 'none'): Cropper;
    }

    export default Cropper;
}
