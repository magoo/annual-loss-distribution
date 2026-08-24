import { describe, it, expect } from 'vitest';
import { computeAnnualLoss } from './monte-carlo.js';

const validParams = {
  frequencyParams: { p50: 5, p95: 20 },
  costParams: { p50: 50000, p95: 500000 },
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

  describe('empirical output', () => {
    it('returns a histogram contract with non-negative samples', () => {
      const result = computeAnnualLoss(validParams);
      expect(result).not.toBeNull();
      expect(result.isHistogram).toBe(true);
      expect(result.samples).toHaveLength(100_000);
      expect(result.samples.every((sample) => Number.isFinite(sample) && sample >= 0)).toBe(true);
    });
  });

  describe('numerical stability and domain properties', () => {
    it('returns finite arrays with strictly increasing x values', () => {
      const result = computeAnnualLoss(validParams);
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(1);
      expect(result.yCdf.length).toBe(result.x.length);

      for (let i = 0; i < result.x.length; i++) {
        expect(Number.isFinite(result.x[i])).toBe(true);
        expect(result.x[i]).toBeGreaterThanOrEqual(0);
        expect(Number.isFinite(result.yCdf[i])).toBe(true);
        if (i > 0) {
          expect(result.x[i]).toBeGreaterThan(result.x[i - 1]);
        }
      }

      expect(result.yCdf[0]).toBeGreaterThanOrEqual(0);
      expect(result.yCdf[result.yCdf.length - 1]).toBe(1);
      expect(result.x[result.x.length - 1]).toBe(result.samples[result.samples.length - 1]);
    });

    it('rejects computationally explosive frequency tails without entering event loops', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 1, p95: 1e12 },
        costParams: { p50: 1000, p95: 10_000 },
        frequencyDistType: 'pareto',
        costDistType: 'lognormal',
      });
      expect(result).toBeNull();
    });
  });

  describe('compound annual-loss behavior', () => {
    it('sums independent per-incident costs rather than multiplying one cost by frequency', () => {
      const result = computeAnnualLoss({
        frequencyParams: { min: 1.49, mode: 1.5, max: 1.51 },
        costParams: { min: 100, mode: 100.5, max: 101 },
        frequencyDistType: 'pert',
        costDistType: 'pert',
      });
      expect(result).not.toBeNull();
      expect(result.samples.some((loss) => loss >= 100 && loss <= 101)).toBe(true);
      expect(result.samples.some((loss) => loss >= 200 && loss <= 202)).toBe(true);
    });

    it('preserves zero-loss years as an explicit CDF point mass', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 0.25, p95: 1 },
        costParams: { p50: 1000, p95: 10_000 },
        frequencyDistType: 'lognormal',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();
      expect(result.x[0]).toBe(0);
      expect(result.yCdf[0]).toBeGreaterThan(0);
      expect(result.samples.some((loss) => loss === 0)).toBe(true);
    });

    it('supports the default infinite-mean Pareto frequency without unbounded work', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 1, p95: 10 },
        costParams: { p50: 50_000, p95: 500_000 },
        frequencyDistType: 'pareto',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();
      expect(result.numRounds).toBeGreaterThanOrEqual(1000);
      expect(result.numRounds).toBeLessThanOrEqual(100_000);
    });
  });

  describe('determinism (seeded RNG)', () => {
    it('produces identical output for the same params', () => {
      const result1 = computeAnnualLoss(validParams);
      const result2 = computeAnnualLoss(validParams);

      expect(result1).not.toBeNull();
      expect(result2).not.toBeNull();

      expect(result1.x).toEqual(result2.x);
      expect(result1.yCdf).toEqual(result2.yCdf);
      expect(result1.samples).toEqual(result2.samples);
    });
  });

  describe('mixed distribution types', () => {
    it('lognormal frequency × pert cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 5, p95: 20 },
        costParams: { min: 1000, mode: 50000, max: 500000 },
        frequencyDistType: 'lognormal',
        costDistType: 'pert',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
      expect(result.yCdf.length).toBe(result.x.length);
    });

    it('pert frequency × lognormal cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { min: 0, mode: 5, max: 20 },
        costParams: { p50: 50000, p95: 500000 },
        frequencyDistType: 'pert',
        costDistType: 'lognormal',
      });
      expect(result).not.toBeNull();
      expect(result.x.length).toBeGreaterThan(0);
    });

    it('pareto frequency × lognormal cost', () => {
      const result = computeAnnualLoss({
        frequencyParams: { p50: 5, p95: 20 },
        costParams: { p50: 50000, p95: 500000 },
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
        frequencyParams: { p50: 0, p95: 10 },
        costParams: validParams.costParams,
      })).toBeNull();
    });

    it('returns null when frequency p95 <= p50', () => {
      expect(computeAnnualLoss({
        frequencyParams: { p50: 10, p95: 10 },
        costParams: validParams.costParams,
      })).toBeNull();
    });

    it('returns null when cost p50 <= 0', () => {
      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: { p50: 0, p95: 500000 },
      })).toBeNull();
    });

    it('returns null when cost p95 < p50', () => {
      expect(computeAnnualLoss({
        frequencyParams: validParams.frequencyParams,
        costParams: { p50: 500000, p95: 100 },
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
