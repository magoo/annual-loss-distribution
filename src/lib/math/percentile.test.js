import { describe, it, expect } from 'vitest';
import { interpolatePercentile } from './percentile.js';

describe('interpolatePercentile', () => {
  it('returns 0 for missing or empty arrays', () => {
    expect(interpolatePercentile([], [], 0.5)).toBe(0);
    expect(interpolatePercentile(null, null, 0.5)).toBe(0);
  });

  it('clamps to the first x value when p is below the first CDF value', () => {
    const x = [10, 20, 30];
    const yCdf = [0.2, 0.6, 1.0];

    expect(interpolatePercentile(x, yCdf, 0.1)).toBe(10);
    expect(interpolatePercentile(x, yCdf, 0.2)).toBe(10);
  });

  it('clamps to the last x value when p is above the last CDF value', () => {
    const x = [10, 20, 30];
    const yCdf = [0.2, 0.6, 0.9];

    expect(interpolatePercentile(x, yCdf, 0.95)).toBe(30);
    expect(interpolatePercentile(x, yCdf, 1.0)).toBe(30);
  });

  it('returns an exact x value when p matches a CDF knot', () => {
    const x = [5, 15, 25];
    const yCdf = [0, 0.5, 1];

    expect(interpolatePercentile(x, yCdf, 0.5)).toBeCloseTo(15, 12);
  });

  it('linearly interpolates between adjacent CDF knots', () => {
    const x = [0, 10, 20];
    const yCdf = [0, 0.5, 1];

    expect(interpolatePercentile(x, yCdf, 0.25)).toBeCloseTo(5, 12);
    expect(interpolatePercentile(x, yCdf, 0.75)).toBeCloseTo(15, 12);
  });
});
