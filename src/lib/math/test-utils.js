/**
 * Linear interpolation to find CDF value at a target x.
 */
export function interpolateCdf(x, yCdf, target) {
  for (let i = 0; i < x.length - 1; i++) {
    if (x[i] <= target && target <= x[i + 1]) {
      const t = (target - x[i]) / (x[i + 1] - x[i]);
      return yCdf[i] + t * (yCdf[i + 1] - yCdf[i]);
    }
  }
  if (target <= x[0]) return yCdf[0];
  return yCdf[yCdf.length - 1];
}
