import { describe, it, expect } from 'vitest';
import { computeLognormal, fitLognormalOLS } from './lognormal.js';

describe('computeLognormal', () => {
  describe('P50/P95/P99 fidelity', () => {
    const cases = [
      { p50: 1, p95: 5, p99: 20, label: 'small' },
      { p50: 50, p95: 200, p99: 500, label: 'typical' },
      { p50: 10000, p95: 100000, p99: 500000, label: 'large' },
      { p50: 0.01, p95: 1, p99: 10, label: 'very small median' },
      { p50: 0.001, p95: 0.01, p99: 0.05, label: 'sub-thousandth median' },
      { p50: 1, p95: 100000, p99: 1000000, label: 'huge P95/P50 ratio' },
    ];

    for (const { p50, p95, p99, label } of cases) {
      it(`CDF ≈ 0.50 at p50 and ≈ 0.95 at p95 (${label}: p50=${p50}, p95=${p95})`, () => {
        const result = computeLognormal({ p50, p95, p99 });
        expect(result).not.toBeNull();

        const cdfAtP50 = interpolateCdf(result.x, result.yCdf, p50);
        const cdfAtP95 = interpolateCdf(result.x, result.yCdf, p95);

        expect(cdfAtP50).toBeCloseTo(0.5, 1);
        expect(cdfAtP95).toBeCloseTo(0.95, 1);
      });
    }
  });

  describe('P99 fidelity', () => {
    it('CDF ≈ 0.99 at p99', () => {
      const result = computeLognormal({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      const cdfAtP99 = interpolateCdf(result.x, result.yCdf, 500);
      expect(cdfAtP99).toBeCloseTo(0.99, 1);
    });
  });

  describe('CDF monotonicity', () => {
    it('CDF values are non-decreasing and within [0, 1]', () => {
      const result = computeLognormal({ p50: 50, p95: 200, p99: 500 });
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
      const result = computeLognormal({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      for (const y of result.yPdf) {
        expect(y).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('numerical stability', () => {
    it('returns finite, strictly increasing x values for extreme but valid quantiles', () => {
      const result = computeLognormal({ p50: 0.001, p95: 1000, p99: 1_000_000 });
      expect(result).not.toBeNull();
      expect(result.x.length).toBe(500);

      for (let i = 0; i < result.x.length; i++) {
        expect(Number.isFinite(result.x[i])).toBe(true);
        expect(Number.isFinite(result.yPdf[i])).toBe(true);
        expect(Number.isFinite(result.yCdf[i])).toBe(true);
        if (i > 0) {
          expect(result.x[i]).toBeGreaterThan(result.x[i - 1]);
        }
      }
    });
  });

  describe('CDF domain coverage for CI interpolation', () => {
    const edgeCases = [
      { p50: 0.01, p95: 1, p99: 10, label: 'very small median' },
      { p50: 0.001, p95: 0.01, p99: 0.05, label: 'sub-thousandth median' },
      { p50: 1, p95: 100000, p99: 1000000, label: 'huge ratio' },
    ];

    for (const { p50, p95, p99, label } of edgeCases) {
      it(`CDF spans below 0.025 and above 0.975 (${label})`, () => {
        const result = computeLognormal({ p50, p95, p99 });
        expect(result).not.toBeNull();

        expect(result.yCdf[0]).toBeLessThan(0.01);
        expect(result.yCdf[result.yCdf.length - 1]).toBeGreaterThan(0.99);
      });
    }
  });

  describe('invalid input handling', () => {
    it('returns null when p50 = 0', () => {
      expect(computeLognormal({ p50: 0, p95: 10, p99: 50 })).toBeNull();
    });

    it('returns null when p95 = p50', () => {
      expect(computeLognormal({ p50: 5, p95: 5, p99: 20 })).toBeNull();
    });

    it('returns null when p95 < p50', () => {
      expect(computeLognormal({ p50: 10, p95: 5, p99: 20 })).toBeNull();
    });

    it('returns null when p99 <= p95', () => {
      expect(computeLognormal({ p50: 5, p95: 20, p99: 20 })).toBeNull();
    });

    it('returns null when p99 < p95', () => {
      expect(computeLognormal({ p50: 5, p95: 20, p99: 10 })).toBeNull();
    });

    it('returns null for negative p50', () => {
      expect(computeLognormal({ p50: -1, p95: 10, p99: 50 })).toBeNull();
    });

    it('returns null for negative p95', () => {
      expect(computeLognormal({ p50: -5, p95: -1, p99: 10 })).toBeNull();
    });
  });
});

describe('fitLognormalOLS', () => {
  it('recovers mu and sigma from exact lognormal quantiles', () => {
    // Known parameters
    const mu = 3.0;
    const sigma = 1.5;

    // Compute exact quantiles
    const p50 = Math.exp(mu + sigma * 0);        // exp(mu)
    const p95 = Math.exp(mu + sigma * 1.6449);
    const p99 = Math.exp(mu + sigma * 2.3263);

    const result = fitLognormalOLS(p50, p95, p99);

    expect(result.mu).toBeCloseTo(mu, 6);
    expect(result.sigma).toBeCloseTo(sigma, 6);
  });

  it('recovers parameters for different mu/sigma combinations', () => {
    const cases = [
      { mu: 0, sigma: 0.5 },
      { mu: 10, sigma: 2 },
      { mu: -1, sigma: 0.1 },
    ];

    for (const { mu, sigma } of cases) {
      const p50 = Math.exp(mu);
      const p95 = Math.exp(mu + sigma * 1.6449);
      const p99 = Math.exp(mu + sigma * 2.3263);

      const result = fitLognormalOLS(p50, p95, p99);

      expect(result.mu).toBeCloseTo(mu, 4);
      expect(result.sigma).toBeCloseTo(sigma, 4);
    }
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
  if (target <= x[0]) return yCdf[0];
  return yCdf[yCdf.length - 1];
}
