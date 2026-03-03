import { jStat } from 'jstat';

const Z_95 = 1.6449; // inverse normal CDF at 0.95
const NUM_POINTS = 500;

/**
 * Compute Lognormal distribution PDF and CDF values.
 * Derives mu and sigma from P50 and P95.
 * @param {{ p50: number, p95: number }} params
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeLognormal(params) {
  const { p50, p95 } = params;

  if (p50 <= 0 || p95 <= p50) return null;

  const mu = Math.log(p50);
  const sigma = (Math.log(p95) - mu) / Z_95;

  if (sigma <= 0 || !isFinite(mu) || !isFinite(sigma)) return null;

  // Use quantile-based bounds so the CDF spans [~0.001, ~0.999],
  // and log-space the grid so resolution is uniform across orders of magnitude.
  const lower = jStat.lognormal.inv(0.001, mu, sigma);
  const upper = jStat.lognormal.inv(0.999, mu, sigma);
  const logLower = Math.log(lower);
  const logUpper = Math.log(upper);
  const logStep = (logUpper - logLower) / (NUM_POINTS - 1);
  const xValues = [];
  for (let i = 0; i < NUM_POINTS; i++) {
    xValues.push(Math.exp(logLower + i * logStep));
  }
  const yPdf = [];
  const yCdf = [];

  try {
    for (const x of xValues) {
      const pdf = jStat.lognormal.pdf(x, mu, sigma);
      const cdf = jStat.lognormal.cdf(x, mu, sigma);
      yPdf.push(isFinite(pdf) ? pdf : 0);
      yCdf.push(isFinite(cdf) ? cdf : 0);
    }
  } catch {
    return null;
  }

  return { x: xValues, yPdf, yCdf };
}
