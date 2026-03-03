/**
 * Linear interpolation on CDF arrays to find the x-value at a target probability.
 * @param {number[]} x - x values (sorted ascending)
 * @param {number[]} yCdf - corresponding CDF values (monotonically increasing)
 * @param {number} p - target probability (0–1)
 * @returns {number} interpolated x-value
 */
export function interpolatePercentile(x, yCdf, p) {
  if (!x || !yCdf || x.length === 0) return 0;
  if (p <= yCdf[0]) return x[0];
  if (p >= yCdf[yCdf.length - 1]) return x[x.length - 1];

  for (let i = 1; i < yCdf.length; i++) {
    if (yCdf[i] >= p) {
      const t = (p - yCdf[i - 1]) / (yCdf[i] - yCdf[i - 1]);
      return x[i - 1] + t * (x[i] - x[i - 1]);
    }
  }

  return x[x.length - 1];
}
