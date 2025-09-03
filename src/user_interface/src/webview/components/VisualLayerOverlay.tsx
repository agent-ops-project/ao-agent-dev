import React from 'react';
import { VisualLayer } from '../utils/nodeLayout';
import { NODE_WIDTH } from '../utils/nodeLayout';
import { NODE_BORDER_WIDTH } from '../utils/layoutConstants';

interface VisualLayerOverlayProps {
  visualLayers: VisualLayer[];
  nodePositions: Map<string, { x: number; y: number }>;
}

export const VisualLayerOverlay: React.FC<VisualLayerOverlayProps> = ({ 
  visualLayers, 
  nodePositions 
}) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1,
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
          {/* Create unique marker definitions for each vertical connection */}
          {visualLayers.map((layer) =>
            layer.nodes.map((nodeId) => (
              <marker
                key={`chevron-arrowhead-${layer.level}-${layer.rowIndex}-${nodeId}`}
                id={`chevron-arrowhead-${layer.level}-${layer.rowIndex}-${nodeId}`}
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
                  stroke="#e0e0e0"
                  strokeWidth="1"
                  strokeLinecap="round"
                />
              </marker>
            ))
          )}
        </defs>
        
        {/* Render horizontal lines and vertical connections */}
        {visualLayers.map((layer) => {
          const verticalConnections = layer.nodes.map((nodeId) => {
            const nodePosition = nodePositions.get(nodeId);
            if (!nodePosition) return null;
            
            return {
              nodeId,
              x: nodePosition.x + NODE_WIDTH / 2,
              startY: layer.horizontalLineY,
              endY: nodePosition.y - NODE_BORDER_WIDTH
            };
          }).filter(conn => conn !== null) as Array<{
            nodeId: string;
            x: number;
            startY: number;
            endY: number;
          }>;
          
          return (
            <g key={`visual-layer-${layer.level}-${layer.rowIndex}`}>
              {/* Horizontal line */}
              <line
                x1={layer.leftmostX + NODE_WIDTH / 2}
                y1={layer.horizontalLineY}
                x2={layer.rightmostX + NODE_WIDTH / 2}
                y2={layer.horizontalLineY}
                stroke="#e0e0e0"
                strokeWidth="1"
                opacity={0.6}
              />
              
              {/* Vertical connections with arrows */}
              {verticalConnections.map((connection) => (
                <line
                  key={`arrow-${layer.level}-${layer.rowIndex}-${connection.nodeId}`}
                  x1={connection.x}
                  y1={connection.startY}
                  x2={connection.x}
                  y2={connection.endY}
                  stroke="#e0e0e0"
                  strokeWidth="2"
                  opacity={0.6}
                  markerEnd={`url(#chevron-arrowhead-${layer.level}-${layer.rowIndex}-${connection.nodeId})`}
                />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
