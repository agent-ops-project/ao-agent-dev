import React from 'react';
import { useIsVsCodeDarkTheme } from '../utils/themeUtils';
import { MiniGraphView } from './GraphView';
import { GraphData } from '../types';

interface ProcessInfo {
  pid: number;
  script_name: string;
  session_id: string;
  status: string;
  role?: string;
}

interface ExperimentsViewProps {
  runningProcesses: ProcessInfo[];
  finishedProcesses: ProcessInfo[];
  onCardClick?: (process: ProcessInfo) => void;
}

// Example graph data (same as overview)
const exampleGraph: GraphData = {
  nodes: [
    { id: '1', input: 'User input data', output: 'Processed user data', codeLocation: 'file.py:15', label: 'User Input Handler', border_color: '#ff3232' },
    { id: '2', input: 'Processed user data', output: 'Validated data', codeLocation: 'file.py:42', label: 'Data Validator', border_color: '#00c542' },
    { id: '3', input: 'Validated data', output: 'Database query', codeLocation: 'file.py:78', label: 'Query Builder', border_color: '#ffba0c' },
    { id: '4', input: 'Database query', output: 'Query results', codeLocation: 'file.py:23', label: 'Query Executor', border_color: '#ffba0c' },
    { id: '5', input: 'Query results', output: 'Formatted response', codeLocation: 'file.py:56', label: 'Response Formatter', border_color: '#00c542' },
    { id: '6', input: 'Validated data', output: 'Cache key', codeLocation: 'file.py:12', label: 'Cache Key Generator', border_color: '#ff3232' },
    { id: '7', input: 'Cache key', output: 'Cache status', codeLocation: 'file.py:34', label: 'Cache Manager', border_color: '#00c542' },
  ],
  edges: [
    { id: 'e1-2', source: '1', target: '2' },
    { id: 'e2-3', source: '2', target: '3' },
    { id: 'e3-4', source: '3', target: '4' },
    { id: 'e4-5', source: '4', target: '5' },
    { id: 'e2-6', source: '2', target: '6' },
    { id: 'e6-7', source: '6', target: '7' },
    { id: 'e7-5', source: '7', target: '5' },
  ],
};

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({ runningProcesses, finishedProcesses, onCardClick }) => {
  const isDarkTheme = useIsVsCodeDarkTheme();
  
  const containerStyle: React.CSSProperties = {
    padding: '20px',
    height: '100%',
    overflowY: 'auto',
    backgroundColor: isDarkTheme ? '#252525' : '#F0F0F0',
    color: isDarkTheme ? '#FFFFFF' : '#000000',
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: isDarkTheme ? '#FFFFFF' : '#000000',
  };

  const processCardStyle: React.CSSProperties = {
    backgroundColor: isDarkTheme ? '#3C3C3C' : '#FFFFFF',
    border: `1px solid ${isDarkTheme ? '#6B6B6B' : '#CCCCCC'}`,
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '12px',
    boxShadow: isDarkTheme ? '0 2px 4px rgba(0,0,0,0.3)' : '0 2px 4px rgba(0,0,0,0.1)',
    cursor: 'pointer',
  };

  const processTitleStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: 'bold',
    marginBottom: '8px',
    color: isDarkTheme ? '#FFFFFF' : '#000000',
  };

  const processDetailStyle: React.CSSProperties = {
    fontSize: '12px',
    color: isDarkTheme ? '#CCCCCC' : '#666666',
    marginBottom: '4px',
  };

  const statusStyle: React.CSSProperties = {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '10px',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  };

  const getStatusStyle = (status: string): React.CSSProperties => {
    const baseStyle = { ...statusStyle };
    if (status === 'running') {
      return {
        ...baseStyle,
        backgroundColor: '#27C93F',
        color: '#FFFFFF',
      };
    } else {
      return {
        ...baseStyle,
        backgroundColor: '#FF6B6B',
        color: '#FFFFFF',
      };
    }
  };

  const emptyStateStyle: React.CSSProperties = {
    textAlign: 'center',
    padding: '40px 20px',
    color: isDarkTheme ? '#CCCCCC' : '#666666',
  };

  if (runningProcesses.length === 0 && finishedProcesses.length === 0) {
    return (
      <div style={containerStyle}>
        <div style={titleStyle}>Develop Processes</div>
        <div style={emptyStateStyle}>
          <div style={{ fontSize: '16px', marginBottom: '8px' }}>No develop processes</div>
          <div style={{ fontSize: '12px' }}>
            Start a develop process to see it here
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {runningProcesses.length > 0 && (
        <>
          <div style={titleStyle}>Running ({runningProcesses.length})</div>
          {runningProcesses.map((process) => (
            <div key={process.pid} style={processCardStyle} onClick={() => onCardClick && onCardClick(process)}>
              <div style={processTitleStyle}>
                {process.script_name}
                <span style={getStatusStyle(process.status)}>
                  {process.status}
                </span>
              </div>
              <div style={processDetailStyle}>
                <strong>PID:</strong> {process.pid}
              </div>
              <div style={processDetailStyle}>
                <strong>Session:</strong> {process.session_id.substring(0, 8)}...
              </div>
            </div>
          ))}
        </>
      )}
      {finishedProcesses.length > 0 && (
        <>
          <div style={{ ...titleStyle, marginTop: runningProcesses.length > 0 ? 32 : 0 }}>Finished ({finishedProcesses.length})</div>
          {finishedProcesses.map((process) => (
            <div key={process.pid} style={processCardStyle} onClick={() => onCardClick && onCardClick(process)}>
              <div style={processTitleStyle}>
                {process.script_name}
                <span style={getStatusStyle(process.status)}>
                  {process.status}
                </span>
              </div>
              <div style={processDetailStyle}>
                <strong>PID:</strong> {process.pid}
              </div>
              <div style={processDetailStyle}>
                <strong>Session:</strong> {process.session_id.substring(0, 8)}...
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}; 