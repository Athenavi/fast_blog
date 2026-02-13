'use client';

import React, {useEffect, useState} from 'react';

interface Config {
  current_version: string;
  frontend_version: string;
  auto_check_interval: number;
  backup_before_update: boolean;
  github_repo: string;
}

interface UpdateStatus {
  available: boolean;
  latest_version?: string;
  is_updating: boolean;
  progress: number;
  message: string;
  changelog?: string;
}

interface UpdateResponse {
  success: boolean;
  data?: {
    config: Config;
    update_status: UpdateStatus & {
      latest_version: string;
      changelog: string;
    };
  };
  error?: string;
}

interface CheckUpdateResponse {
  success: boolean;
  data?: {
    available: boolean;
    latest_version: string;
    changelog: string;
    current_version: string;
  };
  error?: string;
}

interface StartUpdateResponse {
  success: boolean;
  data?: {
    message: string;
    status: string;
  };
  error?: string;
}

interface ProgressResponse {
  success: boolean;
  data?: {
    is_updating: boolean;
    progress: number;
    message: string;
    latest_version: string;
  };
  error?: string;
}

interface BackupResponse {
  success: boolean;
  data?: {
    message: string;
    backup_path: string;
  };
  error?: string;
}

interface ConfigResponse {
  success: boolean;
  data?: {
    config: {
      github_repo: string;
      current_version: string;
      frontend_version: string;
      auto_check_interval: number;
      backup_before_update: boolean;
      update_allowed: boolean;
      min_update_interval: number;
    };
    status: {
      is_updating: boolean;
      last_attempt: number;
    };
  };
  error?: string;
}

// 注意：UpdateStatus 接口已在上面定义

const UpdatePage = () => {
  const [config, setConfig] = useState<Config>({
    current_version: '0.0.0',
    frontend_version: '0.0.0',
    auto_check_interval: 3600,
    backup_before_update: true,
    github_repo: ''
  });

  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>({
    available: false,
    latest_version: '',
    is_updating: false,
    progress: 0,
    message: '加载中...',
    changelog: ''
  });

  const [loading, setLoading] = useState(true);
  const [lastCheckTime, setLastCheckTime] = useState<number | null>(null);
  const [updateType, setUpdateType] = useState<'full' | 'frontend' | 'backend'>('full');

  const [toast, setToast] = useState({
    show: false,
    title: '',
    message: '',
    type: 'info' as 'info' | 'success' | 'warning' | 'error'
  });

  // 移除了更新按钮显示逻辑

  // 显示通知
  const showToast = (title: string, message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    setToast({
      show: true,
      title,
      message,
      type
    });
    
    setTimeout(() => {
      hideToast();
    }, 3000);
  };

  // 隐藏通知
  const hideToast = () => {
    setToast(prev => ({ ...prev, show: false }));
  };

  // 检查更新
  const checkUpdate = async () => {
    try {
      setUpdateStatus(prev => ({ ...prev, message: '正在检查更新...' }));
      
      const response: CheckUpdateResponse = await apiRequest('/update/check', {
        method: 'POST'
      });
      
      if (response.success && response.data) {
        setUpdateStatus(prev => ({
          ...prev,
          available: response.data!.available,
          latest_version: response.data!.latest_version,
          changelog: response.data!.changelog,
          message: '检查完成'
        }));
        
        if (response.data.available) {
          showToast('检查完成', `发现新版本: ${response.data.latest_version}`, 'success');
        } else {
          showToast('检查完成', '当前已是最新版本', 'info');
        }
      } else {
        showToast('错误', response.error || '检查更新失败', 'error');
        setUpdateStatus(prev => ({ ...prev, message: '检查失败' }));
      }
    } catch (error) {
      console.error('Check update error:', error);
      showToast('错误', '检查更新失败，请重试', 'error');
      setUpdateStatus(prev => ({ ...prev, message: '检查失败' }));
    }
  };

  // 执行更新（重定向到独立的更新管理界面）
  const performUpdate = async () => {
    showToast('提示', '请使用独立的更新管理工具进行系统更新', 'info');
    // 可以在这里打开新的窗口或重定向到专门的更新管理页面
    // window.open('/update-manager', '_blank');
  };

  // 不再需要轮询更新状态

  // 获取基础API URL
  const getApiBaseUrl = () => {
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      // 开发环境使用8000端口，生产环境使用相同端口
      const port = process.env.NODE_ENV === 'development' ? '8000' : window.location.port;
      return `${protocol}//${hostname}${port ? ':' + port : ''}`;
    }
    return '';
  };

  // API请求辅助函数
  const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/api/v1${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      ...options
    };
    
    try {
      const response = await fetch(url, defaultOptions);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  };

  // 页面加载时初始化
  useEffect(() => {
    loadUpdateStatus();
    // 每30秒刷新一次状态
    const interval = setInterval(loadUpdateStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // 加载版本状态
  const loadUpdateStatus = async () => {
    try {
      // 获取版本信息
      const versionResponse = await apiRequest('/version/full');
      
      if (versionResponse && versionResponse.versions) {
        setConfig({
          current_version: versionResponse.versions.backend?.version || '0.0.0',
          frontend_version: versionResponse.versions.frontend?.version || '0.0.0',
          auto_check_interval: 3600,
          backup_before_update: true,
          github_repo: versionResponse.versions.author?.repository || ''
        });
        
        setUpdateStatus({
          available: false,
          latest_version: versionResponse.versions.backend?.version || '0.0.0',
          is_updating: false,
          progress: 0,
          message: '版本信息加载完成',
          changelog: ''
        });
        
        setLastCheckTime(Date.now());
      } else {
        // 只在不是定时刷新时显示错误
        if (!lastCheckTime || Date.now() - lastCheckTime > 60000) {
          showToast('错误', '加载版本信息失败', 'error');
        }
      }
    } catch (error) {
      console.error('Load version status error:', error);
      // 只在不是定时刷新时显示错误
      if (!lastCheckTime || Date.now() - lastCheckTime > 60000) {
        showToast('错误', '无法连接到更新服务器', 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-blue-600 mb-3 flex items-center justify-center">
            <i className="fas fa-cloud-download-alt mr-3"></i>
            系统更新管理
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            保持您的系统处于最新状态，获取最新功能和安全更新
          </p>
          {loading && (
            <div className="mt-4 text-blue-600">
              <i className="fas fa-spinner fa-spin mr-2"></i>
              正在加载...
            </div>
          )}
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 当前版本信息卡片 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 border border-gray-200 dark:border-gray-700">
            <div className="bg-blue-600 text-white p-4 rounded-t-xl">
              <h5 className="text-lg font-semibold flex items-center">
                <i className="fas fa-info-circle mr-2"></i>
                当前版本信息
              </h5>
            </div>
            <div className="p-5">
              <div className="flex justify-between items-center mb-4">
                <span className="font-bold text-gray-700 dark:text-gray-300">后端版本:</span>
                <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                  {config.current_version}
                </span>
              </div>
              <div className="flex justify-between items-center mb-4">
                <span className="font-bold text-gray-700 dark:text-gray-300">前端版本:</span>
                <span className="bg-purple-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                  {config.frontend_version}
                </span>
              </div>
              <div className="flex justify-between items-center mb-4">
                <span className="font-bold text-gray-700 dark:text-gray-300">自动检查:</span>
                <span className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                  {Math.floor(config.auto_check_interval / 3600)} 小时
                </span>
              </div>
              <div className="flex justify-between items-center mb-4">
                <span className="font-bold text-gray-700 dark:text-gray-300">源仓库:</span>
                <span className="bg-purple-500 text-white px-3 py-1 rounded-full text-sm font-medium truncate max-w-[150px]">
                  {config.github_repo || '未知'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-bold text-gray-700 dark:text-gray-300">更新备份:</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  config.backup_before_update 
                    ? 'bg-green-500 text-white' 
                    : 'bg-yellow-500 text-gray-800'
                }`}>
                  {config.backup_before_update ? '启用' : '禁用'}
                </span>
              </div>
            </div>
          </div>

          {/* 更新操作卡片 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 border border-gray-200 dark:border-gray-700">
            <div className={`p-4 rounded-t-xl text-white ${
              updateStatus.available ? 'bg-green-500' : 'bg-gray-500'
            }`}>
              <h5 className="text-lg font-semibold flex items-center">
                <i className={`mr-2 ${
                  updateStatus.available ? 'fas fa-arrow-up' : 'fas fa-check-circle'
                }`}></i>
                {updateStatus.available ? '有可用更新' : '已是最新版本'}
              </h5>
            </div>
            <div className="p-5">
              <div id="update-status" className="mb-5">
                <div className="flex justify-between items-center mb-4">
                  <span className="font-bold text-gray-700 dark:text-gray-300">最新版本:</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    updateStatus.available 
                      ? 'bg-green-500 text-white' 
                      : 'bg-gray-500 text-white'
                  }`}>
                    {updateStatus.latest_version || '未知'}
                  </span>
                </div>

                {updateStatus.is_updating && (
                  <div className="mt-4">
                    <p className="font-bold mb-2">更新进度:</p>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2">
                      <div 
                        className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                        style={{ width: `${updateStatus.progress}%` }}
                      ></div>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">{updateStatus.message}</p>
                  </div>
                )}

                <div className="mt-4">
                  <p className="mb-0 flex items-center">
                    <span 
                      className={`w-3 h-3 rounded-full mr-2 ${
                        updateStatus.is_updating 
                          ? 'bg-yellow-500 animate-pulse' 
                          : 'bg-green-500'
                      }`}
                    ></span>
                    <span>{updateStatus.is_updating ? '更新进行中...' : '系统正常'}</span>
                  </p>
                </div>
              </div>

              <div className="space-y-3 mt-4">
                <div className="flex space-x-2">
                  <button 
                    onClick={checkUpdate}
                    disabled={updateStatus.is_updating}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center ${
                      updateStatus.is_updating 
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed dark:bg-gray-600 dark:text-gray-400' 
                        : 'bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-300 dark:hover:bg-blue-800'
                    }`}
                  >
                    <i className="fas fa-sync-alt mr-2"></i>
                    检查更新
                  </button>
                  
                  <button 
                    onClick={loadUpdateStatus}
                    disabled={loading || updateStatus.is_updating}
                    className={`py-2 px-3 rounded-lg font-medium transition-colors duration-200 flex items-center ${
                      loading || updateStatus.is_updating
                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed dark:bg-gray-700 dark:text-gray-400'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                    }`}
                  >
                    <i className={`fas ${loading ? 'fa-spinner fa-spin' : 'fa-refresh'} mr-1`}></i>
                  </button>
                </div>
                
                {showUpdateButton && (
                  <>
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        更新类型
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        <button
                          onClick={() => setUpdateType('full')}
                          className={`py-2 px-3 rounded-lg font-medium transition-colors duration-200 text-center ${
                            updateType === 'full'
                              ? 'bg-blue-500 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                          }`}
                        >
                          <i className="fas fa-sync mr-1"></i>
                          完整更新
                        </button>
                        <button
                          onClick={() => setUpdateType('frontend')}
                          className={`py-2 px-3 rounded-lg font-medium transition-colors duration-200 text-center ${
                            updateType === 'frontend'
                              ? 'bg-purple-500 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                          }`}
                        >
                          <i className="fas fa-desktop mr-1"></i>
                          仅前端
                        </button>
                        <button
                          onClick={() => setUpdateType('backend')}
                          className={`py-2 px-3 rounded-lg font-medium transition-colors duration-200 text-center ${
                            updateType === 'backend'
                              ? 'bg-orange-500 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                          }`}
                        >
                          <i className="fas fa-server mr-1"></i>
                          仅后端
                        </button>
                      </div>
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {updateType === 'full' && '更新整个系统（前后端）'}
                        {updateType === 'frontend' && '仅更新前端界面和组件'}
                        {updateType === 'backend' && '仅更新后端服务和API'}
                      </div>
                    </div>
                    <button 
                      onClick={performUpdate}
                      className="w-full py-2 px-4 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 transition-colors duration-200 flex items-center justify-center shadow-md hover:shadow-lg"
                    >
                      <i className="fas fa-download mr-2"></i>
                      {updateType === 'full' ? '立即更新' : 
                       updateType === 'frontend' ? '更新前端' : '更新后端'}
                    </button>
                  </>
                )}
                
                {lastCheckTime && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 text-center pt-2">
                    最后检查: {new Date(lastCheckTime).toLocaleString('zh-CN')}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 更新日志卡片 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 border border-gray-200 dark:border-gray-700">
            <div className="bg-cyan-500 text-white p-4 rounded-t-xl">
              <h5 className="text-lg font-semibold flex items-center">
                <i className="fas fa-file-alt mr-2"></i>
                更新日志
              </h5>
            </div>
            <div className="p-0">
              <div className="max-h-[300px] overflow-y-auto p-5">
                {updateStatus.changelog ? (
                  <div 
                    className="changelog-content prose max-w-none dark:prose-invert"
                    dangerouslySetInnerHTML={{ __html: updateStatus.changelog }}
                  ></div>
                ) : (
                  <div className="text-center py-10">
                    <i className="fas fa-file-alt text-gray-300 dark:text-gray-600 text-3xl mb-3"></i>
                    <p className="text-gray-500 dark:text-gray-400">
                      {updateStatus.is_updating ? '正在获取更新日志...' : '暂无更新日志'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 通知Toast */}
        <div className="fixed bottom-4 right-4 z-50">
          {toast.show && (
            <div 
              className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg border-l-4 p-4 min-w-[300px] transition-opacity duration-300 ${
                toast.type === 'info' ? 'border-blue-500' :
                toast.type === 'success' ? 'border-green-500' :
                toast.type === 'warning' ? 'border-yellow-500' : 'border-red-500'
              }`}
            >
              <div className="flex items-start">
                <i 
                  className={`mr-3 mt-0.5 text-lg ${
                    toast.type === 'info' ? 'fas fa-info-circle text-blue-500' :
                    toast.type === 'success' ? 'fas fa-check-circle text-green-500' :
                    toast.type === 'warning' ? 'fas fa-exclamation-circle text-yellow-500' : 'fas fa-times-circle text-red-500'
                  }`}
                ></i>
                <div>
                  <h6 className="font-semibold dark:text-white">{toast.title}</h6>
                  <p className="text-gray-600 dark:text-gray-400 text-sm">{toast.message}</p>
                </div>
                <button onClick={hideToast} className="ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                  <i className="fas fa-times"></i>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UpdatePage;