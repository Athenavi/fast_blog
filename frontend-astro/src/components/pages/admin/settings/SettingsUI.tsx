import React, {useEffect, useState} from 'react';
import {
  AlertTriangle, CheckCircle2, ChevronDown, Clock, Download, ExternalLink,
  FileCode, FileText, Film, Image, Layers, Layout, Loader, Monitor, Save,
  Search, Trash2, Upload, X, XCircle
} from 'lucide-react';
import {getConfig} from '@/lib/config';
import {getFullMediaUrl} from '@/lib/utils';
import {type FieldDef} from './SettingsTypes';

// ─── Section Title ────────────────────────────────────
export const SectionTitle: React.FC<{
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  action?: React.ReactNode
}> = ({
                                                                                                             icon: Icon,
                                                                                                             title,
                                                                                                             subtitle,
                                                                                                             action
                                                                                                           }) => (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        <div
            className="w-9 h-9 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
          <Icon className="w-4.5 h-4.5 text-gray-600 dark:text-gray-300"/>
        </div>
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
);

// ─── Skeleton loading ─────────────────────────────────
export const SettingsSkeleton = () => (
    <div className="space-y-5 animate-pulse">
      {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-lg w-24"/>
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded-xl w-full"/>
          </div>
      ))}
    </div>
);

export const MenuSkeleton = () => (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map(i => (
          <div key={i} className="p-5 bg-gray-100 dark:bg-gray-800 rounded-xl">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-lg w-32"/>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full w-12"/>
            </div>
            <div className="ml-4 space-y-2">
              {[1, 2].map(j => (
                  <div key={j} className="h-8 bg-gray-200 dark:bg-gray-700 rounded-lg w-full"/>
              ))}
            </div>
          </div>
      ))}
    </div>
);

export const PageSkeleton = () => (
    <div className="space-y-0 animate-pulse">
      {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center gap-4 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-lg w-32"/>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-lg w-24 hidden sm:block"/>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-lg w-16 hidden lg:block ml-auto"/>
          </div>
      ))}
    </div>
);

// ─── Image Upload Field ───────────────────────────────
export const MediaField: React.FC<{ value: string; onChange: (v: string) => void; placeholder?: string }> = ({
                                                                                                        value,
                                                                                                        onChange,
                                                                                                        placeholder
                                                                                                      }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const isVideo = (url: string) => /\.(mp4|webm|ogg|mov|avi|mkv)(\?|$)/i.test(url);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const isImage = file.type.startsWith('image/');
    const isVideoFile = file.type.startsWith('video/');
    if (!isImage && !isVideoFile) {
      alert('请选择图片或视频文件');
      return;
    }
    const maxSize = isVideoFile ? 50 * 1024 * 1024 : 8 * 1024 * 1024;
    if (file.size > maxSize) {
      alert(isVideoFile ? '视频文件大小不能超过 50MB' : '图片文件大小不能超过 8MB');
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('file', file);

      // 从 cookie 读取 JWT token（与 base-client 和 CoverImageUploader 一致）
      const accessToken = (() => {
        for (const c of document.cookie.split(';')) {
          const [n, v] = c.trim().split('=');
          if (n === 'access_token' && v) return decodeURIComponent(v);
        }
        return null;
      })();

      const xhr = new XMLHttpRequest();
      const result = await new Promise<{
        success?: boolean;
        data?: { url?: string; files?: { url: string }[] };
        message?: string;
        error?: string;
      }>((resolve, reject) => {
        const {API_BASE_URL} = getConfig();
        xhr.open('POST', `${API_BASE_URL}/api/v2/media/settings/upload`);
        xhr.withCredentials = true;
        if (accessToken) {
          xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);
        }
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status === 302 || xhr.status === 401 || xhr.status === 403) {
            reject(new Error('未登录或登录已过期，请重新登录'));
            return;
          }
          try {
            const parsed = JSON.parse(xhr.responseText);
            // 检查服务端业务错误（非 HTTP 层面）
            if (parsed && parsed.success === false) {
              reject(new Error(parsed.message || parsed.error || '上传失败'));
              return;
            }
            resolve(parsed);
          } catch {
            const snippet = xhr.responseText?.slice(0, 120) || '(empty)';
            reject(new Error(`服务器返回非 JSON 响应 (HTTP ${xhr.status}): ${snippet}`));
          }
        };
        xhr.onerror = () => reject(new Error('网络错误，请检查网络连接'));
        xhr.send(formData);
      });
      const url = result?.data?.url || result?.data?.files?.[0]?.url;
      if (url) {
        onChange(url);
      } else {
        alert('上传成功但未获取到文件 URL');
      }
    } catch (err: any) {
      alert(err?.message || '上传失败');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const resolvedUrl = value ? getFullMediaUrl(value) : '';
  const isVideoMedia = value ? isVideo(value) : false;

  return (
    <div className="space-y-3">
      {/* Preview */}
      {value && (
        <div
          className="relative group rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 aspect-video max-h-48">
          {isVideoMedia ? (
            <video src={resolvedUrl} className="w-full h-full object-cover" controls muted onError={(e) => {
              (e.target as HTMLVideoElement).style.display = 'none';
            }}/>
          ) : (
            <img src={resolvedUrl} alt="预览" className="w-full h-full object-cover" onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}/>
          )}
          <div
            className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
            <button onClick={() => onChange('')}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                    title="移除媒体">
              <Trash2 className="w-4 h-4"/>
            </button>
          </div>
        </div>
      )}
      {/* Upload button + URL input */}
      <div className="flex gap-2">
        <input ref={fileInputRef} type="file" accept="image/*,video/*" onChange={handleFileSelect} className="hidden"/>
        <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading}
                className="flex-shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800/80 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all disabled:opacity-50">
          {uploading ? <Loader className="w-4 h-4 animate-spin"/> : <Upload className="w-4 h-4"/>}
          {uploading ? `${uploadProgress}%` : '上传媒体'}
        </button>
        <div className="relative flex-1">
          <Film className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
          <input type="text" value={value} onChange={e => onChange(e.target.value)}
                 className="w-full px-4 py-2.5 pl-10 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800/80 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all"
                 placeholder={placeholder || '输入媒体 URL'}/>
        </div>
      </div>
    </div>
  );
};

// ─── Enhanced Field Input ─────────────────────────────
export const FieldInput: React.FC<{field: FieldDef; value: string; onChange: (v: string) => void}> = ({field, value, onChange}) => {
  const baseClass = "w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800/80 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 dark:focus:border-blue-500 transition-all duration-200";

  if (field.type === 'select' && field.options) {
    return (
        <div className="relative">
          <select value={value} onChange={e => onChange(e.target.value)}
                  className={`${baseClass} appearance-none pr-10 cursor-pointer`}>
            {field.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
        </div>
    );
  }
  if (field.type === 'textarea') {
    return (
      <textarea value={value} onChange={e => onChange(e.target.value)} rows={field.rows||3}
                className={`${baseClass} resize-none`} placeholder={field.placeholder}/>
    );
  }
  if (field.type === 'image' || field.type === 'media') {
    return (
      <MediaField value={value} onChange={onChange} placeholder={field.placeholder}/>
    );
  }
  return (
      <div className="relative">
        {field.icon && (
            <field.icon
                className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"/>
        )}
        <input type={field.type || 'text'} value={value} onChange={e => onChange(e.target.value)}
               className={`${baseClass} ${field.icon ? 'pl-10' : ''}`} placeholder={field.placeholder}/>
      </div>
  );
};

// ─── Enhanced Modal ───────────────────────────────────
export const Modal: React.FC<{
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  maxWidth?: string
}> = ({open, onClose, title, subtitle, children, maxWidth = 'max-w-lg'}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (open) {
      setIsVisible(true);
      requestAnimationFrame(() => setIsAnimating(true));
    } else {
      setIsAnimating(false);
      const timer = setTimeout(() => setIsVisible(false), 200);
      return () => clearTimeout(timer);
    }
  }, [open]);

  if (!isVisible) return null;
  return (
      <div
          className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-200 ${isAnimating ? 'bg-black/50 backdrop-blur-sm' : 'bg-black/0'}`}
          onClick={onClose}>
        <div
            className={`bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full ${maxWidth} max-h-[85vh] overflow-hidden transform transition-all duration-200 ${isAnimating ? 'scale-100 opacity-100 translate-y-0' : 'scale-95 opacity-0 translate-y-4'}`}
            onClick={e => e.stopPropagation()}>
          <div
              className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white text-base">{title}</h2>
              {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
            </div>
            <button onClick={onClose}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
              <X className="w-4.5 h-4.5"/>
            </button>
          </div>
          <div className="p-6 overflow-y-auto max-h-[calc(85vh-80px)]">{children}</div>
        </div>
      </div>
  );
};

// ─── Status Badge ─────────────────────────────────────
export const StatusBadge: React.FC<{ active: boolean; label?: string }> = ({active, label}) => (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
        active
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
          : 'bg-gray-100 text-gray-500 dark:text-gray-400 dark:bg-gray-800 dark:text-gray-400'
    }`}>
    <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`}/>
      {label || (active ? '激活' : '禁用')}
  </span>
);

// ─── Template Badge ───────────────────────────────────
export const TemplateBadge: React.FC<{ template: string }> = ({template}) => {
  const config: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
    'default': {icon: Layout, color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'},
    'full-width': {icon: Monitor, color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'},
    'sidebar': {icon: Layers, color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'},
  };
  const c = config[template] || config['default'];
  const Icon = c.icon;
  return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${c.color}`}>
      <Icon className="w-3 h-3"/>{template}
    </span>
  );
};

// ─── Empty State ──────────────────────────────────────
export const EmptyState: React.FC<{
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  action?: React.ReactNode
}> = ({
                                                                                                      icon: Icon,
                                                                                                      title,
                                                                                                      desc,
                                                                                                      action
                                                                                                    }) => (
    <div className="flex flex-col items-center justify-center py-16 px-6">
      <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-gray-300 dark:text-gray-600"/>
      </div>
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
      <p className="text-xs text-gray-400 dark:text-gray-500 dark:text-gray-400 mt-1">{desc}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
);

// ─── Delete Confirm ───────────────────────────────────
export const DeleteConfirm: React.FC<{
  title: string;
  desc: string;
  onConfirm: () => void;
  onCancel: () => void;
  isPending?: boolean
}> = ({title, desc, onConfirm, onCancel, isPending}) => (
    <div className="text-center py-2">
      <div
          className="w-14 h-14 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-7 h-7 text-red-500"/>
      </div>
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">{title}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">{desc}</p>
      <div className="flex items-center justify-center gap-3">
        <button onClick={onCancel}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
          取消
        </button>
        <button onClick={onConfirm} disabled={isPending}
                className="px-5 py-2.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl transition-colors disabled:opacity-50 inline-flex items-center gap-2">
          {isPending && <Loader className="w-4 h-4 animate-spin"/>}
          确认删除
        </button>
      </div>
    </div>
);


