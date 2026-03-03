import { jStat } from 'jstat';

const Z_95 = 1.6449;
const NUM_SAMPLES = 10000;
const NUM_PLOT_POINTS = 500;

/**
 * Derive lognormal mu and sigma from P50 and P95.
 */
function deriveMuSigma(p50, p95) {
  const mu = Math.log(p50);
  const sigma = (Math.log(p95) - mu) / Z_95;
  return { mu, sigma };
}

/**
 * Generate lognormal samples using Box-Muller transform.
 * Uses a seeded-style approach with jStat for normal samples.
 */
function sampleLognormal(mu, sigma, n) {
  const samples = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const z = jStat.normal.sample(0, 1);
    samples[i] = Math.exp(mu + sigma * z);
  }
  return samples;
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
 * Transforms samples to log-space, computes KDE there, then transforms back.
 */
function gaussianKdePdf(sortedSamples, xValues) {
  const n = sortedSamples.length;
  const logSamples = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    logSamples[i] = Math.log(sortedSamples[i]);
  }

  // Silverman bandwidth in log-space
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
    // KDE in log-space gives density w.r.t. log(x), divide by x for density w.r.t. x
    const density = coeff * (1 / Math.sqrt(2 * Math.PI)) * sum / x;
    pdf.push(isFinite(density) ? density : 0);
  }

  return pdf;
}

/**
 * Compute Annual Loss distribution via Monte Carlo simulation.
 * Multiplies lognormal frequency samples by lognormal cost samples.
 *
 * @param {{ frequencyParams: {p50, p95}, costParams: {p50, p95} }} allParams
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeAnnualLoss(allParams) {
  const { frequencyParams, costParams } = allParams;

  if (!frequencyParams || !costParams) return null;
  if (frequencyParams.p50 <= 0 || frequencyParams.p95 <= frequencyParams.p50) return null;
  if (costParams.p50 <= 0 || costParams.p95 <= costParams.p50) return null;

  const freqMuSigma = deriveMuSigma(frequencyParams.p50, frequencyParams.p95);
  const costMuSigma = deriveMuSigma(costParams.p50, costParams.p95);

  if (freqMuSigma.sigma <= 0 || costMuSigma.sigma <= 0) return null;

  // Generate samples
  const freqSamples = sampleLognormal(freqMuSigma.mu, freqMuSigma.sigma, NUM_SAMPLES);
  const costSamples = sampleLognormal(costMuSigma.mu, costMuSigma.sigma, NUM_SAMPLES);

  // Pairwise multiplication → annual loss samples
  const lossSamples = new Float64Array(NUM_SAMPLES);
  for (let i = 0; i < NUM_SAMPLES; i++) {
    lossSamples[i] = freqSamples[i] * costSamples[i];
  }

  // Sort for empirical CDF
  lossSamples.sort();

  // Trim to P0.1 – P99 range
  const lowerIdx = Math.floor(NUM_SAMPLES * 0.001);
  const upperIdx = Math.floor(NUM_SAMPLES * 0.99);
  const lower = lossSamples[lowerIdx];
  const upper = lossSamples[upperIdx];

  if (lower <= 0 || upper <= lower || !isFinite(lower) || !isFinite(upper)) return null;

  // Generate x values (log-spaced for better coverage of heavy tail)
  const logLower = Math.log(lower);
  const logUpper = Math.log(upper);
  const logStep = (logUpper - logLower) / (NUM_PLOT_POINTS - 1);
  const x = [];
  for (let i = 0; i < NUM_PLOT_POINTS; i++) {
    x.push(Math.exp(logLower + i * logStep));
  }

  // Compute PDF via Gaussian KDE in log-space
  const yPdf = gaussianKdePdf(lossSamples, x);

  // Compute empirical CDF via binary search
  const yCdf = x.map((xVal) => empiricalCdf(lossSamples, xVal));

  return { x, yPdf, yCdf };
}
