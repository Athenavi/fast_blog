'use client';

interface ErrorStateProps {
  error: string;
  retryAction?: () => void;
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  type?: 'error' | 'warning' | 'info';
}

const ErrorState: React.FC<ErrorStateProps> = ({
  error,
  retryAction,
  secondaryAction,
  type = 'error'
}) => {
  // 安全访问错误信息
  const safeError = typeof error === 'string' ? error : String(error);
  
  // 判断是否为认证相关错误
  const isAuthError = safeError.includes('401') || 
                     safeError.toLowerCase().includes('unauthorized') || 
                     safeError.includes('requires_auth') ||
                     safeError.includes('登录') ||
                     safeError.includes('认证');
  
  // 根据错误类型选择图标和样式
  const getErrorConfig = () => {
    if (isAuthError) {
      return {
        icon: (
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        ),
        borderColor: 'border-yellow-200 dark:border-yellow-800',
        textColor: 'text-yellow-500',
        title: '需要登录',
        message: safeError || '您需要登录才能访问此内容'
      };
    }
    
    switch (type) {
      case 'warning':
        return {
          icon: (
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ),
          borderColor: 'border-yellow-200 dark:border-yellow-800',
          textColor: 'text-yellow-500',
          title: '警告',
          message: safeError
        };
      case 'info':
        return {
          icon: (
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          borderColor: 'border-blue-200 dark:border-blue-800',
          textColor: 'text-blue-500',
          title: '提示',
          message: safeError
        };
      case 'error':
      default:
        return {
          icon: (
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          borderColor: 'border-red-200 dark:border-red-800',
          textColor: 'text-red-500',
          title: '加载失败',
          message: safeError
        };
    }
  };
  
  const config = getErrorConfig();
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="container mx-auto px-4">
        <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm ${config.borderColor} p-8 max-w-lg mx-auto`}>
          <div className={`${config.textColor} mb-4`}>
            {config.icon}
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 text-center">{config.title}</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6 text-center">{config.message}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {retryAction && (
              <button
                onClick={retryAction}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-center"
              >
                重试
              </button>
            )}
            {secondaryAction && (
              <button
                onClick={secondaryAction.onClick}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors text-center"
              >
                {secondaryAction.label}
              </button>
            )}
          </div>
          
          {isAuthError && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4 text-center">
              请前往登录页面进行身份验证
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorState;