'use client';

import {useState} from 'react';
import {apiClient} from '@/lib/api';

export default function TestApiPage() {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const testAuth = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/users/me');
      if (response.success && response.data) {
        setResult(`认证成功！用户信息: ${JSON.stringify(response.data, null, 2)}`);
      } else {
        setResult(`认证失败: ${response.error}`);
      }
    } catch (error) {
      setResult(`请求失败: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">API 测试页面</h1>
          
          <div className="mb-6">
            <button
              onClick={testAuth}
              disabled={loading}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {loading ? '测试中...' : '测试认证API'}
            </button>
          </div>
          
          {result && (
            <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-md">
              <h2 className="text-lg font-mono text-gray-800 dark:text-gray-200">结果:</h2>
              <pre className="whitespace-pre-wrap break-words text-sm text-gray-700 dark:text-gray-300">{result}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}