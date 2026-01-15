import React, { useState, useEffect } from 'react';
import { LessonsView, Lesson } from '../../../shared_components/components/lessons/LessonsView';
import { useIsVsCodeDarkTheme } from '../../../shared_components/utils/themeUtils';

declare global {
  interface Window {
    vscode?: {
      postMessage: (message: any) => void;
    };
    isLessonsView?: boolean;
  }
}

export const LessonsTabApp: React.FC = () => {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const isDarkTheme = useIsVsCodeDarkTheme();

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data;

      switch (message.type) {
        case 'lessons_list':
          console.log('[LessonsTabApp] Received lessons_list:', message.lessons);
          setLessons(message.lessons || []);
          break;
      }
    };

    window.addEventListener('message', handleMessage);

    // Send ready message to request lessons data
    if (window.vscode) {
      window.vscode.postMessage({ type: 'ready' });
    }

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  return (
    <div
      style={{
        width: '100%',
        height: '100vh',
        overflow: 'hidden',
      }}
    >
      <LessonsView lessons={lessons} isDarkTheme={isDarkTheme} />
    </div>
  );
};
