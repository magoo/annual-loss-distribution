import { jStat } from 'jstat';

const NUM_POINTS = 500;

/**
 * Fit Pareto parameters exactly from P50 and P95.
 * Pareto quantile: Q(p) = scale * (1/(1-p))^(1/shape)
 */
export function fitPareto(p50, p95) {
  const shape = Math.log(10) / Math.log(p95 / p50);
  const scale = p50 / Math.pow(2, 1 / shape);
  return { scale, shape };
}

/**
 * Compute Pareto distribution PDF and CDF values.
 * Fits scale and shape from P50 and P95.
 * @param {{ p50: number, p95: number }} params
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computePareto(params) {
  const { p50, p95 } = params;

  if (p50 <= 0 || p95 <= p50) return null;

  const { scale, shape } = fitPareto(p50, p95);

  if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;

  // Generate log-spaced x-values across nearly the full positive support.
  const lower = scale; // Pareto support starts at scale
  const upper = scale * Math.pow(1000, 1 / shape);
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
