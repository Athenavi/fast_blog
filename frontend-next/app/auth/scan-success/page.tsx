'use client';

import {useEffect, useState} from 'react';

interface ScanSuccessPageProps {
  searchParams?: {
    message?: string;
  };
}

const ScanSuccessPage = ({ searchParams }: ScanSuccessPageProps) => {
  const [message, setMessage] = useState<string>('扫码成功，请在手机端确认登录');

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
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
              <i className="fas fa-check text-green-600 text-2xl"></i>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">扫码成功</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <div className="text-sm text-gray-500">
              <i className="fas fa-info-circle mr-1"></i>
              请返回电脑端完成登录
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScanSuccessPage;