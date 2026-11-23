import { describe, expect, it } from 'vitest';
import { coordinatePair, finiteCoord } from './location';

describe('saved coordinates', () => {
  it('accepts numbers and numeric strings', () => {
    expect(finiteCoord('7.29')).toBe(7.29);
    expect(coordinatePair('6.05', 80.2)).toEqual({ lat: 6.05, lon: 80.2 });
  });

  it('does not invent a district coordinate', () => {
    expect(finiteCoord('')).toBeNull();
    expect(finiteCoord(undefined)).toBeNull();
    expect(coordinatePair(undefined, 80)).toBeNull();
  });
});