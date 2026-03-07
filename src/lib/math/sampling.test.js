import { describe, it, expect } from 'vitest';
import { generateXValues } from './sampling.js';

describe('generateXValues', () => {
  it('generates 500 points by default', () => {
    const values = generateXValues(1, 10);

    expect(values).toHaveLength(500);
    expect(values[0]).toBe(1);
    expect(values[values.length - 1]).toBeCloseTo(10, 12);
  });

  it('respects custom point count and endpoints', () => {
    const values = generateXValues(10, 20, 6);

    expect(values).toEqual([10, 12, 14, 16, 18, 20]);
  });

  it('uses uniform spacing for ascending ranges', () => {
    const values = generateXValues(0, 1, 9);

    const step = values[1] - values[0];
    for (let i = 1; i < values.length - 1; i++) {
      expect(values[i + 1] - values[i]).toBeCloseTo(step, 12);
    }
  });

  it('supports descending ranges with uniform negative spacing', () => {
    const values = generateXValues(5, -5, 6);

    expect(values).toEqual([5, 3, 1, -1, -3, -5]);
  });

  it('returns constant values when lower equals upper', () => {
    const values = generateXValues(7, 7, 8);

    expect(values).toHaveLength(8);
    for (const value of values) {
      expect(value).toBe(7);
    }
  });
});
