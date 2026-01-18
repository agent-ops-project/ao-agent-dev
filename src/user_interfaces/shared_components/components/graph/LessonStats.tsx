import React from 'react';
import { Lesson } from '../lessons/LessonsView';

interface LessonStatsProps {
  sessionId: string;
  lessons: Lesson[];
  isDarkTheme?: boolean;
  onNavigateToLessons?: () => void;
}

export const LessonStats: React.FC<LessonStatsProps> = ({
  sessionId,
  lessons,
  isDarkTheme = false,
  onNavigateToLessons,
}) => {
  // Count lessons extracted from this graph
  const lessonsExtractedFrom = lessons.filter(
    (lesson) => lesson.extractedFrom?.sessionId === sessionId
  ).length;

  // Count lessons applied to this graph
  const lessonsAppliedTo = lessons.filter(
    (lesson) => lesson.appliedTo?.some((app) => app.sessionId === sessionId)
  ).length;

  return (
    <div
      style={{
        position: 'sticky',
        top: '56px',
        zIndex: 100,
        height: 0,
        overflow: 'visible',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '-2px',
          left: '12px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          backgroundColor: isDarkTheme ? '#0e639c' : '#007acc',
          borderRadius: '8px',
          boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
          border: 'none',
          cursor: onNavigateToLessons ? 'pointer' : 'default',
          fontSize: '12px',
          color: '#ffffff',
          fontWeight: 500,
          transition: 'background-color 0.2s',
        }}
        onClick={onNavigateToLessons}
        onMouseEnter={(e) => {
          if (onNavigateToLessons) {
            e.currentTarget.style.backgroundColor = isDarkTheme ? '#1177bb' : '#005a9e';
          }
        }}
        onMouseLeave={(e) => {
          if (onNavigateToLessons) {
            e.currentTarget.style.backgroundColor = isDarkTheme ? '#0e639c' : '#007acc';
          }
        }}
        title="View lessons"
      >
        <span>{lessonsExtractedFrom} lesson{lessonsExtractedFrom !== 1 ? 's' : ''} extracted</span>
        <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>|</span>
        <span>{lessonsAppliedTo} lesson{lessonsAppliedTo !== 1 ? 's' : ''} applied</span>
      </div>
    </div>
  );
};
