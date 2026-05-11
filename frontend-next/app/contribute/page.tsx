import React, {Suspense} from 'react';
import ClientContributePage from './ClientContributePage';

const ContributePageWrapper = () => {
  return (
    <Suspense fallback={
      <div className="container mx-auto px-4 py-8 max-w-5xl flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    }>
      <ClientContributePage />
    </Suspense>
  );
};

export default ContributePageWrapper;