import { LayoutNode, BandInfo, RoutedEdge } from '../core/types';
import { createDirectPath } from '../paths/direct';
import { createBandPath, createBandPathWithHorizontalConnector } from '../paths/bands';
import { wouldDirectLineCrossNodes, hasNodesBetweenInVisualLayers } from './collisions';

export function calculateEdges(nodes: LayoutNode[], bands: BandInfo[], containerWidth: number, layerSpacing: number, nodeHeight: number, nodeSpacing: number): RoutedEdge[] {
  const edges: RoutedEdge[] = [];
  if (!nodes.length) return edges;
  const maxNodesPerRow = Math.max(1, Math.floor((containerWidth - nodeSpacing) / ( (nodes[0]?.width || 0) + nodeSpacing)));
  const isSingleColumn = maxNodesPerRow === 1;
  nodes.forEach(source => {
    source.children.forEach((childId, idx) => {
      const target = nodes.find(n => n.id === childId);
      if (!target || source.x == null || source.y == null || target.x == null || target.y == null) return;
      const edge: RoutedEdge = { id: `${source.id}-${childId}`, source: source.id, target: childId, type: 'direct', points: [], sourceHandle: 'bottom', targetHandle: 'top' };
      const isDirect = target.layer === source.layer! + 1;
      if (isDirect) {
        const hasNodesInBetween = hasNodesBetweenInVisualLayers(source, target, nodes, layerSpacing);
        const wouldCross = wouldDirectLineCrossNodes(source, target, nodes);
        let useBand = false;
        if (isSingleColumn) {
          const nodesBetween = nodes.filter(n => n.y! > source.y! + source.height! && n.y! + n.height! < target.y!);
          useBand = nodesBetween.length > 0 || idx > 0;
        } else {
          useBand = wouldCross || hasNodesInBetween;
        }
        if (useBand) {
          edge.type = 'band';
          edge.band = source.band;
          const band = bands.find(b => b.name === source.band);
          if (band) {
            const needsHorizontal = !isSingleColumn && source.children.length > 1 && (wouldCross || hasNodesInBetween);
            const childNodes = source.children.map(cid => nodes.find(n => n.id === cid)).filter(Boolean) as LayoutNode[];
            edge.points = needsHorizontal
              ? createBandPathWithHorizontalConnector(source, target, band.x, band.side, childNodes)
              : createBandPath(source, target, band.x, band.side);
            edge.sourceHandle = band.side === 'right' ? 'right-source' : 'left-source';
            edge.targetHandle = needsHorizontal ? 'top' : (band.side === 'right' ? 'left-target' : 'right-target');
          }
        } else {
          edge.points = createDirectPath(source, target, nodeHeight);
        }
      } else {
        edge.type = 'band';
        edge.band = source.band;
        const band = bands.find(b => b.name === source.band);
        if (band) {
          edge.points = createBandPath(source, target, band.x, band.side);
          edge.sourceHandle = band.side === 'right' ? 'right-source' : 'left-source';
          edge.targetHandle = band.side === 'right' ? 'left-target' : 'right-target';
        }
      }
      if (edge.points.length) edges.push(edge);
    });
  });
  return edges;
}
