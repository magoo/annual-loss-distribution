import { jStat } from 'jstat';

const NUM_POINTS = 500;

/**
 * OLS fit of Pareto parameters from three quantiles (P50, P95, P99).
 * Pareto quantile: Q(p) = scale * (1/(1-p))^(1/shape)
 * Taking logs: ln(Q(p)) = ln(scale) + (1/shape) * ln(1/(1-p))
 * OLS regression of ys on xs gives intercept=ln(scale), slope=1/shape.
 */
export function fitParetoOLS(p50, p95, p99) {
  const xs = [Math.log(1 / (1 - 0.5)), Math.log(1 / (1 - 0.95)), Math.log(1 / (1 - 0.99))];
  // xs = [ln(2), ln(20), ln(100)]
  const ys = [Math.log(p50), Math.log(p95), Math.log(p99)];
  const n = 3;
  const sumX = xs[0] + xs[1] + xs[2];
  const sumY = ys[0] + ys[1] + ys[2];
  const sumXY = xs[0] * ys[0] + xs[1] * ys[1] + xs[2] * ys[2];
  const sumX2 = xs[0] * xs[0] + xs[1] * xs[1] + xs[2] * xs[2];
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  const scale = Math.exp(intercept);
  const shape = 1 / slope;
  return { scale, shape };
}

/**
 * Compute Pareto distribution PDF and CDF values.
 * Fits scale and shape from P50, P95, P99 via OLS.
 * @param {{ p50: number, p95: number, p99: number }} params
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computePareto(params) {
  const { p50, p95, p99 } = params;

  if (p50 <= 0 || p95 <= p50 || p99 <= p95) return null;

  const { scale, shape } = fitParetoOLS(p50, p95, p99);

  if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;

  // Generate log-spaced x-values from ~P0.1 to ~P99.9
  const lower = scale; // Pareto support starts at scale
  const upper = scale * Math.pow(1000, 1 / shape); // P99.9
  if (lower <= 0 || upper <= lower || !isFinite(upper)) return null;

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
      // jStat.pareto uses (scale, shape) parameterization:
      // PDF = shape * scale^shape / x^(shape+1)  for x >= scale
      // CDF = 1 - (scale/x)^shape                for x >= scale
      const pdf = jStat.pareto.pdf(x, scale, shape);
      const cdf = jStat.pareto.cdf(x, scale, shape);
      yPdf.push(isFinite(pdf) ? pdf : 0);
      yCdf.push(isFinite(cdf) ? cdf : 0);
    }
  } catch {
    return null;
  }

  return { x: xValues, yPdf, yCdf };
}
