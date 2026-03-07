import { describe, it, expect } from 'vitest';
import { computeScenarioMC } from './scenario-monte-carlo.js';

const oddsScenario = [
  {
    id: 1,
    name: 'Phishing',
    frequencyMethod: 'odds',
    frequencyParams: { odds: 2 },
    costDistType: 'lognormal',
    costParams: { p50: 10_000, p95: 50_000, p99: 150_000 },
  },
];

const mixedCostScenarios = [
  {
    id: 1,
    name: 'A',
    frequencyMethod: 'odds',
    frequencyParams: { odds: 3 },
    costDistType: 'lognormal',
    costParams: { p50: 10_000, p95: 50_000, p99: 150_000 },
  },
  {
    id: 2,
    name: 'B',
    frequencyMethod: 'odds',
    frequencyParams: { odds: 4 },
    costDistType: 'pert',
    costParams: { min: 5_000, mode: 20_000, max: 250_000 },
  },
];

describe('computeScenarioMC', () => {
  it('returns null for empty scenarios', () => {
    expect(computeScenarioMC([], 'loss')).toBeNull();
    expect(computeScenarioMC(null, 'loss')).toBeNull();
  });

  it('produces deterministic output for the same inputs', () => {
    const result1 = computeScenarioMC(oddsScenario, 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
    });
    const result2 = computeScenarioMC(oddsScenario, 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
    });

    expect(result1).not.toBeNull();
    expect(result2).not.toBeNull();
    expect(result1).toEqual(result2);
  });

  it('returns histogram contract with bounded, monotone CDF for valid scenario frequency runs', () => {
    const result = computeScenarioMC(oddsScenario, 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
    });

    expect(result).not.toBeNull();
    expect(result.isHistogram).toBe(true);
    expect(result.samples.length).toBe(10_000);
    expect(result.x.length).toBeGreaterThan(0);
    expect(result.yCdf.length).toBe(result.x.length);

    for (let i = 0; i < result.samples.length; i++) {
      expect(Number.isFinite(result.samples[i])).toBe(true);
      expect(result.samples[i]).toBeGreaterThanOrEqual(0);
      expect(Number.isInteger(result.samples[i])).toBe(true);
    }

    for (let i = 0; i < result.yCdf.length; i++) {
      expect(result.yCdf[i]).toBeGreaterThanOrEqual(0);
      expect(result.yCdf[i]).toBeLessThanOrEqual(1);
      if (i > 0) {
        expect(result.yCdf[i]).toBeGreaterThanOrEqual(result.yCdf[i - 1]);
      }
    }
  });

  it('supports hybrid mode: single-distribution frequency with scenario-based costs', () => {
    const result = computeScenarioMC(mixedCostScenarios, 'loss', {
      frequencyScenarioMode: false,
      costScenarioMode: true,
      frequencyDistType: 'lognormal',
      frequencyParams: { p50: 2, p95: 8, p99: 20 },
    });

    expect(result).not.toBeNull();
    expect(result.samples.length).toBe(10_000);
    expect(result.x.length).toBeGreaterThan(0);
    expect(result.yCdf.length).toBe(result.x.length);
    expect(result.samples.some((v) => v > 0)).toBe(true);
  });

  it('supports hybrid mode: scenario-based frequency with single-distribution costs', () => {
    const result = computeScenarioMC(oddsScenario, 'cost', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
      costDistType: 'pert',
      costParams: { min: 1_000, mode: 10_000, max: 50_000 },
    });

    expect(result).not.toBeNull();
    expect(result.samples.length).toBeGreaterThan(0);
    expect(result.x.length).toBeGreaterThan(0);
    expect(result.yCdf.length).toBe(result.x.length);
    expect(result.samples.every((v) => v >= 0)).toBe(true);
  });

  it('ignores cost params when active section is frequency and cost scenario mode is off', () => {
    const result = computeScenarioMC([
      {
        id: 1,
        name: 'No cost needed',
        frequencyMethod: 'odds',
        frequencyParams: { odds: 3 },
      },
    ], 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
    });

    expect(result).not.toBeNull();
    expect(result.samples.length).toBe(10_000);
  });

  it('returns null when a scenario has invalid odds parameters', () => {
    const invalid = [
      {
        id: 1,
        name: 'Invalid',
        frequencyMethod: 'odds',
        frequencyParams: { odds: 0 },
        costDistType: 'lognormal',
        costParams: { p50: 1_000, p95: 10_000, p99: 50_000 },
      },
    ];

    expect(computeScenarioMC(invalid, 'loss')).toBeNull();
  });

  it('returns null when hybrid single-distribution samplers are invalid', () => {
    const invalidFreq = computeScenarioMC(oddsScenario, 'loss', {
      frequencyScenarioMode: false,
      costScenarioMode: true,
      frequencyDistType: 'lognormal',
      frequencyParams: { p50: 10, p95: 10, p99: 20 },
    });

    const invalidCost = computeScenarioMC(oddsScenario, 'loss', {
      frequencyScenarioMode: true,
      costScenarioMode: false,
      costDistType: 'pert',
      costParams: { min: 10, mode: 10, max: 100 },
    });

    expect(invalidFreq).toBeNull();
    expect(invalidCost).toBeNull();
  });
});
