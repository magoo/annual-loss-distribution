import { jStat } from 'jstat';

const NUM_POINTS = 500;

/**
 * Derive PERT (modified beta) shape parameters.
 * alpha = 1 + 4*(mode - min) / (max - min)
 * beta  = 1 + 4*(max - mode) / (max - min)
 */
export function fitPert(min, mode, max) {
  const range = max - min;
  const alpha = 1 + 4 * (mode - min) / range;
  const beta = 1 + 4 * (max - mode) / range;
  return { alpha, beta, min, max };
}

/**
 * Compute PERT distribution PDF and CDF values.
 * Uses a scaled Beta distribution on [min, max].
 * @param {{ min: number, mode: number, max: number }} params
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computePert(params) {
  const { min, mode, max } = params;

  if (min >= mode || mode >= max) return null;
  if (min < 0) return null;

  const range = max - min;
  if (range <= 0 || !isFinite(range)) return null;

  const { alpha, beta } = fitPert(min, mode, max);

  if (alpha <= 0 || beta <= 0 || !isFinite(alpha) || !isFinite(beta)) return null;

  // Generate x values linearly in [min, max]
  const step = range / (NUM_POINTS - 1);
  const xValues = [];
  for (let i = 0; i < NUM_POINTS; i++) {
    xValues.push(min + i * step);
  }

  const yPdf = [];
  const yCdf = [];

  try {
    for (const x of xValues) {
      // Transform x to [0,1] for the standard beta
      const t = (x - min) / range;
      const clamped = Math.max(0, Math.min(1, t));
      const pdf = jStat.beta.pdf(clamped, alpha, beta) / range;
      const cdf = jStat.beta.cdf(clamped, alpha, beta);
      yPdf.push(isFinite(pdf) ? pdf : 0);
      yCdf.push(isFinite(cdf) ? cdf : 0);
    }
  } catch {
    return null;
  }

  return { x: xValues, yPdf, yCdf };
}
