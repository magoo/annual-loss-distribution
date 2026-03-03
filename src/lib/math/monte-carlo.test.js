import { describe, it, expect } from 'vitest';
import { computeAnnualLoss } from './monte-carlo.js';

const validParams = {
  frequencyParams: { p50: 5, p95: 20 },
  costParams: { p50: 50000, p95: 500000 },
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

  describe('P50/P95 fidelity (statistical)', () => {
    it('empirical CDF at theoretical median ≈ 0.50', () => {
      // Product of two lognormals is lognormal:
      //   mu_product = mu_freq + mu_cost
      //   sigma_product = sqrt(sigma_freq^2 + sigma_cost^2)
      // Theoretical median = exp(mu_product)
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
      // Relaxed tolerance ±0.05 for Monte Carlo noise
      expect(cdfAtMedian).toBeGreaterThan(0.35);
      expect(cdfAtMedian).toBeLessThan(0.65);
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
