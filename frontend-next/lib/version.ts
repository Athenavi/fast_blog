// 版本信息工具函数
interface VersionInfo {
  version: string;
  buildTime: string;
  environment: string;
  framework: string;
  nodeVersion: string;
  reactVersion: string;
  commitHash?: string;
}

// 从 version.ini 读取版本信息
const getVersionFromIni = (): Partial<VersionInfo> => {
  try {
    // 在浏览器环境中，我们无法直接读取文件
    // 这里返回默认值或通过环境变量获取
    return {
      version: process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0',
      buildTime: process.env.NEXT_PUBLIC_BUILD_TIME || new Date().toISOString(),
      framework: 'Next.js 16.1.6',
      nodeVersion: process.env.NODE_VERSION || '25.2.1',
      reactVersion: '19.0.0'
    };
  } catch (error) {
    console.warn('Failed to read version info:', error);
    return {
      version: '0.1.0',
      buildTime: new Date().toISOString(),
      framework: 'Next.js 16.1.6',
      nodeVersion: '25.2.1',
      reactVersion: '19.0.0'
    };
  }
};

// 获取完整的版本信息
export const getVersionInfo = (): VersionInfo => {
  const baseInfo = getVersionFromIni();

  return {
    version: baseInfo.version || '0.1.0',
    buildTime: baseInfo.buildTime || new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    framework: baseInfo.framework || 'Next.js',
    nodeVersion: baseInfo.nodeVersion || process.version,
    reactVersion: baseInfo.reactVersion || '19.0.0',
    commitHash: process.env.NEXT_PUBLIC_COMMIT_HASH
  };
};

// 检查是否为开发环境
export const isDevelopment = (): boolean => {
  return process.env.NODE_ENV === 'development';
};

// 检查是否为生产环境
export const isProduction = (): boolean => {
  return process.env.NODE_ENV === 'production';
};

// 获取简短版本号
export const getShortVersion = (): string => {
  const info = getVersionInfo();
  return info.version;
};

// 获取构建时间
export const getBuildTime = (): string => {
  const info = getVersionInfo();
  return info.buildTime;
};