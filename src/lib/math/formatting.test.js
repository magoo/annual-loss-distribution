import { describe, it, expect } from 'vitest';
import { formatValue, formatCompact } from './formatting.js';

describe('formatValue', () => {
  it('returns em dash for nullish or NaN values', () => {
    expect(formatValue(null, true)).toBe('—');
    expect(formatValue(undefined, false)).toBe('—');
    expect(formatValue(Number.NaN, true)).toBe('—');
  });

  it('formats dollar values with rounding and separators', () => {
    expect(formatValue(1234.2, true)).toBe('$1,234');
    expect(formatValue(1234.8, true)).toBe('$1,235');
  });

  it('formats non-dollar values with up to 2 fractional digits', () => {
    expect(formatValue(1234.567, false)).toBe('1,234.57');
    expect(formatValue(1234, false)).toBe('1,234');
  });
});

describe('formatCompact', () => {
  it('returns em dash for nullish or NaN values', () => {
    expect(formatCompact(null, true)).toBe('—');
    expect(formatCompact(Number.NaN, false)).toBe('—');
  });

  it('applies K/M/B suffixes for dollar values', () => {
    expect(formatCompact(1500, true)).toBe('$1.5K');
    expect(formatCompact(2_500_000, true)).toBe('$2.5M');
    expect(formatCompact(3_200_000_000, true)).toBe('$3.2B');
  });

  it('uses compact suffixes for non-dollar values only at M/B scale', () => {
    expect(formatCompact(1500, false)).toBe('1,500');
    expect(formatCompact(2_500_000, false)).toBe('2.5M');
    expect(formatCompact(3_200_000_000, false)).toBe('3.2B');
  });

  it('preserves sign in compact formatting', () => {
    expect(formatCompact(-1500, true)).toBe('$-1.5K');
    expect(formatCompact(-2_500_000, false)).toBe('-2.5M');
  });

  it('falls back to formatValue when suffix thresholds are not met', () => {
    expect(formatCompact(999, true)).toBe('$999');
    expect(formatCompact(999.25, false)).toBe('999.25');
  });
});
