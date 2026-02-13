import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import dynamic from 'next/dynamic';
import type {Options} from 'easymde';
import MediaSelectorModal from '@/components/ui/MediaSelectorModal';
import type {MediaFile} from '@/lib/api';

// 动态导入编辑器组件
const SimpleMdeEditor = dynamic(
  () => import('react-simplemde-editor').then(mod => mod.SimpleMdeReact),
  { 
    ssr: false,
    loading: () => (
      <div className="h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
          <p className="text-gray-600 dark:text-gray-400">加载编辑器中...</p>
        </div>
      </div>
    )
  }
);

interface OptimizedMarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  debounceDelay?: number; // 防抖延迟时间，默认300ms
  minHeight?: string;
  maxHeight?: string;
  placeholder?: string;
  disabled?: boolean;
  onInsertMedia?: (media: MediaFile | MediaFile[]) => void; // 媒体文件插入回调
}

const OptimizedMarkdownEditor: React.FC<OptimizedMarkdownEditorProps> = ({ 
  value, 
  onChange, 
  debounceDelay = 300,
  minHeight = '400px',
  maxHeight = '800px',
  placeholder = '开始编写您的文章...',
  disabled = false,
  onInsertMedia
}) => {
  const [isClient, setIsClient] = useState(false);
  const [localValue, setLocalValue] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [showMediaSelector, setShowMediaSelector] = useState(false);
  const [mediaSelectorType, setMediaSelectorType] = useState<'image' | 'video' | 'audio' | 'all'>('image');
  const editorRef = useRef<unknown>(null); // 使用unknown替代any
  
  // 设置编辑器引用
  const handleEditorMount = useCallback((editor: unknown) => {
    editorRef.current = editor;
  }, []);

  // 防抖函数
  const debouncedOnChange = useCallback((newValue: string) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    debounceTimerRef.current = setTimeout(() => {
      onChange(newValue);
    }, debounceDelay);
  }, [onChange, debounceDelay]);

  // 监听外部value变化，同步本地状态
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setIsClient(true);
    
    // 动态加载easymde的CSS
    if (typeof document !== 'undefined') {
      const existingLink = document.getElementById('easymde-css');
      if (!existingLink) {
        const link = document.createElement('link');
        link.id = 'easymde-css';
        link.rel = 'stylesheet';
        link.href = 'https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css';
        document.head.appendChild(link);
      }
    }
  }, []);

  // 确保编辑器样式正确加载
  useEffect(() => {
    if (isClient && containerRef.current) {
      const timer = setTimeout(() => {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('resize'));
          containerRef.current!.offsetHeight;
        }
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [isClient]);

  // 处理编辑器值变化
  const handleEditorChange = useCallback((newValue: string) => {
    setLocalValue(newValue);
    debouncedOnChange(newValue);
  }, [debouncedOnChange]);

  // 处理媒体文件选择（支持单个或多个文件）
  const handleMediaSelect = useCallback((media: MediaFile | MediaFile[]) => {
    if (onInsertMedia) {
      onInsertMedia(media);
    } else {
      // 处理单个文件
      const mediaFiles = Array.isArray(media) ? media : [media];
      
      // 为每个文件生成对应的Markdown格式
      const mediaMarkdowns = mediaFiles.map(singleMedia => {
        const mediaUrl = `/api/v1/media/${singleMedia.id}`;
        
        if (singleMedia.mime_type.startsWith('image/')) {
          // 图片格式：![alt](url)
          return `![${singleMedia.original_filename}](${mediaUrl})`;
        } else if (singleMedia.mime_type.startsWith('video/')) {
          // 视频格式：<video controls><source src="url" type="mime_type">您的浏览器不支持视频标签。</video>
          return `<video controls><source src="${mediaUrl}" type="${singleMedia.mime_type}">您的浏览器不支持视频标签。</video>`;
        } else if (singleMedia.mime_type.startsWith('audio/')) {
          // 音频格式：<audio controls><source src="url" type="mime_type">您的浏览器不支持音频标签。</audio>
          return `<audio controls><source src="${mediaUrl}" type="${singleMedia.mime_type}">您的浏览器不支持音频标签。</audio>`;
        } else {
          // 其他文件类型：[文件名](url)
          return `[${singleMedia.original_filename}](${mediaUrl})`;
        }
      });
      
      // 将所有Markdown内容连接，用换行分隔
      const combinedMarkdown = mediaMarkdowns.join('\n\n');
      
      // 插入到编辑器当前光标位置
      if (editorRef.current) {
        // 类型断言为any来访问codemirror属性
        const editorInstance = editorRef.current as any;
        if (editorInstance.codemirror) {
          const cm = editorInstance.codemirror;
          const cursor = cm.getCursor();
          cm.replaceRange(combinedMarkdown, cursor);
          cm.setCursor(cursor.line, cursor.ch + combinedMarkdown.length);
          cm.focus();
          
          // 触发onChange事件
          const newValue = cm.getValue();
          setLocalValue(newValue);
          debouncedOnChange(newValue);
        }
      }
    }
  }, [onInsertMedia, debouncedOnChange]);

  // 自定义媒体按钮
  const customImageToolbarButton = useMemo(() => ({
    name: 'custom-image',
    action: () => {
      setMediaSelectorType('image');
      setShowMediaSelector(true);
    },
    className: 'fa fa-picture-o',
    title: '从媒体库选择图片',
  }), []);

  const customVideoToolbarButton = useMemo(() => ({
    name: 'custom-video',
    action: () => {
      setMediaSelectorType('video');
      setShowMediaSelector(true);
    },
    className: 'fa fa-file-video-o',
    title: '从媒体库选择视频',
  }), []);

  const customAudioToolbarButton = useMemo(() => ({
    name: 'custom-audio',
    action: () => {
      setMediaSelectorType('audio');
      setShowMediaSelector(true);
    },
    className: 'fa fa-file-audio-o',
    title: '从媒体库选择音频',
  }), []);

  // 编辑器配置选项
  const easyMDEOptions = useMemo<Options>(() => ({
    autofocus: false,
    placeholder,
    spellChecker: false,
    status: ['autosave', 'lines', 'words'] as const,
    minHeight,
    maxHeight,
    sideBySideFullscreen: false,
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'code', 'quote', 'unordered-list', 'ordered-list', '|',
      'link', 
      customImageToolbarButton, 
      customVideoToolbarButton, 
      customAudioToolbarButton, 
      '|',
      'preview', 'side-by-side', 'fullscreen', '|',
      'guide'
    ],
    autoRefresh: { delay: 300 },
    inputStyle: 'textarea',
    lineWrapping: true,
    theme: 'bootstrap',
    renderingConfig: {
      codeSyntaxHighlighting: true,
    },
    shortcuts: {
      togglePreview: null, // 禁用快捷键以减少冲突
      toggleSideBySide: null,
      toggleFullScreen: null,
    },
  }), [placeholder, minHeight, maxHeight, customImageToolbarButton, customVideoToolbarButton, customAudioToolbarButton]);

  if (!isClient) {
    return (
      <div className="h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg">
        <p className="text-gray-600 dark:text-gray-400">加载中...</p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="easymde-container w-full"
    >
      <SimpleMdeEditor
        value={localValue}
        onChange={handleEditorChange}
        options={easyMDEOptions}
        getMdeInstance={handleEditorMount}
      />
      
      {/* 媒体选择器模态框 */}
      <MediaSelectorModal
        isOpen={showMediaSelector}
        onClose={() => setShowMediaSelector(false)}
        onSelect={handleMediaSelect}
        allowedTypes={[mediaSelectorType]} // 根据按钮类型筛选
      />
    </div>
  );
};

export default OptimizedMarkdownEditor;