import React, {Suspense} from 'react';
import ClientVipPaymentPage from './ClientVipPaymentPage';

const VipPaymentPageWrapper = () => {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 flex items-center justify-center">Loading payment...</div>}>
      <ClientVipPaymentPage />
    </Suspense>
  );
};

export default VipPaymentPageWrapper;