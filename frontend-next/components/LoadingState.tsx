'use client';

interface LoadingStateProps {
  message?: string;
  fullScreen?: boolean;
}

const LoadingState: React.FC<LoadingStateProps> = ({
  message = '加载中...',
  fullScreen = false
}) => {
  const containerClasses = fullScreen
    ? 'min-h-screen flex items-center justify-center'
    : 'py-12 flex items-center justify-center';

  return (
    <div className={containerClasses}>
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        <p className="text-gray-600 dark:text-gray-400">{message}</p>
      </div>
    </div>
  );
};

export default LoadingState;