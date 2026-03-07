import { describe, it, expect } from 'vitest';
import {
  SECTIONS,
  DIST_TYPES,
  DIST_CONFIGS,
  getDistConfig,
  computeDistribution,
} from './distributions.js';

describe('SECTIONS', () => {
  it('has frequency, cost, and loss keys', () => {
    expect(SECTIONS).toHaveProperty('frequency');
    expect(SECTIONS).toHaveProperty('cost');
    expect(SECTIONS).toHaveProperty('loss');
  });

  it('frequency does not use dollars', () => {
    expect(SECTIONS.frequency.useDollars).toBe(false);
  });

  it('cost uses dollars', () => {
    expect(SECTIONS.cost.useDollars).toBe(true);
  });

  it('loss uses dollars', () => {
    expect(SECTIONS.loss.useDollars).toBe(true);
  });
});

describe('DIST_TYPES', () => {
  it('contains lognormal, pert, and pareto', () => {
    expect(DIST_TYPES).toContain('lognormal');
    expect(DIST_TYPES).toContain('pert');
    expect(DIST_TYPES).toContain('pareto');
  });

  it('has exactly 3 types', () => {
    expect(DIST_TYPES).toHaveLength(3);
  });
});

describe('DIST_CONFIGS', () => {
  const sections = ['frequency', 'cost'];

  for (const distType of ['lognormal', 'pert', 'pareto']) {
    for (const section of sections) {
      it(`${distType}/${section} has defaults, fields, and guidance`, () => {
        const config = DIST_CONFIGS[distType][section];
        expect(config).toBeDefined();
        expect(config.defaults).toBeDefined();
        expect(config.fields).toBeDefined();
        expect(Array.isArray(config.fields)).toBe(true);
        expect(config.fields.length).toBeGreaterThan(0);
        expect(typeof config.guidance).toBe('string');
      });
    }
  }

  it('each dist type has a label', () => {
    for (const distType of ['lognormal', 'pert', 'pareto']) {
      expect(typeof DIST_CONFIGS[distType].label).toBe('string');
    }
  });
});

describe('getDistConfig', () => {
  it('returns config for valid dist type and section', () => {
    const config = getDistConfig('lognormal', 'frequency');
    expect(config).not.toBeNull();
    expect(config.defaults).toBeDefined();
    expect(config.fields).toBeDefined();
  });

  it('returns null for invalid dist type', () => {
    expect(getDistConfig('invalid', 'frequency')).toBeNull();
  });

  it('returns null for invalid section', () => {
    expect(getDistConfig('lognormal', 'invalid')).toBeNull();
  });

  it('returns null for loss section (no config)', () => {
    expect(getDistConfig('lognormal', 'loss')).toBeNull();
  });
});

describe('computeDistribution', () => {
  it('dispatches lognormal correctly', () => {
    const result = computeDistribution(
      'frequency',
      { p50: 1, p95: 10, p99: 50 },
      null,
      'lognormal'
    );
    expect(result).not.toBeNull();
    expect(result.x.length).toBeGreaterThan(0);
    expect(result.yPdf.length).toBe(result.x.length);
    expect(result.yCdf.length).toBe(result.x.length);
  });

  it('dispatches pert correctly', () => {
    const result = computeDistribution(
      'cost',
      { min: 1000, mode: 50000, max: 500000 },
      null,
      'pert'
    );
    expect(result).not.toBeNull();
    expect(result.x.length).toBeGreaterThan(0);
  });

  it('dispatches pareto correctly', () => {
    const result = computeDistribution(
      'frequency',
      { p50: 5, p95: 20, p99: 80 },
      null,
      'pareto'
    );
    expect(result).not.toBeNull();
    expect(result.x.length).toBeGreaterThan(0);
  });

  it('dispatches loss section to Monte Carlo', () => {
    const allParams = {
      frequencyParams: { p50: 5, p95: 20, p99: 80 },
      costParams: { p50: 50000, p95: 500000, p99: 2000000 },
      frequencyDistType: 'lognormal',
      costDistType: 'lognormal',
    };
    const result = computeDistribution('loss', null, allParams, 'lognormal');
    expect(result).not.toBeNull();
    expect(result.x.length).toBeGreaterThan(0);
  });

  it('defaults to lognormal for unknown dist type', () => {
    const result = computeDistribution(
      'frequency',
      { p50: 1, p95: 10, p99: 50 },
      null,
      'unknown'
    );
    expect(result).not.toBeNull();
    expect(result.x.length).toBeGreaterThan(0);
  });

  it('returns null for loss section when required allParams are invalid', () => {
    const result = computeDistribution('loss', null, {
      frequencyParams: { p50: 0, p95: 10, p99: 50 },
      costParams: { p50: 1000, p95: 10000, p99: 50000 },
      frequencyDistType: 'lognormal',
      costDistType: 'lognormal',
    }, 'lognormal');
    expect(result).toBeNull();
  });

  it('ignores distType argument for loss section and uses allParams dist types', () => {
    const allParams = {
      frequencyParams: { p50: 5, p95: 20, p99: 80 },
      costParams: { min: 1000, mode: 50000, max: 500000 },
      frequencyDistType: 'lognormal',
      costDistType: 'pert',
    };

    const resultKnown = computeDistribution('loss', null, allParams, 'lognormal');
    const resultUnknown = computeDistribution('loss', null, allParams, 'unknown');

    expect(resultKnown).not.toBeNull();
    expect(resultUnknown).not.toBeNull();
    expect(resultKnown).toEqual(resultUnknown);
  });
});
