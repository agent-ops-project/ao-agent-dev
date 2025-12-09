import React from 'react';

interface LoginScreenProps {
  onLogin: () => void;
  isDarkTheme?: boolean;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin, isDarkTheme = false }) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: isDarkTheme ? '#fff' : '#000',
      padding: '20px',
      textAlign: 'center'
    }}>
      <div style={{ marginBottom: '20px' }}>
        <svg 
          width="64" 
          height="64" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="1.5" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        >
          <rect x="3" y="11" width="18" height="10" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <h2 style={{ marginBottom: '10px' }}>Agops Agent Copilot</h2>
      <p style={{ marginBottom: '30px', opacity: 0.8 }}>Please sign in to access your experiments</p>
      <button
        onClick={onLogin}
        style={{
          padding: '12px 24px',
          backgroundColor: 'var(--vscode-button-background)',
          color: 'var(--vscode-button-foreground)',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
          fontWeight: 600
        }}
      >
        Sign in with Google
      </button>
    </div>
  );
};
