import React, { useState, useRef, useEffect } from 'react';
import { useIsVsCodeDarkTheme } from '../../utils/themeUtils';
import { ProcessCard } from './ProcessCard';
import { GraphData, ProcessInfo } from '../../types';

interface UserInfo {
  displayName?: string;
  avatarUrl?: string;
  email?: string;
}

interface ExperimentsViewProps {
  runningProcesses: ProcessInfo[];
  finishedProcesses: ProcessInfo[];
  onCardClick?: (process: ProcessInfo) => void;
  isDarkTheme?: boolean;
  user?: UserInfo;
  onLogout?: () => void;
  onLogin?: () => void;
}

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({
  runningProcesses,
  finishedProcesses,
  onCardClick,
  isDarkTheme = false,
  user,
  onLogout,
  onLogin,
}) => {
  const [hoveredCards, setHoveredCards] = useState<Set<string>>(new Set());
  const [menuOpen, setMenuOpen] = useState(false);
  const userRowRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Simple inline icons to avoid adding dependencies
  const IconLogout = ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path d="M16 13v-2H7V8l-5 4 5 4v-3z" fill="currentColor" />
      <path d="M20 3h-8v2h8v14h-8v2h8c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" fill="currentColor" />
    </svg>
  );

  // Close menu when clicking outside or pressing Escape
  useEffect(() => {
    if (!menuOpen) return;

    const handleDocClick = (e: MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (userRowRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setMenuOpen(false);
    };

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };

    document.addEventListener('mousedown', handleDocClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleDocClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [menuOpen]);

  // Footer layout constants
  const footerHeight = 60; // px

  // Debug logging
  console.log('ExperimentsView render - runningProcesses:', runningProcesses);
  console.log('ExperimentsView render - finishedProcesses:', finishedProcesses);
  console.log('ExperimentsView render - user:', user);

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    padding: '20px 20px',
    paddingBottom: `${footerHeight + 20}px`, // reserve space for footer
    height: '100%',
    maxHeight: '100%',
    overflowY: 'auto',
    boxSizing: 'border-box',
    backgroundColor: isDarkTheme ? '#252525' : '#F0F0F0',
    color: isDarkTheme ? '#FFFFFF' : '#000000',
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: isDarkTheme ? '#FFFFFF' : '#000000',
  };

  const emptyStateStyle: React.CSSProperties = {
    textAlign: 'center',
    padding: '40px 20px',
    color: isDarkTheme ? '#CCCCCC' : '#666666',
  };

  const footerStyle: React.CSSProperties = {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: `${footerHeight}px`,
    padding: '8px 12px',
    boxSizing: 'border-box',
    borderTop: `1px solid ${isDarkTheme ? '#3a3a3a' : '#e0e0e0'}`,
    backgroundColor: isDarkTheme ? '#1e1e1e' : '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    zIndex: 10,
  };

  const userRowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    cursor: user ? 'pointer' : 'default',
    flex: '1',
  };

  const loginButtonStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 16px',
    fontSize: 14,
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: '#007acc',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    transition: 'background-color 0.2s',
  };

  const loginButtonHoverStyle: React.CSSProperties = {
    ...loginButtonStyle,
    backgroundColor: '#005a9e',
  };

  const avatarStyle: React.CSSProperties = {
    width: 44,
    height: 44,
    borderRadius: '50%',
    objectFit: 'cover',
    backgroundColor: '#ddd',
  };

  const nameBlockStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    lineHeight: 1,
    minWidth: 0,
  };

  const nameStyle: React.CSSProperties = {
    fontSize: 14,
    fontWeight: 600,
    color: isDarkTheme ? '#FFFFFF' : '#111111',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  };

  const emailStyle: React.CSSProperties = {
    marginTop:5,
    fontSize: 12,
    color: isDarkTheme ? '#BBBBBB' : '#666666',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  };

  const menuStyle: React.CSSProperties = {
    position: 'absolute',
    right: 12,
    bottom: `${footerHeight + 8}px`,
    minWidth: 140,
    borderRadius: 6,
    overflow: 'hidden',
    boxShadow: '0 6px 16px rgba(0,0,0,0.12)',
    backgroundColor: isDarkTheme ? '#2b2b2b' : '#ffffff',
    border: `1px solid ${isDarkTheme ? '#3a3a3a' : '#e6e6e6'}`,
    zIndex: 20,
  };

  const menuItemStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 12px',
    fontSize: 14,
    cursor: 'pointer',
    color: isDarkTheme ? '#ffffff' : '#111111',
  };

  const handleCardHover = (cardId: string, isEntering: boolean) => {
    setHoveredCards((prev) => {
      const newSet = new Set(prev);
      if (isEntering) {
        newSet.add(cardId);
      } else {
        newSet.delete(cardId);
      }
      return newSet;
    });
  };

  const handleLogoutClick = () => {
    setMenuOpen(false);
    if (onLogout) onLogout();
    else console.log('Logout clicked (no handler provided)');
  };

  const handleLoginClick = () => {
    if (onLogin) onLogin();
    else console.log('Login clicked (no handler provided)');
  };

  const renderExperimentSection = (
    processes: ProcessInfo[],
    sectionTitle: string,
    sectionPrefix: string,
    marginTop?: number
  ) => {
    if (processes.length === 0) return null;

    return (
      <>
        <div style={{ ...titleStyle, ...(marginTop && { marginTop }) }}>
          {sectionTitle}
        </div>
        {processes.map((process) => {
          const cardId = `${sectionPrefix}-${process.session_id}`;
          const isHovered = hoveredCards.has(cardId);
          const nodeColors = process.color_preview || [];
          return (
            <ProcessCard
              key={process.session_id}
              process={process}
              isHovered={isHovered}
              isDarkTheme={isDarkTheme}
              nodeColors={nodeColors}
              onClick={() => onCardClick && onCardClick(process)}
              onMouseEnter={() => handleCardHover(cardId, true)}
              onMouseLeave={() => handleCardHover(cardId, false)}
            />
          );
        })}
      </>
    );
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

        {/* Footer */}
        <div style={footerStyle}>
          {user ? (
            <>
              <div
                ref={userRowRef}
                style={userRowStyle}
                onClick={() => setMenuOpen((s) => !s)}
                role="button"
                aria-haspopup="true"
                aria-expanded={menuOpen}
              >
                <img
                  src={user.avatarUrl || 'https://www.gravatar.com/avatar/?d=mp&s=200'}
                  alt={user.displayName || 'User avatar'}
                  style={avatarStyle}
                />
                <div style={nameBlockStyle}>
                  <div style={nameStyle}>{user.displayName || 'User'}</div>
                  <div style={emailStyle}>{user.email || ''}</div>
                </div>
              </div>

              {menuOpen && (
                <div ref={menuRef} style={menuStyle}>             
                  <div
                    style={{ ...menuItemStyle, borderTop: `1px solid ${isDarkTheme ? '#3a3a3a' : '#eee'}` }}
                    onClick={handleLogoutClick}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', marginRight: 8 }}>
                      <IconLogout />
                    </span>
                    Logout
                  </div>
                </div>
              )}
            </>
          ) : (
            <button
              style={loginButtonStyle}
              onClick={handleLoginClick}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#005a9e';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#007acc';
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="currentColor"/>
              </svg>
              Sign in with Google
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {renderExperimentSection(runningProcesses, 'Running', 'running')}
      {renderExperimentSection(finishedProcesses, 'Finished', 'finished', runningProcesses.length > 0 ? 32 : 0)}

      {/* Footer (always present) */}
      <div style={footerStyle}>
        {user ? (
          <>
            <div
              ref={userRowRef}
              style={userRowStyle}
              onClick={() => setMenuOpen((s) => !s)}
              role="button"
              aria-haspopup="true"
              aria-expanded={menuOpen}
            >
              <img
                src={user.avatarUrl || 'https://www.gravatar.com/avatar/?d=mp&s=200'}
                alt={user.displayName || 'User avatar'}
                style={avatarStyle}
              />
              <div style={nameBlockStyle}>
                <div style={nameStyle}>{user.displayName || 'User'}</div>
                <div style={emailStyle}>{user.email || ''}</div>
              </div>        
            </div>

            {menuOpen && (
              <div ref={menuRef} style={menuStyle}>           
                <div style={{ ...menuItemStyle, borderTop: `1px solid ${isDarkTheme ? '#3a3a3a' : '#eee'}` }} onClick={handleLogoutClick}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', marginRight: 8 }}>
                    <IconLogout />
                  </span>
                  Logout
                </div>
              </div>
            )}
          </>
        ) : (
          <button
            style={loginButtonStyle}
            onClick={handleLoginClick}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#005a9e';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#007acc';
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="currentColor"/>
            </svg>
            Sign in with Google
          </button>
        )}
      </div>
    </div>
  );
};