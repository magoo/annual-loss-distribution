/**
 * Format a numeric value with optional dollar sign.
 * @param {number} value
 * @param {boolean} useDollars
 * @returns {string}
 */
export function formatValue(value, useDollars) {
  if (value == null || isNaN(value)) return '—';
  const formatted = useDollars
    ? '$' + Math.round(value).toLocaleString('en-US')
    : value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  return formatted;
}

/**
 * Format a value compactly for large numbers (e.g., $2.4M).
 * @param {number} value
 * @param {boolean} useDollars
 * @returns {string}
 */
export function formatCompact(value, useDollars) {
  if (value == null || isNaN(value)) return '—';

  const abs = Math.abs(value);
  let num, suffix;

  if (abs >= 1e9) {
    num = value / 1e9;
    suffix = 'B';
  } else if (abs >= 1e6) {
    num = value / 1e6;
    suffix = 'M';
  } else if (abs >= 1e3 && useDollars) {
    num = value / 1e3;
    suffix = 'K';
  } else {
    return formatValue(value, useDollars);
  }

  const formatted = num.toLocaleString('en-US', { maximumFractionDigits: 1 });
  return useDollars ? `$${formatted}${suffix}` : `${formatted}${suffix}`;
}
