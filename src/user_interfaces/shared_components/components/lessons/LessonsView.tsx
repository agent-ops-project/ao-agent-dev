import React from 'react';

export interface Lesson {
  id: string;
  title: string;
  category: string;
  description: string;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
  tags: string[];
}

interface LessonsViewProps {
  lessons: Lesson[];
  isDarkTheme: boolean;
}

function getCategoryColor(category: string): string {
  const categoryColors: Record<string, string> = {
    'Basics': '#4a9eff',
    'Prompting': '#7fc17b',
    'Optimization': '#d4a825',
    'Advanced Techniques': '#c586c0',
    'Best Practices': '#4ec9b0',
  };
  return categoryColors[category] || '#888888';
}

export const LessonsView: React.FC<LessonsViewProps> = ({ lessons, isDarkTheme }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: isDarkTheme ? "#1e1e1e" : "#ffffff",
        color: isDarkTheme ? "#e5e5e5" : "#333333",
        fontFamily: "var(--vscode-font-family, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "20px 24px",
          borderBottom: `1px solid ${isDarkTheme ? "#3c3c3c" : "#e0e0e0"}`,
          backgroundColor: isDarkTheme ? "#1e1e1e" : "#ffffff",
          flexShrink: 0,
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: "20px",
            fontWeight: 600,
            color: isDarkTheme ? "#e5e5e5" : "#333333",
          }}
        >
          LLM Lessons & Best Practices
        </h2>
        <p
          style={{
            margin: "8px 0 0 0",
            fontSize: "13px",
            color: isDarkTheme ? "#a0a0a0" : "#666666",
          }}
        >
          Learn best practices for working with Large Language Models
        </p>
      </div>

      {/* Lessons List */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px" }}>
        {lessons.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: isDarkTheme ? "#888888" : "#666666",
            }}
          >
            No lessons available
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {lessons.map((lesson) => (
              <div
                key={lesson.id}
                style={{
                  backgroundColor: isDarkTheme ? "#252525" : "#ffffff",
                  border: `1px solid ${isDarkTheme ? "#3c3c3c" : "#e0e0e0"}`,
                  borderRadius: "6px",
                  padding: "18px 20px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = isDarkTheme ? "#2d2d2d" : "#f9f9f9";
                  e.currentTarget.style.borderColor = isDarkTheme ? "#555" : "#ccc";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = isDarkTheme ? "#252525" : "#ffffff";
                  e.currentTarget.style.borderColor = isDarkTheme ? "#3c3c3c" : "#e0e0e0";
                }}
              >
                {/* Title and Category */}
                <div style={{ marginBottom: "8px" }}>
                  <h3
                    style={{
                      margin: "0 0 6px 0",
                      fontSize: "16px",
                      fontWeight: 600,
                      color: isDarkTheme ? "#e5e5e5" : "#333333",
                    }}
                  >
                    {lesson.title}
                  </h3>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: "600",
                        padding: "3px 8px",
                        borderRadius: "3px",
                        backgroundColor: getCategoryColor(lesson.category),
                        color: "#ffffff",
                      }}
                    >
                      {lesson.category}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: "500",
                        padding: "3px 8px",
                        borderRadius: "3px",
                        backgroundColor:
                          lesson.difficulty === 'Beginner'
                            ? 'rgba(127, 193, 123, 0.15)'
                            : lesson.difficulty === 'Intermediate'
                            ? 'rgba(212, 168, 37, 0.15)'
                            : 'rgba(224, 82, 82, 0.15)',
                        color:
                          lesson.difficulty === 'Beginner'
                            ? '#7fc17b'
                            : lesson.difficulty === 'Intermediate'
                            ? '#d4a825'
                            : '#e05252',
                      }}
                    >
                      {lesson.difficulty}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <p
                  style={{
                    margin: "0 0 12px 0",
                    fontSize: "13px",
                    lineHeight: "1.6",
                    color: isDarkTheme ? "#cccccc" : "#555555",
                  }}
                >
                  {lesson.description}
                </p>

                {/* Tags */}
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "6px",
                  }}
                >
                  {lesson.tags.map((tag: string) => (
                    <span
                      key={tag}
                      style={{
                        fontSize: "11px",
                        padding: "3px 8px",
                        borderRadius: "10px",
                        backgroundColor: isDarkTheme ? "#3c3c3c" : "#e8e8e8",
                        color: isDarkTheme ? "#aaaaaa" : "#555555",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
