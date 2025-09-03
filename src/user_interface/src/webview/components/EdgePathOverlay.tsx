import React from 'react';
import { EdgePath } from '../utils/edgeTypes';

interface EdgePathOverlayProps {
  edgePaths: EdgePath[];
}

export const EdgePathOverlay: React.FC<EdgePathOverlayProps> = ({ edgePaths }) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 2, // Above visual layer overlay
      }}
    >
      <svg
        style={{
          width: '100%',
          height: '100%',
          overflow: 'visible',
        }}
      >
        <defs>
          {/* Arrow marker for edge paths */}
          <marker
            id="edge-arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="5"
            refY="5"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <polyline
              points="0,0 5,5 0,10"
              fill="none"
              stroke="#666"
              strokeWidth="1"
              strokeLinecap="round"
            />
          </marker>
        </defs>
        
        {/* Render each edge path */}
        {edgePaths.map((edgePath) => {
          const pathData = edgePath.points.reduce((acc, point, index) => {
            if (index === 0) {
              return `M ${point.x},${point.y}`;
            } else {
              return `${acc} L ${point.x},${point.y}`;
            }
          }, '');

          return (
            <path
              key={edgePath.id}
              d={pathData}
              stroke="#666"
              strokeWidth="2"
              fill="none"
              markerEnd="url(#edge-arrowhead)"
            />
          );
        })}
      </svg>
    </div>
  );
};
