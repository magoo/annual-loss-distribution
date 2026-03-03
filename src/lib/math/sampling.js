/**
 * Generate evenly spaced x values for plotting.
 * @param {number} lower - Lower bound
 * @param {number} upper - Upper bound
 * @param {number} n - Number of points (default 500)
 * @returns {number[]}
 */
export function generateXValues(lower, upper, n = 500) {
  const step = (upper - lower) / (n - 1);
  const values = [];
  for (let i = 0; i < n; i++) {
    values.push(lower + i * step);
  }
  return values;
}
