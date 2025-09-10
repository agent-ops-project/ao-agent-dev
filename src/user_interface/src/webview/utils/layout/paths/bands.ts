import { LayoutNode, Point } from '../core/types';

// Band path using explicit band X coordinate (mirrors original internal implementation)
export function createBandPath(source: LayoutNode, target: LayoutNode, bandX: number, side: 'left' | 'right'): Point[] {
  if (source.x == null || source.y == null || target.x == null || target.y == null) return [];
  const sourceX = source.x + (side === 'right' ? source.width! : 0);
  const sourceY = source.y + source.height! / 2;
  const arrowOffset = 5;
  const targetX = target.x + (side === 'right' ? target.width! - arrowOffset : arrowOffset);
  const targetY = target.y + target.height! / 2;
  return [
    { x: sourceX, y: sourceY },
    { x: bandX, y: sourceY },
    { x: bandX, y: targetY },
    { x: targetX, y: targetY }
  ];
}

export function createBandPathWithHorizontalConnector(source: LayoutNode, target: LayoutNode, bandX: number, side: 'left' | 'right', children: LayoutNode[]): Point[] {
  if (source.x == null || source.y == null || target.x == null || target.y == null) return [];
  const sourceX = source.x + (side === 'right' ? source.width! : 0);
  const sourceY = source.y + source.height! / 2;
  if (!children.length) return createBandPath(source, target, bandX, side);
  const minChildY = Math.min(...children.filter(c => c && c.y != null).map(c => c.y!));
  const connectorY = (isFinite(minChildY) ? minChildY : sourceY) - 20;
  const targetCenterX = target.x + target.width! / 2;
  const targetY = target.y;
  return [
    { x: sourceX, y: sourceY },
    { x: bandX, y: sourceY },
    { x: bandX, y: connectorY },
    { x: targetCenterX, y: connectorY },
    { x: targetCenterX, y: targetY }
  ];
}
