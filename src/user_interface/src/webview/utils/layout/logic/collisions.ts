import { LayoutNode, LayerInfo } from '../core/types';

export function wouldDirectLineCrossNodes(source: LayoutNode, target: LayoutNode, allNodes: LayoutNode[]): boolean {
  const sourceX = source.x! + source.width! / 2;
  const sourceY = source.y! + source.height!;
  const targetX = target.x! + target.width! / 2;
  const targetY = target.y!;
  return allNodes.some(node => {
    if (node.id === source.id || node.id === target.id) return false;
    if (node.y! <= sourceY || node.y! + node.height! >= targetY) return false;
    const nodeLeft = node.x!, nodeRight = node.x! + node.width!, nodeTop = node.y!, nodeBottom = node.y! + node.height!;
    const lineXAtNodeTop = sourceX + (targetX - sourceX) * (nodeTop - sourceY) / (targetY - sourceY);
    const lineXAtNodeBottom = sourceX + (targetX - sourceX) * (nodeBottom - sourceY) / (targetY - sourceY);
    const lineMinX = Math.min(lineXAtNodeTop, lineXAtNodeBottom);
    const lineMaxX = Math.max(lineXAtNodeTop, lineXAtNodeBottom);
    return !(lineMaxX < nodeLeft || lineMinX > nodeRight);
  });
}

export function hasNodesBetweenInVisualLayers(source: LayoutNode, target: LayoutNode, allNodes: LayoutNode[], layerSpacing: number): boolean {
  const sourceBottom = source.y! + source.height!;
  const targetTop = target.y!;
  const expectedSpacing = layerSpacing;
  const actualSpacing = targetTop - sourceBottom;
  if (actualSpacing > expectedSpacing * 1.5) return true;
  return allNodes.some(node => {
    if (node.id === source.id || node.id === target.id) return false;
    return node.y! > sourceBottom && node.y! + node.height! < targetTop;
  });
}

export function applyCenterBandCascade(layers: LayerInfo[], containerWidth: number, nodeWidth: number, nodeHeight: number, nodeSpacing: number): void {
  const rowStep = nodeHeight + 20;
  layers.forEach((layer, idx) => {
    if (!layer.nodes || layer.nodes.length < 3) return;
    if (!layer.visualLayers || layer.visualLayers.length !== 1) return;
    const sorted = [...layer.nodes].filter(n => typeof n.x === 'number').sort((a,b)=> (a.x! - b.x!));
    if (sorted.length !== layer.nodes.length) return;
    const candidates = sorted.slice(1, -1).filter(node => node.children.some(cid => {
      const child = layers.flatMap(l => l.nodes).find(n => n.id === cid);
      return child && typeof child.layer === 'number' && child.layer! > node.layer! + 1;
    }));
    if (candidates.length === 0) return;
    const originalTopY = sorted[0].y!;
    const firstRowNodes = sorted.filter(n => !candidates.includes(n));
    const secondRowNodes = candidates;
    const firstTotalWidth = firstRowNodes.length * nodeWidth + (firstRowNodes.length - 1) * nodeSpacing;
    const firstXOffset = Math.max(nodeSpacing, (containerWidth - firstTotalWidth) / 2);
    firstRowNodes.forEach((n,i)=> { n.x = firstXOffset + i * (nodeWidth + nodeSpacing); n.visualLayer = 0; n.y = originalTopY; });
    const secondTotalWidth = secondRowNodes.length * nodeWidth + (secondRowNodes.length - 1) * nodeSpacing;
    const secondXOffset = Math.max(nodeSpacing, (containerWidth - secondTotalWidth) / 2);
    secondRowNodes.forEach((n,i)=> { n.x = secondXOffset + i * (nodeWidth + nodeSpacing); n.visualLayer = 1; n.y = originalTopY + rowStep; });
    layer.visualLayers = [firstRowNodes.map(n=>n.id), secondRowNodes.map(n=>n.id)];
    for (let j = idx + 1; j < layers.length; j++) {
      layers[j].nodes.forEach(n => { if (typeof n.y === 'number') n.y += rowStep; if (typeof n.visualLayer === 'number') n.visualLayer = (n.visualLayer ?? 0) + 1; });
    }
  });
}
