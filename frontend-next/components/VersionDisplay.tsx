'use client';

import React, {useEffect, useState} from 'react';
import {getVersionInfo, isDevelopment, isProduction} from '@/lib/version';

interface VersionDisplayProps {
  showDetailed?: boolean;
  className?: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ 
  showDetailed = false, 
  className = '' 
}) => {
  const [versionInfo, setVersionInfo] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setVersionInfo(getVersionInfo());
  }, []);

  const copyVersionInfo = () => {
    if (versionInfo) {
      const infoText = `
应用版本: ${versionInfo.version}
构建时间: ${versionInfo.buildTime}
环境: ${versionInfo.environment}
框架: ${versionInfo.framework}
React版本: ${versionInfo.reactVersion}
      `.trim();
      
      navigator.clipboard.writeText(infoText).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  if (!versionInfo) return null;

  return (
    <div className={`text-xs text-gray-500 dark:text-gray-400 ${className}`}>
      <div className="flex items-center space-x-2">
        <span>v{versionInfo.version}</span>
        {isDevelopment() && (
          <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">
            DEV
          </span>
        )}
        {isProduction() && (
          <span className="px-1.5 py-0.5 bg-green-100 text-green-800 text-xs rounded-full">
            PROD
          </span>
        )}
        <button
          onClick={copyVersionInfo}
          className="opacity-0 hover:opacity-100 transition-opacity text-blue-500 hover:text-blue-700"
          title="复制版本信息"
        >
          {copied ? '✓' : '📋'}
        </button>
      </div>
      
      {showDetailed && (
        <div className="mt-2 text-xs space-y-1">
          <div>构建时间: {new Date(versionInfo.buildTime).toLocaleString()}</div>
          <div>框架: {versionInfo.framework}</div>
          <div>Node.js: {versionInfo.nodeVersion}</div>
          {versionInfo.commitHash && versionInfo.commitHash !== 'unknown' && (
            <div>Commit: {versionInfo.commitHash.substring(0, 8)}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default VersionDisplay;