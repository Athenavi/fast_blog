'use client';

import Link from 'next/link';
import {useEffect, useState} from 'react';

interface ScanErrorPageProps {
  searchParams?: {
    message?: string;
  };
}

const ScanErrorPage = ({ searchParams }: ScanErrorPageProps) => {
  const [message, setMessage] = useState<string>('扫码失败，请重试');

  useEffect(() => {
    if (searchParams?.message) {
      setMessage(searchParams.message);
    }
  }, [searchParams]);

  return (
    <div className="min-h-full flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-4">
              <i className="fas fa-times text-red-600 text-2xl"></i>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">扫码失败</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <Link 
              href="/login"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <i className="fas fa-arrow-left mr-2"></i>
              返回登录页
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScanErrorPage;