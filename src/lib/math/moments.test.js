import { describe, expect, it } from 'vitest';
import { distributionMean, frequencyWorkRate } from './moments.js';

describe('distribution moments and planning rates', () => {
  it('returns finite means for lognormal and PERT models', () => {
    expect(distributionMean('lognormal', { p50: 1, p95: 10 })).toBeGreaterThan(1);
    expect(distributionMean('pert', { min: 0, mode: 1, max: 10 })).toBeCloseTo(14 / 6, 12);
  });

  it('uses P95 to plan work for an infinite-mean Pareto frequency', () => {
    const params = { p50: 1, p95: 10 };
    expect(distributionMean('pareto', params)).toBe(Infinity);
    expect(frequencyWorkRate('pareto', params)).toBe(10);
  });
});
