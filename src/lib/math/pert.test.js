import { describe, it, expect } from 'vitest';
import { fitPert, computePert } from './pert.js';

describe('fitPert', () => {
  it('symmetric case: min=0, mode=5, max=10 gives alpha ≈ beta ≈ 3', () => {
    const { alpha, beta } = fitPert(0, 5, 10);
    // alpha = 1 + 4*(5-0)/(10-0) = 1 + 2 = 3
    // beta  = 1 + 4*(10-5)/(10-0) = 1 + 2 = 3
    expect(alpha).toBeCloseTo(3, 10);
    expect(beta).toBeCloseTo(3, 10);
  });

  it('left-skewed: mode closer to min', () => {
    const { alpha, beta } = fitPert(0, 2, 10);
    // alpha = 1 + 4*(2/10) = 1.8
    // beta  = 1 + 4*(8/10) = 4.2
    expect(alpha).toBeCloseTo(1.8, 10);
    expect(beta).toBeCloseTo(4.2, 10);
  });

  it('right-skewed: mode closer to max', () => {
    const { alpha, beta } = fitPert(0, 8, 10);
    // alpha = 1 + 4*(8/10) = 4.2
    // beta  = 1 + 4*(2/10) = 1.8
    expect(alpha).toBeCloseTo(4.2, 10);
    expect(beta).toBeCloseTo(1.8, 10);
  });

  it('returns min and max unchanged', () => {
    const result = fitPert(100, 500, 1000);
    expect(result.min).toBe(100);
    expect(result.max).toBe(1000);
  });
});

describe('computePert', () => {
  describe('CDF properties', () => {
    it('CDF is monotonically non-decreasing and within [0, 1]', () => {
      const result = computePert({ min: 0, mode: 5, max: 10 });
      expect(result).not.toBeNull();

      for (let i = 0; i < result.yCdf.length; i++) {
        expect(result.yCdf[i]).toBeGreaterThanOrEqual(0);
        expect(result.yCdf[i]).toBeLessThanOrEqual(1);
      }

      for (let i = 0; i < result.yCdf.length - 1; i++) {
        expect(result.yCdf[i + 1]).toBeGreaterThanOrEqual(result.yCdf[i]);
      }
    });

    it('CDF ≈ 0 at min and CDF ≈ 1 at max', () => {
      const result = computePert({ min: 0, mode: 5, max: 10 });
      expect(result).not.toBeNull();

      expect(result.yCdf[0]).toBeLessThan(0.01);
      expect(result.yCdf[result.yCdf.length - 1]).toBeGreaterThan(0.99);
    });
  });

  describe('PDF properties', () => {
    it('all PDF values are non-negative', () => {
      const result = computePert({ min: 0, mode: 5, max: 10 });
      expect(result).not.toBeNull();

      for (const y of result.yPdf) {
        expect(y).toBeGreaterThanOrEqual(0);
      }
    });

    it('mode is near the PDF peak', () => {
      const mode = 5;
      const result = computePert({ min: 0, mode, max: 10 });
      expect(result).not.toBeNull();

      // Find x at peak PDF
      let maxPdf = 0;
      let xAtPeak = 0;
      for (let i = 0; i < result.yPdf.length; i++) {
        if (result.yPdf[i] > maxPdf) {
          maxPdf = result.yPdf[i];
          xAtPeak = result.x[i];
        }
      }

      // Peak should be near the mode
      expect(xAtPeak).toBeCloseTo(mode, 0);
    });
  });

  describe('domain coverage', () => {
    it('x ranges from min to max', () => {
      const result = computePert({ min: 100, mode: 500, max: 1000 });
      expect(result).not.toBeNull();

      expect(result.x[0]).toBeCloseTo(100, 5);
      expect(result.x[result.x.length - 1]).toBeCloseTo(1000, 5);
    });
  });

  describe('numerical stability', () => {
    it('returns finite arrays for wide but valid ranges', () => {
      const result = computePert({ min: 0, mode: 1, max: 1_000_000 });
      expect(result).not.toBeNull();
      expect(result.x.length).toBe(500);
      expect(result.yPdf.length).toBe(result.x.length);
      expect(result.yCdf.length).toBe(result.x.length);

      for (let i = 0; i < result.x.length; i++) {
        expect(Number.isFinite(result.x[i])).toBe(true);
        expect(Number.isFinite(result.yPdf[i])).toBe(true);
        expect(Number.isFinite(result.yCdf[i])).toBe(true);
      }
    });
  });

  describe('invalid inputs', () => {
    it('returns null when min >= mode', () => {
      expect(computePert({ min: 5, mode: 5, max: 10 })).toBeNull();
      expect(computePert({ min: 6, mode: 5, max: 10 })).toBeNull();
    });

    it('returns null when mode >= max', () => {
      expect(computePert({ min: 0, mode: 10, max: 10 })).toBeNull();
      expect(computePert({ min: 0, mode: 11, max: 10 })).toBeNull();
    });

    it('returns null when min < 0', () => {
      expect(computePert({ min: -1, mode: 5, max: 10 })).toBeNull();
    });
  });
});
