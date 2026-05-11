import React, {Suspense} from 'react';
import ClientQrScanHandlerPage from './ClientQrScanHandlerPage';

const QrScanHandlerPageWrapper = () => {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      <ClientQrScanHandlerPage />
    </Suspense>
  );
};

export default QrScanHandlerPageWrapper;