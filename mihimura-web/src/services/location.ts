/** A coordinate the farmer or a saved farm actually provided. */
export function finiteCoord(value: unknown): number | null {
  const number =
    typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : Number.NaN;
  return Number.isFinite(number) ? number : null;
}

export function coordinatePair(lat: unknown, lon: unknown): { lat: number; lon: number } | null {
  const latitude = finiteCoord(lat);
  const longitude = finiteCoord(lon);
  if (latitude === null || longitude === null) return null;
  return { lat: latitude, lon: longitude };
}
