import React from 'react';

interface GraphHeaderProps {
  runName: string;
  isDarkTheme: boolean;
}

export const GraphHeader: React.FC<GraphHeaderProps> = ({
  runName,
  isDarkTheme,
}) => {
  return (
    <div
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 150,
        padding: '12px 20px',
        borderBottom: `1px solid ${isDarkTheme ? '#3c3c3c' : '#e0e0e0'}`,
        backgroundColor: isDarkTheme ? '#1e1e1e' : '#ffffff',
        color: isDarkTheme ? '#e5e5e5' : '#333333',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontSize: '16px',
          fontWeight: 600,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {runName || 'Untitled'}
      </div>
    </div>
  );
};
