import React, {Suspense} from 'react';
import ClientOAuthSuccessPage from './ClientOAuthSuccessPage';

const OAuthSuccessPageWrapper = () => {
  return (
    <Suspense fallback={
      <div 
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: '#f0f2f5'
        }}
      >
        <div 
          style={{
            textAlign: 'center',
            padding: '2rem',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
          }}
        >
          <div style={{ fontSize: '3rem', color: '#4CAF50', marginBottom: '1rem' }}>✓</div>
          <h2 style={{ color: '#333' }}>Loading...</h2>
        </div>
      </div>
    }>
      <ClientOAuthSuccessPage />
    </Suspense>
  );
};

export default OAuthSuccessPageWrapper;