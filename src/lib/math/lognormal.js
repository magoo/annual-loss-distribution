import { jStat } from 'jstat';

const NUM_POINTS = 500;

/**
 * OLS fit of lognormal parameters from three quantiles (P50, P95, P99).
 * Lognormal quantile: ln(Q(p)) = mu + sigma * Z_p
 * Regresses [ln(P50), ln(P95), ln(P99)] on [Z_50=0, Z_95=1.6449, Z_99=2.3263].
 */
export function fitLognormalOLS(p50, p95, p99) {
  const xs = [0, 1.6449, 2.3263]; // Z_50, Z_95, Z_99
  const ys = [Math.log(p50), Math.log(p95), Math.log(p99)];
  const n = 3;
  const sumX = xs[0] + xs[1] + xs[2];
  const sumY = ys[0] + ys[1] + ys[2];
  const sumXY = xs[0] * ys[0] + xs[1] * ys[1] + xs[2] * ys[2];
  const sumX2 = xs[0] * xs[0] + xs[1] * xs[1] + xs[2] * xs[2];
  const sigma = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const mu = (sumY - sigma * sumX) / n;
  return { mu, sigma };
}

/**
 * Compute Lognormal distribution PDF and CDF values.
 * Derives mu and sigma from P50, P95, and P99 via OLS.
 * @param {{ p50: number, p95: number, p99: number }} params
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeLognormal(params) {
  const { p50, p95, p99 } = params;

  if (p50 <= 0 || p95 <= p50 || p99 <= p95) return null;

  const { mu, sigma } = fitLognormalOLS(p50, p95, p99);

  if (sigma <= 0 || !isFinite(mu) || !isFinite(sigma)) return null;

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
