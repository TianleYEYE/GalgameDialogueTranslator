export function finiteNumberOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function buildOverlayGeometry({ game, crop, fontSize, savedBounds = {} }) {
  const gameWidth = Math.max(Number(game?.width) || 960, 320);
  const gameHeight = Math.max(Number(game?.height) || 540, 180);
  const gameX = Number(game?.x) || 0;
  const gameY = Number(game?.y) || 0;
  const defaultHeight = Math.max((Number.parseInt(fontSize, 10) || 20) * 4, 96);
  const defaultWidth = Math.max(gameWidth * Math.max(crop.right - crop.left, 0.25), 320);
  const width = Math.max(finiteNumberOrNull(savedBounds.width) || defaultWidth, 280);
  const height = Math.max(finiteNumberOrNull(savedBounds.height) || defaultHeight, 80);
  const maxTop = Math.max(gameHeight - height - 8, 8);
  const defaultTop = Math.min(Math.max(gameHeight * crop.top - height - 8, 8), maxTop);

  return {
    x: finiteNumberOrNull(savedBounds.x) ?? gameX + gameWidth * crop.left,
    y: finiteNumberOrNull(savedBounds.y) ?? gameY + defaultTop,
    width,
    height
  };
}

export function normalizeOverlayBounds(bounds) {
  return {
    x: finiteNumberOrNull(bounds?.x),
    y: finiteNumberOrNull(bounds?.y),
    width: finiteNumberOrNull(bounds?.width),
    height: finiteNumberOrNull(bounds?.height)
  };
}
