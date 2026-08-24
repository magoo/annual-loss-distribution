import { describe, expect, it } from 'vitest';
import { empiricalCdfArrays } from './empirical.js';

describe('empiricalCdfArrays', () => {
  it('preserves zero probability and the full simulated maximum', () => {
    const sorted = Float64Array.from([0, 0, 10, 20, 100]);
    const result = empiricalCdfArrays(sorted, 20);

    expect(result.x[0]).toBe(0);
    expect(result.yCdf[0]).toBe(0.4);
    expect(result.x[result.x.length - 1]).toBe(100);
    expect(result.yCdf[result.yCdf.length - 1]).toBe(1);
  });

  it('returns a monotone CDF for positive heavy-tailed samples', () => {
    const sorted = Float64Array.from([1, 2, 3, 10, 100, 10_000]);
    const result = empiricalCdfArrays(sorted, 10);

    expect(result.x[result.x.length - 1]).toBe(10_000);
    for (let i = 1; i < result.yCdf.length; i++) {
      expect(result.yCdf[i]).toBeGreaterThanOrEqual(result.yCdf[i - 1]);
    }
  });
});
