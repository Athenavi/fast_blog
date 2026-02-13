'use client';

import React, {Suspense} from 'react';
import ClientSearchPage from './ClientSearchPage';

const SearchPage = () => {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading search...</div>}>
      <ClientSearchPage />
    </Suspense>
  );
};

export default SearchPage;
