import { describe, it, expect } from 'vitest';
import { computeAnnualLoss } from './monte-carlo.js';

const validParams = {
  frequencyParams: { p50: 5, p95: 20, p99: 80 },
  costParams: { p50: 50000, p95: 500000, p99: 2000000 },
  frequencyDistType: 'lognormal',
  costDistType: 'lognormal',
};

describe('computeAnnualLoss', () => {
  describe('CDF monotonicity', () => {
    it('CDF values are non-decreasing and within [0, 1]', () => {
      const result = computeAnnualLoss(validParams);
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
      const result = computeAnnualLoss(validParams);
      expect(result).not.toBeNull();

      for (const y of result.yPdf) {
        expect(y).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('numerical stability and domain properties', () => {
    it('returns finite arrays with strictly increasing x values', () => {
      const result = computeAnnualLoss(validParams);
      expect(result).not.toBeNull();
      expect(result.x.length).toBe(500);
      expect(result.yPdf.length).toBe(result.x.length);
      expect(result.yCdf.length).toBe(result.x.length);

      for (let i = 0; i < result.x.length; i++) {
        expect(Number.isFinite(result.x[i])).toBe(true);
        expect(result.x[i]).toBeGreaterThan(0);
        expect(Number.isFinite(result.yPdf[i])).toBe(true);
        expect(Number.isFinite(result.yCdf[i])).toBe(true);
        if (i > 0) {
          expect(result.x[i]).toBeGreaterThan(result.x[i - 1]);
        }
      }

      expect(result.yCdf[0]).toBeGreaterThanOrEqual(0);
      expect(result.yCdf[result.yCdf.length - 1]).toBeLessThanOrEqual(1);
      expect(result.yCdf[result.yCdf.length - 1]).toBeGreaterThan(0.9);
    });

    it('handles extreme but valid mixed distributions without NaN/Infinity', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 0.01, p95: 2, p99: 20 },
        costParams: { p50: 1000, p95: 2_000_000, p99: 50_000_000 },
        frequencyDistType: 'pareto',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();

      for (let i = 0; i < result.x.length; i++) {
        expect(Number.isFinite(result.x[i])).toBe(true);
        expect(Number.isFinite(result.yPdf[i])).toBe(true);
        expect(Number.isFinite(result.yCdf[i])).toBe(true);
      }
    });
  });

  describe('P50/P95 fidelity (statistical)', () => {
    it('empirical CDF at theoretical median ≈ 0.50', () => {
      const Z_95 = 1.6449;
      const muFreq = Math.log(validParams.frequencyParams.p50);
      const sigmaFreq = (Math.log(validParams.frequencyParams.p95) - muFreq) / Z_95;
      const muCost = Math.log(validParams.costParams.p50);
      const sigmaCost = (Math.log(validParams.costParams.p95) - muCost) / Z_95;

      const muProduct = muFreq + muCost;
      const theoreticalMedian = Math.exp(muProduct);

      const result = computeAnnualLoss(validParams);
      expect(result).not.toBeNull();

      const cdfAtMedian = interpolateCdf(result.x, result.yCdf, theoreticalMedian);
      expect(cdfAtMedian).toBeGreaterThan(0.35);
      expect(cdfAtMedian).toBeLessThan(0.65);
    });
  });

  describe('determinism (seeded RNG)', () => {
    it('produces identical output for the same params', () => {
      const result1 = computeAnnualLoss(validParams);
      const result2 = computeAnnualLoss(validParams);

      expect(result1).not.toBeNull();
      expect(result2).not.toBeNull();

      expect(result1.x).toEqual(result2.x);
      expect(result1.yPdf).toEqual(result2.yPdf);
      expect(result1.yCdf).toEqual(result2.yCdf);
    });
  });

  describe('mixed distribution types', () => {
    it('lognormal frequency × pert cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 5, p95: 20, p99: 80 },
        costParams: { min: 1000, mode: 50000, max: 500000 },
        frequencyDistType: 'lognormal',
        costDistType: 'pert',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
      expect(result.yPdf.length).toBe(result.x.length);
      expect(result.yCdf.length).toBe(result.x.length);
    });

    it('pert frequency × lognormal cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { min: 0, mode: 5, max: 20 },
        costParams: { p50: 50000, p95: 500000, p99: 2000000 },
        frequencyDistType: 'pert',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
    });

    it('pareto frequency × lognormal cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 5, p95: 20, p99: 80 },
        costParams: { p50: 50000, p95: 500000, p99: 2000000 },
        frequencyDistType: 'pareto',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
    });

    it('pert frequency × pert cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { min: 0, mode: 5, max: 20 },
        costParams: { min: 1000, mode: 50000, max: 500000 },
        frequencyDistType: 'pert',
        costDistType: 'pert',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
    });
  });

  describe('invalid input handling', () => {
    it('returns null when frequencyParams is missing', () => {
      expect(computeAnnualLoss({ costParams: validParams.costParams })).toBeNull();
    });

    it('returns null when costParams is missing', () => {
      expect(computeAnnualLoss({ frequencyParams: validParams.frequencyParams })).toBeNull();
    });

    it('returns null when frequency p50 <= 0', () => {
      expect(computeAnnualLoss({
        frequencyParams: { p50: 0, p95: 10, p99: 50 },
        costParams: validParams.costParams,
      })).toBeNull();
    });

    it('returns null when frequency p95 <= p50', () => {
      expect(computeAnnualLoss({
        frequencyParams: { p50: 10, p95: 10, p99: 50 },
        costParams: validParams.costParams,
      })).toBeNull();
    });

    it('returns null when frequency p99 <= p95', () => {
      expect(computeAnnualLoss({
        frequencyParams: { p50: 5, p95: 20, p99: 20 },
        costParams: validParams.costParams,
      })).toBeNull();
    });

    it('returns null when cost p50 <= 0', () => {
      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: { p50: 0, p95: 500000, p99: 2000000 },
      })).toBeNull();
    });

    it('returns null when cost p95 < p50', () => {
      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: { p50: 500000, p95: 100, p99: 2000000 },
      })).toBeNull();
    });

    it('returns null when distribution type is unknown', () => {
      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: validParams.costParams,
        frequencyDistType: 'unknown',
        costDistType: 'lognormal',
      })).toBeNull();

      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: validParams.costParams,
        frequencyDistType: 'lognormal',
        costDistType: 'unknown',
      })).toBeNull();
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
  if (target <= x[0]) return yCdf[0];
  return yCdf[yCdf.length - 1];
}
