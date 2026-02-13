'use client';

import React, {useEffect, useState} from 'react';
import {
    FaArchive,
    FaCog,
    FaDatabase,
    FaDownload,
    FaExclamationTriangle,
    FaSpinner,
    FaTable,
    FaTrash
} from 'react-icons/fa';
import {BackupService} from '@/lib/api';

interface BackupFile {
  name: string;
  type: 'schema' | 'data' | 'all' | 'unknown';
  size: number; // in bytes
  created_at: string;
}

const BackupManagement = () => {
  const [backupFiles, setBackupFiles] = useState<BackupFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBackupModal, setShowBackupModal] = useState(false);
  const [backupProgress, setBackupProgress] = useState(0);
  const [backupTitle, setBackupTitle] = useState('');
  const [backupMessage, setBackupMessage] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteFilename, setDeleteFilename] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Load backup files
  useEffect(() => {
    loadBackupFiles();
  }, []);

  const loadBackupFiles = async () => {
    try {
      setLoading(true);
      const response = await BackupService.getBackups();
      
      if (response.success && response.data) {
        // 转换后端返回的数据格式为页面所需的格式
        const transformedData = response.data.data.map(item => ({
          name: item.name,
          type: item.type,
          size: item.size,
          created_at: item.created_at
        }));
        setBackupFiles(transformedData);
      } else {
        console.error('Failed to load backup files:', response.error || (response as any).message);
        setBackupFiles([]);
      }
    } catch (error: any) {
      console.error('Failed to load backup files:', error);
      alert((error as Error).message || '加载备份文件失败');
      setBackupFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getBackupTypeLabel = (type: string) => {
    switch (type) {
      case 'schema':
        return '结构备份';
      case 'data':
        return '数据备份';
      case 'all':
        return '完整备份';
      default:
        return '未知类型';
    }
  };

  const getBackupTypeColor = (type: string) => {
    switch (type) {
      case 'schema':
        return 'bg-blue-100 text-blue-800';
      case 'data':
        return 'bg-green-100 text-green-800';
      case 'all':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getBackupIcon = (type: string) => {
    switch (type) {
      case 'schema':
        return <FaDatabase className="text-sm" />;
      case 'data':
        return <FaTable className="text-sm" />;
      case 'all':
        return <FaArchive className="text-sm" />;
      default:
        return <FaArchive className="text-sm" />;
    }
  };

  const getBackupBgColor = (type: string) => {
    switch (type) {
      case 'schema':
        return 'bg-blue-100 text-blue-600';
      case 'data':
        return 'bg-green-100 text-green-600';
      case 'all':
        return 'bg-purple-100 text-purple-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const handleCreateBackup = async (type: 'schema' | 'data' | 'all') => {
    let title = '';
    let message = '';

    switch (type) {
      case 'schema':
        title = '备份数据库结构';
        message = '正在备份数据库表结构...';
        break;
      case 'data':
        title = '备份数据库数据';
        message = '正在备份数据库表数据...';
        break;
      case 'all':
        title = '完整数据库备份';
        message = '正在备份数据库结构和数据...';
        break;
    }

    setBackupTitle(title);
    setBackupMessage(message);
    setBackupProgress(0);
    setShowBackupModal(true);

    try {
      // 开始进度指示
      setBackupProgress(10);
      
      const response = await BackupService.createBackup(type);
      
      if (response.success) {
        setBackupProgress(100);
        
        // 重新加载备份列表以显示新创建的备份
        await loadBackupFiles();
        
        setTimeout(() => {
          setShowBackupModal(false);
          alert((response as any).message || '备份成功！');
        }, 500);
      } else {
        setShowBackupModal(false);
        console.error('Backup failed:', response.error || (response as any).message);
        alert((response as any).message || response.error || '备份失败');
      }
    } catch (error: any) {
      setShowBackupModal(false);
      console.error('Backup failed:', error);
      alert((error as Error).message || '备份失败，请检查网络连接和服务器状态');
    }
  };

  const handleDeleteClick = (filename: string) => {
    setDeleteFilename(filename);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    setIsDeleting(true);
    
    try {
      const response = await BackupService.deleteBackup(deleteFilename);
      
      if (response.success) {
        // 重新加载备份列表以移除已删除的备份
        await loadBackupFiles();
        
        setShowDeleteModal(false);
        setIsDeleting(false);
        alert((response as any).message || '删除成功！');
      } else {
        setShowDeleteModal(false);
        setIsDeleting(false);
        console.error('Delete failed:', response.error || (response as any).message);
        alert((response as any).message || response.error || '删除失败');
      }
    } catch (error: any) {
      setIsDeleting(false);
      setShowDeleteModal(false);
      console.error('Delete failed:', error);
      alert((error as Error).message || '删除失败，请检查网络连接');
    }
  };

  const handleDownload = async (filename: string) => {
    try {
      const blob = await BackupService.downloadBackup(filename);
      
      // 创建临时链接下载文件
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // 清理临时链接
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('下载失败，请稍后重试');
    }
  };

  return (
    <div className="space-y-6">
      {/* 备份操作卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* 备份结构 */}
        <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-blue-500 transition-all hover:shadow-md">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-blue-100 text-blue-600 mr-4">
              <FaDatabase className="text-xl" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">备份数据库结构</h3>
              <p className="text-sm text-gray-600">仅备份表结构，不包含数据</p>
            </div>
          </div>
          <button
            onClick={() => handleCreateBackup('schema')}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
          >
            <FaDownload className="mr-2" /> 备份结构
          </button>
        </div>

        {/* 备份数据 */}
        <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-green-500 transition-all hover:shadow-md">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-green-100 text-green-600 mr-4">
              <FaTable className="text-xl" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">备份数据库数据</h3>
              <p className="text-sm text-gray-600">仅备份表数据，不包含结构</p>
            </div>
          </div>
          <button
            onClick={() => handleCreateBackup('data')}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center"
          >
            <FaDownload className="mr-2" /> 备份数据
          </button>
        </div>

        {/* 完整备份 */}
        <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-purple-500 transition-all hover:shadow-md">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-purple-100 text-purple-600 mr-4">
              <FaArchive className="text-xl" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">完整备份</h3>
              <p className="text-sm text-gray-600">备份数据库结构和数据</p>
            </div>
          </div>
          <button
            onClick={() => handleCreateBackup('all')}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center"
          >
            <FaArchive className="mr-2" /> 完整备份
          </button>
        </div>
      </div>

      {/* 备份文件列表 */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {/* 表格头部 */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">备份文件列表</h2>
          <div className="text-sm text-gray-500">
            共 <span className="font-semibold text-blue-600">{backupFiles.length}</span> 个备份文件
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="text-center py-12">
              <FaSpinner className="animate-spin mx-auto text-3xl text-blue-500" />
              <p className="mt-2 text-gray-500">加载中...</p>
            </div>
          ) : backupFiles.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      文件名
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      类型
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      大小
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {backupFiles.map((backup, index) => (
                    <tr key={index} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className={`flex-shrink-0 h-10 w-10 rounded-full ${getBackupBgColor(backup.type)} flex items-center justify-center`}>
                            {getBackupIcon(backup.type)}
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{backup.name}</div>
                            {backup.name.endsWith('.gz') && (
                              <span className="text-xs text-gray-500">压缩文件</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getBackupTypeColor(backup.type)}`}>
                          {getBackupTypeLabel(backup.type)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatFileSize(backup.size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(backup.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-3">
                          <button
                            onClick={() => handleDownload(backup.name)}
                            className="text-blue-600 hover:text-blue-800 p-2 rounded-full hover:bg-blue-50 transition-colors"
                            title="下载"
                          >
                            <FaDownload />
                          </button>
                          <button
                            onClick={() => handleDeleteClick(backup.name)}
                            className="text-red-600 hover:text-red-800 p-2 rounded-full hover:bg-red-50 transition-colors"
                            title="删除"
                          >
                            <FaTrash />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <FaArchive className="text-5xl text-gray-400 mx-auto" />
              <p className="text-gray-500 text-lg mt-4">暂无备份文件</p>
              <p className="text-sm text-gray-400 mt-2">点击上方的备份按钮创建第一个备份</p>
            </div>
          )}
        </div>
      </div>

      {/* 备份进度模态框 */}
      {showBackupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full transform transition-all">
            <div className="p-6">
              <div className="mt-3 text-center">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
                  <FaCog className="animate-spin text-blue-600" />
                </div>
                <h3 className="text-lg leading-6 font-medium text-gray-900 mt-2">{backupTitle}</h3>
                <div className="mt-2 px-7 py-3">
                  <p className="text-sm text-gray-500">{backupMessage}</p>
                  <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${backupProgress}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认模态框 */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full transform transition-all">
            <div className="p-6">
              <div className="mt-3 text-center">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <FaExclamationTriangle className="text-red-600" />
                </div>
                <h3 className="text-lg leading-6 font-medium text-gray-900 mt-2">确认删除</h3>
                <div className="mt-2 px-7 py-3">
                  <p className="text-sm text-gray-500">
                    您确定要删除备份文件 "<span className="font-medium">{deleteFilename}</span>" 吗？此操作不可撤销。
                  </p>
                  <div className="flex justify-center space-x-4 mt-6">
                    <button
                      onClick={confirmDelete}
                      disabled={isDeleting}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center"
                    >
                      {isDeleting ? <FaSpinner className="animate-spin mr-2" /> : null}
                      确认删除
                    </button>
                    <button
                      onClick={() => setShowDeleteModal(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                    >
                      取消
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BackupManagement;