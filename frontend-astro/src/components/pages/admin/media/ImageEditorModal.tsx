'use client';

import React, {useState} from 'react';
import {useMutation, useQuery} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';
import {useToast} from '@/components/ui/toast-provider';
import {
  Crop, RotateCw, Droplets, Image, X, Save, RefreshCw, Loader,
} from 'lucide-react';

interface Props {
  mediaId: number;
  filename: string;
  onClose: () => void;
  onSaved: () => void;
}

const FILTERS = [
  {id: 'blur', label: '模糊'}, {id: 'sharpen', label: '锐化'},
  {id: 'emboss', label: '浮雕'}, {id: 'contour', label: '轮廓'},
  {id: 'smooth', label: '平滑'}, {id: 'edge_enhance', label: '边缘增强'},
];

export default function ImageEditorModal({mediaId, filename, onClose, onSaved}: Props) {
  const toast = useToast();
  const [tab, setTab] = useState<'info' | 'crop' | 'rotate' | 'filter'>('info');
  const [cropX, setCropX] = useState('0');
  const [cropY, setCropY] = useState('0');
  const [cropW, setCropW] = useState('200');
  const [cropH, setCropH] = useState('200');
  const [degrees, setDegrees] = useState('90');

  // Image info
  const {data: infoData, isLoading: infoLoading} = useQuery({
    queryKey: ['image-info', mediaId],
    queryFn: async () => {
      const r = await apiClient.get(`/media/edit/${mediaId}/info`);
      return r.data || {};
    },
  });

  const cropMut = useMutation({
    mutationFn: () => apiClient.post(`/media/edit/${mediaId}/crop`, {x: Number(cropX), y: Number(cropY), width: Number(cropW), height: Number(cropH)}),
    onSuccess: (r) => { if (r.success) { toast.success('裁剪成功'); onSaved(); } else toast.error(r.error); },
    onError: () => toast.error('裁剪失败'),
  });

  const rotateMut = useMutation({
    mutationFn: () => apiClient.post(`/media/edit/${mediaId}/rotate`, {degrees: Number(degrees)}),
    onSuccess: (r) => { if (r.success) { toast.success('旋转成功'); onSaved(); } else toast.error(r.error); },
    onError: () => toast.error('旋转失败'),
  });

  const filterMut = useMutation({
    mutationFn: (ft: string) => apiClient.post(`/media/edit/${mediaId}/filter`, {filter_type: ft}),
    onSuccess: (r) => { if (r.success) { toast.success('滤镜已应用'); onSaved(); } else toast.error(r.error); },
    onError: () => toast.error('滤镜应用失败'),
  });

  const grayMut = useMutation({
    mutationFn: () => apiClient.post(`/media/edit/${mediaId}/grayscale`),
    onSuccess: (r) => { if (r.success) { toast.success('已转为灰度图'); onSaved(); } else toast.error(r.error); },
    onError: () => toast.error('转换失败'),
  });

  const tabs = [
    {key: 'info', label: '信息', icon: Image},
    {key: 'crop', label: '裁剪', icon: Crop},
    {key: 'rotate', label: '旋转', icon: RotateCw},
    {key: 'filter', label: '滤镜', icon: Droplets},
  ] as const;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">图片编辑: {filename}</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500"/>
          </button>
        </div>

        {/* Tab nav */}
        <div className="flex gap-1 px-6 pt-4">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      tab === t.key ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}>
              <t.icon className="w-3.5 h-3.5"/>{t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6">
          {tab === 'info' && (
            <div className="space-y-3">
              {infoLoading ? (
                <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>
              ) : (
                <>
                  <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center">
                    <Image className="w-16 h-16 text-gray-400"/>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {infoData?.info ? Object.entries(infoData.info).map(([k, v]) => (
                      <div key={k} className="flex justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <span className="text-gray-500">{k}</span>
                        <span className="text-gray-900 dark:text-white font-mono text-xs">{String(v)}</span>
                      </div>
                    )) : <p className="col-span-2 text-gray-400 text-center py-4">无法获取图片信息</p>}
                  </div>
                </>
              )}
            </div>
          )}

          {tab === 'crop' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-500">设置裁剪区域坐标和尺寸</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  {label: 'X', val: cropX, set: setCropX},
                  {label: 'Y', val: cropY, set: setCropY},
                  {label: '宽度', val: cropW, set: setCropW},
                  {label: '高度', val: cropH, set: setCropH},
                ].map(f => (
                  <div key={f.label}>
                    <label className="text-xs text-gray-500 mb-1 block">{f.label}</label>
                    <input value={f.val} onChange={e => f.set(e.target.value)} type="number" min="0"
                           className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm"/>
                  </div>
                ))}
              </div>
              <button onClick={() => cropMut.mutate()} disabled={cropMut.isPending}
                      className="w-full py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50">
                {cropMut.isPending ? '处理中...' : '应用裁剪'}
              </button>
            </div>
          )}

          {tab === 'rotate' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-500">选择旋转角度</p>
              <div className="flex gap-2">
                {[90, 180, 270, -90].map(d => (
                  <button key={d} onClick={() => { setDegrees(String(d)); rotateMut.mutate(); }}
                          className="flex-1 py-3 bg-gray-100 dark:bg-gray-800 rounded-xl text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                    {d}°
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={degrees} onChange={e => setDegrees(e.target.value)} type="number"
                       className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm" placeholder="自定义角度"/>
                <button onClick={() => rotateMut.mutate()} disabled={rotateMut.isPending}
                        className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm hover:bg-blue-700 disabled:opacity-50">旋转</button>
              </div>
            </div>
          )}

          {tab === 'filter' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-500">应用图片滤镜效果</p>
              <div className="grid grid-cols-3 gap-2">
                {FILTERS.map(f => (
                  <button key={f.id} onClick={() => filterMut.mutate(f.id)} disabled={filterMut.isPending}
                          className="py-3 bg-gray-100 dark:bg-gray-800 rounded-xl text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50">
                    {f.label}
                  </button>
                ))}
              </div>
              <button onClick={() => grayMut.mutate()} disabled={grayMut.isPending}
                      className="w-full py-2.5 bg-gray-600 text-white rounded-xl text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-2">
                <Droplets className="w-4 h-4"/>转为灰度图
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">关闭</button>
          <button onClick={onSaved} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors inline-flex items-center gap-1.5">
            <Save className="w-3.5 h-3.5"/>完成
          </button>
        </div>
      </div>
    </div>
  );
}
