export function farmBoundary(f: any) {
  const raw = f?.boundary ?? f?.boundary_json;
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function toCanvas(boundary: any[], farm: any) {
  if (!boundary?.length) return [];
  const lons = boundary.map((x) => Number(x[0])),
    lats = boundary.map((x) => Number(x[1]));
  const minLon = Math.min(...lons),
    maxLon = Math.max(...lons),
    minLat = Math.min(...lats),
    maxLat = Math.max(...lats),
    dx = maxLon - minLon || 0.01,
    dy = maxLat - minLat || 0.01;
  return boundary.slice(0, -1).map(([lon, lat]: number[]) => ({
    x: 80 + ((lon - minLon) / dx) * 440,
    y: 320 - ((lat - minLat) / dy) * 260,
  }));
}

export function fromCanvas(points: { x: number; y: number }[], farm: any) {
  const lat = Number(farm?.lat || 7.291),
    lon = Number(farm?.lon || 81.674),
    scale = 0.012;
  const coords = points.map((p) => [lon + ((p.x - 300) / 440) * scale, lat - ((p.y - 190) / 260) * scale]);
  return [...coords, coords[0]];
}
