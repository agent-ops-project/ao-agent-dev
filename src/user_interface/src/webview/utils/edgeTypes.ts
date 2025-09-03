import { Point } from '../types';
import { VisualLayer } from './nodeLayout';

export interface EdgePath {
  id: string;
  type: 'direct-child' | 'multi-layer' | 'same-layer';
  points: Point[];
  parentNodeId: string;
  childNodeId: string;
}

export interface EdgeCase {
  canHandle(parentLayer: number, childLayer: number): boolean;
  route(
    parentNode: { id: string; x: number; y: number },
    childNode: { id: string; x: number; y: number },
    visualLayers: VisualLayer[],
    nodeWidth: number,
    nodeHeight: number
  ): EdgePath;
}

export interface EdgeRoutingResult {
  edgePaths: EdgePath[];
  visualLayerEdges: VisualLayerEdge[];
}

export interface VisualLayerEdge {
  id: string;
  type: 'visual-layer';
  level: number;
  rowIndex: number;
  nodeIds: string[];
  horizontalLine: {
    x1: number;
    x2: number;
    y: number;
  };
  verticalConnections: Array<{
    nodeId: string;
    x: number;
    startY: number;
    endY: number;
  }>;
}
