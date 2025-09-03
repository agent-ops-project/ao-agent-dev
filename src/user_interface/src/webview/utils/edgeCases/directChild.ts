import { EdgeCase, EdgePath } from '../edgeTypes';
import { VisualLayer } from '../nodeLayout';
import { NODE_BORDER_WIDTH } from '../layoutConstants';

export class DirectChildEdgeCase implements EdgeCase {
  canHandle(parentLayer: number, childLayer: number): boolean {
    // Handle direct children: parent at layer N, child at layer N+1
    return childLayer === parentLayer + 1;
  }

  route(
    parentNode: { id: string; x: number; y: number },
    childNode: { id: string; x: number; y: number },
    visualLayers: VisualLayer[],
    nodeWidth: number,
    nodeHeight: number
  ): EdgePath {
    // Find the visual layer for the child
    const childVisualLayer = visualLayers.find(layer => 
      layer.nodes.includes(childNode.id)
    );

    if (!childVisualLayer) {
      // Fallback: simple straight line if no visual layer found
      return {
        id: `edge-${parentNode.id}-${childNode.id}`,
        type: 'direct-child',
        parentNodeId: parentNode.id,
        childNodeId: childNode.id,
        points: [
          { x: parentNode.x + nodeWidth / 2, y: parentNode.y + nodeHeight },
          { x: childNode.x + nodeWidth / 2, y: childNode.y }
        ]
      };
    }

    // Case 1: Direct child routing
    // 1. Start from parent bottom center
    const startX = parentNode.x + nodeWidth / 2;
    const startY = parentNode.y + nodeHeight;
    
    // 2. Go down to the horizontal connector line height
    const horizontalLineY = childVisualLayer.horizontalLineY;
    
    // 3. Go horizontally to the child's X position
    const childCenterX = childNode.x + nodeWidth / 2;
    
    // 4. Go down to the center of the horizontal connector line
    const endY = horizontalLineY;

    return {
      id: `edge-${parentNode.id}-${childNode.id}`,
      type: 'direct-child',
      parentNodeId: parentNode.id,
      childNodeId: childNode.id,
      points: [
        { x: startX, y: startY },
        { x: startX, y: horizontalLineY },
        { x: childCenterX, y: horizontalLineY },
        { x: childCenterX, y: endY }
      ]
    };
  }
}
