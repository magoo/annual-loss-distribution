import { jStat } from 'jstat';
import { fitLognormalOLS } from './lognormal.js';
import { fitParetoOLS } from './pareto.js';
import { fitPert } from './pert.js';

const DEFAULT_SEED = 12345;
const NUM_SAMPLES = 100000;
const NUM_PLOT_POINTS = 500;

/**
 * Mulberry32 seeded PRNG. Returns values in [0, 1).
 */
function createRng(seed = DEFAULT_SEED) {
  let s = seed | 0;
  return function () {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Sample from a distribution using inverse transform sampling with seeded RNG.
 * @param {string} distType - 'lognormal', 'pert', or 'pareto'
 * @param {object} params - Distribution parameters
 * @param {number} n - Number of samples
 * @param {function} rng - Seeded RNG returning [0,1)
 * @returns {Float64Array}
 */
function sampleDistribution(distType, params, n, rng) {
  const samples = new Float64Array(n);

  switch (distType) {
    case 'lognormal': {
      const { mu, sigma } = fitLognormalOLS(params.p50, params.p95, params.p99);
      if (sigma <= 0 || !isFinite(mu) || !isFinite(sigma)) return null;
      for (let i = 0; i < n; i++) {
        samples[i] = jStat.lognormal.inv(rng(), mu, sigma);
      }
      break;
    }
    case 'pert': {
      const { alpha, beta, min, max } = fitPert(params.min, params.mode, params.max);
      const range = max - min;
      if (alpha <= 0 || beta <= 0 || range <= 0) return null;
      for (let i = 0; i < n; i++) {
        samples[i] = min + range * jStat.beta.inv(rng(), alpha, beta);
      }
      break;
    }
    case 'pareto': {
      const { scale, shape } = fitParetoOLS(params.p50, params.p95, params.p99);
      if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;
      for (let i = 0; i < n; i++) {
        samples[i] = jStat.pareto.inv(rng(), scale, shape);
      }
      break;
    }
    default:
      return null;
  }

  return samples;
}

/**
 * Validate params can produce samples for a given distribution type.
 */
function validateDistParams(distType, params) {
  switch (distType) {
    case 'lognormal':
    case 'pareto':
      return params.p50 > 0 && params.p95 > params.p50 && params.p99 > params.p95;
    case 'pert':
      return params.min >= 0 && params.mode > params.min && params.max > params.mode;
    default:
      return false;
  }
}

/**
 * Compute empirical CDF value for a given x using binary search on sorted samples.
 */
function empiricalCdf(sortedSamples, x) {
  let lo = 0;
  let hi = sortedSamples.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (sortedSamples[mid] <= x) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo / sortedSamples.length;
}

/**
 * Gaussian KDE in log-space with Silverman bandwidth.
 */
function gaussianKdePdf(sortedSamples, xValues) {
  const n = sortedSamples.length;
  const logSamples = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    logSamples[i] = Math.log(sortedSamples[i]);
  }

  const mean = logSamples.reduce((a, b) => a + b, 0) / n;
  const variance = logSamples.reduce((sum, v) => sum + (v - mean) ** 2, 0) / n;
  const stddev = Math.sqrt(variance);
  const h = 1.06 * stddev * Math.pow(n, -0.2);

  if (h <= 0 || !isFinite(h)) return xValues.map(() => 0);

  const pdf = [];
  const coeff = 1 / (n * h);

  for (const x of xValues) {
    const logX = Math.log(x);
    let sum = 0;
    for (let i = 0; i < n; i++) {
      const u = (logX - logSamples[i]) / h;
      sum += Math.exp(-0.5 * u * u);
    }
    const density = coeff * (1 / Math.sqrt(2 * Math.PI)) * (sum / x);
    pdf.push(isFinite(density) ? density : 0);
  }

  return pdf;
}

/**
 * Compute Annual Loss distribution via Monte Carlo simulation.
 * Multiplies frequency samples by cost samples (supports mixed distribution types).
 *
 * @param {object} allParams
 * @param {object} allParams.frequencyParams
 * @param {object} allParams.costParams
 * @param {string} allParams.frequencyDistType
 * @param {string} allParams.costDistType
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeAnnualLoss(allParams) {
  const {
    frequencyParams,
    costParams,
    frequencyDistType = 'lognormal',
    costDistType = 'lognormal',
  } = allParams;

  if (!frequencyParams || !costParams) return null;
  if (!validateDistParams(frequencyDistType, frequencyParams)) return null;
  if (!validateDistParams(costDistType, costParams)) return null;

  const rng = createRng(DEFAULT_SEED);

  const freqSamples = sampleDistribution(frequencyDistType, frequencyParams, NUM_SAMPLES, rng);
  const costSamples = sampleDistribution(costDistType, costParams, NUM_SAMPLES, rng);

  if (!freqSamples || !costSamples) return null;

  // Pairwise multiplication
  const lossSamples = new Float64Array(NUM_SAMPLES);
  for (let i = 0; i < NUM_SAMPLES; i++) {
    lossSamples[i] = freqSamples[i] * costSamples[i];
  }

  lossSamples.sort();

  // Trim to P0.1 - P99 range
  const lowerIdx = Math.floor(NUM_SAMPLES * 0.001);
  const upperIdx = Math.floor(NUM_SAMPLES * 0.99);
  const lower = lossSamples[lowerIdx];
  const upper = lossSamples[upperIdx];

  if (lower <= 0 || upper <= lower || !isFinite(lower) || !isFinite(upper)) return null;

  // Log-spaced x values
  const logLower = Math.log(lower);
  const logUpper = Math.log(upper);
  const logStep = (logUpper - logLower) / (NUM_PLOT_POINTS - 1);
  const x = [];
  for (let i = 0; i < NUM_PLOT_POINTS; i++) {
    x.push(Math.exp(logLower + i * logStep));
  }

  const yPdf = gaussianKdePdf(lossSamples, x);
  const yCdf = x.map((xVal) => empiricalCdf(lossSamples, xVal));

  return { x, yPdf, yCdf };
}
