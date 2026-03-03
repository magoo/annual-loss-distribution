import { describe, it, expect } from 'vitest';
import { computeLognormal } from './lognormal.js';

describe('computeLognormal', () => {
  describe('P50/P95 fidelity', () => {
    const cases = [
      { p50: 1, p95: 5, label: 'small' },
      { p50: 50, p95: 200, label: 'typical' },
      { p50: 10000, p95: 100000, label: 'large' },
      { p50: 0.01, p95: 1, label: 'very small median' },
      { p50: 0.001, p95: 0.01, label: 'sub-thousandth median' },
      { p50: 1, p95: 100000, label: 'huge P95/P50 ratio' },
    ];

    for (const { p50, p95, label } of cases) {
      it(`CDF ≈ 0.50 at p50 and ≈ 0.95 at p95 (${label}: p50=${p50}, p95=${p95})`, () => {
        const result = computeLognormal({ p50, p95 });
        expect(result).not.toBeNull();

        const cdfAtP50 = interpolateCdf(result.x, result.yCdf, p50);
        const cdfAtP95 = interpolateCdf(result.x, result.yCdf, p95);

        expect(cdfAtP50).toBeCloseTo(0.5, 1);  // ±0.05
        expect(cdfAtP95).toBeCloseTo(0.95, 1);  // ±0.05
      });
    }
  });

  describe('CDF monotonicity', () => {
    it('CDF values are non-decreasing and within [0, 1]', () => {
      const result = computeLognormal({ p50: 50, p95: 200 });
      expect(result).not.toBeNull();

      for (let i = 0; i < result.yCdf.length; i++) {
        expect(result.yCdf[i]).toBeGreaterThanOrEqual(0);
        expect(result.yCdf[i]).toBeLessThanOrEqual(1);
      }

      for (let i = 0; i < result.yCdf.length - 1; i++) {
        expect(result.yCdf[i + 1]).toBeGreaterThanOrEqual(result.yCdf[i]);
      }
    });
  });

  describe('PDF non-negativity', () => {
    it('all PDF values are >= 0', () => {
      const result = computeLognormal({ p50: 50, p95: 200 });
      expect(result).not.toBeNull();

      for (const y of result.yPdf) {
        expect(y).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('CDF domain coverage for CI interpolation', () => {
    const edgeCases = [
      { p50: 0.01, p95: 1, label: 'very small median' },
      { p50: 0.001, p95: 0.01, label: 'sub-thousandth median' },
      { p50: 1, p95: 100000, label: 'huge ratio' },
    ];

    for (const { p50, p95, label } of edgeCases) {
      it(`CDF spans below 0.025 and above 0.975 (${label})`, () => {
        const result = computeLognormal({ p50, p95 });
        expect(result).not.toBeNull();

        // CDF must start low enough for CI lower bounds (slider min 50% → lowerP=0.25)
        expect(result.yCdf[0]).toBeLessThan(0.01);
        // CDF must end high enough for CI upper bounds (slider max 95% → upperP=0.975)
        expect(result.yCdf[result.yCdf.length - 1]).toBeGreaterThan(0.99);
      });
    }
  });

  describe('invalid input handling', () => {
    it('returns null when p50 = 0', () => {
      expect(computeLognormal({ p50: 0, p95: 10 })).toBeNull();
    });

    it('returns null when p95 = p50', () => {
      expect(computeLognormal({ p50: 5, p95: 5 })).toBeNull();
    });

    it('returns null when p95 < p50', () => {
      expect(computeLognormal({ p50: 10, p95: 5 })).toBeNull();
    });

    it('returns null for negative p50', () => {
      expect(computeLognormal({ p50: -1, p95: 10 })).toBeNull();
    });

    it('returns null for negative p95', () => {
      expect(computeLognormal({ p50: -5, p95: -1 })).toBeNull();
    });
  });
});

/**
 * Linear interpolation to find CDF value at a target x.
 */
function interpolateCdf(x, yCdf, target) {
  for (let i = 0; i < x.length - 1; i++) {
    if (x[i] <= target && target <= x[i + 1]) {
      const t = (target - x[i]) / (x[i + 1] - x[i]);
      return yCdf[i] + t * (yCdf[i + 1] - yCdf[i]);
    }
  }
  // If target is beyond range, return nearest boundary
  if (target <= x[0]) return yCdf[0];
  return yCdf[yCdf.length - 1];
}
