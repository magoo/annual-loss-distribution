import { describe, it, expect } from 'vitest';
import { validateQuantiles, validatePert, validate } from './validation.js';

describe('validateQuantiles', () => {
  it('returns empty errors for valid params', () => {
    const errors = validateQuantiles({ p50: 10, p95: 100, p99: 500 });
    expect(errors).toEqual({});
  });

  describe('required fields', () => {
    it('missing p50 returns Required', () => {
      const errors = validateQuantiles({ p95: 100, p99: 500 });
      expect(errors.p50).toBe('Required');
    });

    it('NaN p50 returns Required', () => {
      const errors = validateQuantiles({ p50: NaN, p95: 100, p99: 500 });
      expect(errors.p50).toBe('Required');
    });

    it('missing p95 returns Required', () => {
      const errors = validateQuantiles({ p50: 10, p99: 500 });
      expect(errors.p95).toBe('Required');
    });

    it('NaN p95 returns Required', () => {
      const errors = validateQuantiles({ p50: 10, p95: NaN, p99: 500 });
      expect(errors.p95).toBe('Required');
    });

    it('missing p99 returns Required', () => {
      const errors = validateQuantiles({ p50: 10, p95: 100 });
      expect(errors.p99).toBe('Required');
    });

    it('NaN p99 returns Required', () => {
      const errors = validateQuantiles({ p50: 10, p95: 100, p99: NaN });
      expect(errors.p99).toBe('Required');
    });

    it('Infinity p50 returns finite-number error', () => {
      const errors = validateQuantiles({ p50: Infinity, p95: 100, p99: 500 });
      expect(errors.p50).toBe('Must be a finite number');
    });

    it('-Infinity p95 returns finite-number error', () => {
      const errors = validateQuantiles({ p50: 10, p95: -Infinity, p99: 500 });
      expect(errors.p95).toBe('Must be a finite number');
    });
  });

  describe('negative values', () => {
    it('negative p50 returns error', () => {
      const errors = validateQuantiles({ p50: -1, p95: 100, p99: 500 });
      expect(errors.p50).toBeTruthy();
    });

    it('negative p95 returns error', () => {
      const errors = validateQuantiles({ p50: 10, p95: -5, p99: 500 });
      expect(errors.p95).toBeTruthy();
    });

    it('negative p99 returns error', () => {
      const errors = validateQuantiles({ p50: 10, p95: 100, p99: -1 });
      expect(errors.p99).toBeTruthy();
    });
  });

  describe('ordering constraints', () => {
    it('p95 <= p50 returns error on p95', () => {
      const errors = validateQuantiles({ p50: 100, p95: 50, p99: 500 });
      expect(errors.p95).toBeTruthy();
    });

    it('p95 = p50 returns error on p95', () => {
      const errors = validateQuantiles({ p50: 100, p95: 100, p99: 500 });
      expect(errors.p95).toBeTruthy();
    });

    it('p99 <= p95 returns error on p99', () => {
      const errors = validateQuantiles({ p50: 10, p95: 100, p99: 50 });
      expect(errors.p99).toBeTruthy();
    });

    it('p99 = p95 returns error on p99', () => {
      const errors = validateQuantiles({ p50: 10, p95: 100, p99: 100 });
      expect(errors.p99).toBeTruthy();
    });
  });
});

describe('validatePert', () => {
  it('returns empty errors for valid params', () => {
    const errors = validatePert({ min: 0, mode: 5, max: 10 });
    expect(errors).toEqual({});
  });

  describe('required fields', () => {
    it('missing min returns Required', () => {
      const errors = validatePert({ mode: 5, max: 10 });
      expect(errors.min).toBe('Required');
    });

    it('NaN min returns Required', () => {
      const errors = validatePert({ min: NaN, mode: 5, max: 10 });
      expect(errors.min).toBe('Required');
    });

    it('missing mode returns Required', () => {
      const errors = validatePert({ min: 0, max: 10 });
      expect(errors.mode).toBe('Required');
    });

    it('NaN mode returns Required', () => {
      const errors = validatePert({ min: 0, mode: NaN, max: 10 });
      expect(errors.mode).toBe('Required');
    });

    it('missing max returns Required', () => {
      const errors = validatePert({ min: 0, mode: 5 });
      expect(errors.max).toBe('Required');
    });

    it('NaN max returns Required', () => {
      const errors = validatePert({ min: 0, mode: 5, max: NaN });
      expect(errors.max).toBe('Required');
    });

    it('Infinity mode returns finite-number error', () => {
      const errors = validatePert({ min: 0, mode: Infinity, max: 10 });
      expect(errors.mode).toBe('Must be a finite number');
    });
  });

  describe('value constraints', () => {
    it('min < 0 returns error', () => {
      const errors = validatePert({ min: -1, mode: 5, max: 10 });
      expect(errors.min).toBeTruthy();
    });

    it('mode <= min returns error', () => {
      const errors = validatePert({ min: 5, mode: 5, max: 10 });
      expect(errors.mode).toBeTruthy();
    });

    it('mode < min returns error', () => {
      const errors = validatePert({ min: 5, mode: 3, max: 10 });
      expect(errors.mode).toBeTruthy();
    });

    it('max <= mode returns error', () => {
      const errors = validatePert({ min: 0, mode: 10, max: 10 });
      expect(errors.max).toBeTruthy();
    });

    it('max < mode returns error', () => {
      const errors = validatePert({ min: 0, mode: 10, max: 5 });
      expect(errors.max).toBeTruthy();
    });
  });
});

describe('validate dispatcher', () => {
  it('section=loss returns empty object regardless of params', () => {
    expect(validate('loss', {}, 'lognormal')).toEqual({});
    expect(validate('loss', null, 'pert')).toEqual({});
  });

  it('distType=lognormal routes to quantile validation', () => {
    const errors = validate('frequency', { p50: -1, p95: 100, p99: 500 }, 'lognormal');
    expect(errors.p50).toBeTruthy();
  });

  it('distType=pareto routes to quantile validation', () => {
    const errors = validate('cost', { p50: 100, p95: 50, p99: 500 }, 'pareto');
    expect(errors.p95).toBeTruthy();
  });

  it('distType=pert routes to PERT validation', () => {
    const errors = validate('frequency', { min: -1, mode: 5, max: 10 }, 'pert');
    expect(errors.min).toBeTruthy();
  });

  it('unknown distType defaults to quantile validation', () => {
    const errors = validate('frequency', { p50: -1, p95: 100, p99: 500 }, 'unknown');
    expect(errors.p50).toBeTruthy();
  });

  it('distType=odds rejects non-finite values', () => {
    const errors = validate('frequency', { odds: Infinity }, 'odds');
    expect(errors.odds).toBe('Must be a finite number');
  });
});
