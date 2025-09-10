import { LayoutNode, LayerInfo, BandInfo } from '../core/types';
import { chooseBandSideForNode } from './bands';
import { wouldDirectLineCrossNodes, hasNodesBetweenInVisualLayers } from './collisions';

export interface BandCalcConfig {
  nodeWidth: number;
  nodeHeight: number;
  nodeSpacing: number;
  layerSpacing: number;
  bandSpacing: number;
  containerWidth: number;
}

// Pure function to compute band allocations and band axis positions.
export function calculateBands(
  nodes: LayoutNode[],
  layers: LayerInfo[],
  cfg: BandCalcConfig
): BandInfo[] {
  const { nodeWidth, nodeSpacing, layerSpacing, bandSpacing, containerWidth } = cfg;
  const bands: BandInfo[] = [];

  const maxNodesPerRow = Math.max(1, Math.floor((containerWidth - nodeSpacing) / (nodeWidth + nodeSpacing)));
  const isSingleColumn = maxNodesPerRow === 1;

  const needsBand = (node: LayoutNode): boolean => {
    const hasSkipLayer = node.children.some(cid => {
      const child = nodes.find(n => n.id === cid);
      return child && child.layer !== (node.layer! + 1);
    });
    let directCross = false;
    if (node.children.length) {
      directCross = node.children.some(cid => {
        const child = nodes.find(n => n.id === cid);
        if (!child || child.layer !== (node.layer! + 1)) return false;
        if (isSingleColumn) {
          const between = nodes.filter(n => n.y! > node.y! + node.height! && n.y! + n.height! < child.y!);
          return between.length > 0;
        }
        return wouldDirectLineCrossNodes(node, child, nodes) || hasNodesBetweenInVisualLayers(node, child, nodes, layerSpacing);
      });
    }
    if (isSingleColumn) return hasSkipLayer || directCross || node.children.length > 1;
    return hasSkipLayer || directCross; // wide screen
  };

  const nodesNeedingBands = nodes.filter(needsBand);

  let bandLevel = 1;
  let rightAssigned = false;
  nodesNeedingBands.forEach((node, index) => {
    const bestSide = chooseBandSideForNode(node, nodes, containerWidth);
    let preferLeft = bestSide === 'left';
    if (isSingleColumn) {
      const hasIntermediateSkip = node.children.some(cid => {
        const child = nodes.find(n => n.id === cid);
        if (!child || child.layer === node.layer! + 1) return false;
        const minL = Math.min(node.layer!, child.layer!);
        const maxL = Math.max(node.layer!, child.layer!);
        const intermediate = nodes.filter(n => n.layer! > minL && n.layer! < maxL);
        return intermediate.length > 0;
      });
      preferLeft = hasIntermediateSkip ? (nodesNeedingBands.length > 1 ? index % 2 === 0 : true) : preferLeft;
    }
    if (!rightAssigned && !preferLeft) {
      const name = `Band ${bandLevel} Right`;
      node.band = name; rightAssigned = true;
    } else {
      const name = `Band ${bandLevel} Left`;
      node.band = name; rightAssigned = false; bandLevel++;
    }
  });

  // Determine node area span
  const allNodes = layers.flatMap(l => l.nodes);
  let nodeAreaStart: number;
  let nodeAreaEnd: number;
  if (allNodes.length) {
    const xs = allNodes.map(n => n.x!);
    nodeAreaStart = Math.min(...xs);
    nodeAreaEnd = Math.max(...allNodes.map(n => n.x! + n.width!));
  } else {
    nodeAreaStart = 30; nodeAreaEnd = containerWidth - 30;
  }

  for (let level = 1; level <= bandLevel; level++) {
    bands.push({ name: `Band ${level} Right`, x: nodeAreaEnd + 15 + (level - 1) * bandSpacing, side: 'right', level });
    bands.push({ name: `Band ${level} Left`, x: nodeAreaStart - 15 - (level - 1) * bandSpacing, side: 'left', level });
  }
  return bands;
}
