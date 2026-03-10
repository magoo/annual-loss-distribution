import { describe, it, expect } from 'vitest';
import { fitParetoOLS, computePareto } from './pareto.js';
import { interpolateCdf } from './test-utils.js';

describe('fitParetoOLS', () => {
  it('recovers scale and shape from exact Pareto quantiles', () => {
    // Known Pareto parameters
    const scale = 10;
    const shape = 2;

    // Exact Pareto quantiles: Q(p) = scale * (1/(1-p))^(1/shape)
    const p50 = scale * Math.pow(1 / (1 - 0.5), 1 / shape);
    const p95 = scale * Math.pow(1 / (1 - 0.95), 1 / shape);
    const p99 = scale * Math.pow(1 / (1 - 0.99), 1 / shape);

    const result = fitParetoOLS(p50, p95, p99);

    expect(result.scale).toBeCloseTo(scale, 4);
    expect(result.shape).toBeCloseTo(shape, 4);
  });

  it('recovers parameters for different scale/shape combinations', () => {
    const cases = [
      { scale: 1, shape: 1 },
      { scale: 100, shape: 3 },
      { scale: 0.5, shape: 0.5 },
    ];

    for (const { scale, shape } of cases) {
      const p50 = scale * Math.pow(2, 1 / shape);
      const p95 = scale * Math.pow(20, 1 / shape);
      const p99 = scale * Math.pow(100, 1 / shape);

      const result = fitParetoOLS(p50, p95, p99);

      expect(result.scale).toBeCloseTo(scale, 3);
      expect(result.shape).toBeCloseTo(shape, 3);
    }
  });
});

describe('computePareto', () => {
  describe('CDF properties', () => {
    it('CDF is monotonically non-decreasing and within [0, 1]', () => {
      const result = computePareto({ p50: 50, p95: 200, p99: 500 });
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

  describe('PDF properties', () => {
    it('all PDF values are non-negative', () => {
      const result = computePareto({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      for (const y of result.yPdf) {
        expect(y).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('numerical stability', () => {
    it('returns finite arrays for extreme heavy-tail quantiles', () => {
      const result = computePareto({ p50: 1, p95: 10_000, p99: 1_000_000 });
      expect(result).not.toBeNull();
      expect(result.x.length).toBe(500);
      expect(result.yPdf.length).toBe(result.x.length);
      expect(result.yCdf.length).toBe(result.x.length);

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

  describe('CDF domain starts at scale', () => {
    it('first x value equals the fitted scale parameter', () => {
      const result = computePareto({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      const { scale } = fitParetoOLS(50, 200, 500);
      expect(result.x[0]).toBeCloseTo(scale, 5);
    });
  });

  describe('heavy tail', () => {
    it('P99 value is significantly larger than P50', () => {
      const result = computePareto({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      // The x range should extend well beyond p50
      const maxX = result.x[result.x.length - 1];
      expect(maxX).toBeGreaterThan(500);
    });
  });

  describe('P50/P95/P99 fidelity', () => {
    const cases = [
      { p50: 50, p95: 200, p99: 500, label: 'typical' },
      { p50: 1, p95: 100, p99: 10000, label: 'heavy tail' },
      { p50: 10000, p95: 50000, p99: 200000, label: 'large scale' },
    ];

    for (const { p50, p95, p99, label } of cases) {
      it(`CDF ≈ 0.50 at p50 and ≈ 0.95 at p95 (${label})`, () => {
        const result = computePareto({ p50, p95, p99 });
        expect(result).not.toBeNull();

        const cdfAtP50 = interpolateCdf(result.x, result.yCdf, p50);
        const cdfAtP95 = interpolateCdf(result.x, result.yCdf, p95);

        expect(cdfAtP50).toBeCloseTo(0.5, 1);
        expect(cdfAtP95).toBeCloseTo(0.95, 1);
      });
    }

    it('CDF ≈ 0.99 at p99', () => {
      const result = computePareto({ p50: 50, p95: 200, p99: 500 });
      expect(result).not.toBeNull();

      const cdfAtP99 = interpolateCdf(result.x, result.yCdf, 500);
      expect(cdfAtP99).toBeCloseTo(0.99, 1);
    });
  });

  describe('invalid inputs', () => {
    it('returns null when p50 <= 0', () => {
      expect(computePareto({ p50: 0, p95: 10, p99: 50 })).toBeNull();
      expect(computePareto({ p50: -1, p95: 10, p99: 50 })).toBeNull();
    });

    it('returns null when p95 <= p50', () => {
      expect(computePareto({ p50: 50, p95: 50, p99: 200 })).toBeNull();
      expect(computePareto({ p50: 50, p95: 30, p99: 200 })).toBeNull();
    });

    it('returns null when p99 <= p95', () => {
      expect(computePareto({ p50: 50, p95: 200, p99: 200 })).toBeNull();
      expect(computePareto({ p50: 50, p95: 200, p99: 100 })).toBeNull();
    });
  });
});
