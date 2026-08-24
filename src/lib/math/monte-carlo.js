import { jStat } from 'jstat';
import { fitLognormal } from './lognormal.js';
import { fitPareto } from './pareto.js';
import { fitPert } from './pert.js';
import { createRng } from './rng.js';
import { empiricalCdfArrays } from './empirical.js';
import { frequencyWorkRate } from './moments.js';
import {
  MIN_SIMULATION_ROUNDS,
  MAX_EVENTS_PER_ROUND,
  TARGET_EVENT_DRAWS,
  MAX_TOTAL_EVENT_DRAWS,
} from './simulation-limits.js';

const DEFAULT_SEED = 12345;
const NUM_SAMPLES = 100000;

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
      const { mu, sigma } = fitLognormal(params.p50, params.p95);
      if (sigma <= 0 || !isFinite(mu) || !isFinite(sigma)) return null;
      for (let i = 0; i < n; i++) {
        const sample = jStat.lognormal.inv(rng(), mu, sigma);
        if (!Number.isFinite(sample) || sample < 0) return null;
        samples[i] = sample;
      }
      break;
    }
    case 'pert': {
      const { alpha, beta, min, max } = fitPert(params.min, params.mode, params.max);
      const range = max - min;
      if (alpha <= 0 || beta <= 0 || range <= 0) return null;
      for (let i = 0; i < n; i++) {
        const sample = min + range * jStat.beta.inv(rng(), alpha, beta);
        if (!Number.isFinite(sample) || sample < 0) return null;
        samples[i] = sample;
      }
      break;
    }
    case 'pareto': {
      const { scale, shape } = fitPareto(params.p50, params.p95);
      if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;
      for (let i = 0; i < n; i++) {
        const sample = jStat.pareto.inv(rng(), scale, shape);
        if (!Number.isFinite(sample) || sample < 0) return null;
        samples[i] = sample;
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
      return params.p50 > 0 && params.p95 > params.p50;
    case 'pert':
      return params.min >= 0 && params.mode > params.min && params.max > params.mode;
    default:
      return false;
  }
}

/**
 * Compute Annual Loss distribution via Monte Carlo simulation.
 * Treats frequency as an annual incident count and sums an independent cost
 * draw for every simulated incident (supports mixed distribution types).
 *
 * @param {object} allParams
 * @param {object} allParams.frequencyParams
 * @param {object} allParams.costParams
 * @param {string} allParams.frequencyDistType
 * @param {string} allParams.costDistType
 * @returns {{ samples: number[], x: number[], yCdf: number[], isHistogram: true, numRounds: number } | null}
 */
export function computeAnnualLoss(allParams) {
  if (!allParams) return null;
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

  const workRate = frequencyWorkRate(frequencyDistType, frequencyParams);
  if (!Number.isFinite(workRate) || workRate < 0) return null;

  const plannedSamples = Math.min(
    NUM_SAMPLES,
    Math.max(MIN_SIMULATION_ROUNDS, Math.floor(TARGET_EVENT_DRAWS / Math.max(1, workRate))),
  );
  if (plannedSamples * workRate > MAX_TOTAL_EVENT_DRAWS) return null;

  const frequencySamples = sampleDistribution(frequencyDistType, frequencyParams, plannedSamples, rng);
  if (!frequencySamples) return null;

  const eventCounts = new Uint32Array(plannedSamples);
  let totalEventDraws = 0;
  for (let year = 0; year < plannedSamples; year++) {
    const count = Math.max(0, Math.round(frequencySamples[year]));
    if (!Number.isSafeInteger(count) || count > MAX_EVENTS_PER_ROUND) return null;
    totalEventDraws += count;
    if (totalEventDraws > MAX_TOTAL_EVENT_DRAWS) return null;
    eventCounts[year] = count;
  }

  const costSamples = sampleDistribution(costDistType, costParams, totalEventDraws, rng);
  if (!costSamples) return null;

  const lossSamples = new Float64Array(plannedSamples);
  let costIndex = 0;
  for (let i = 0; i < plannedSamples; i++) {
    let annualLoss = 0;
    for (let event = 0; event < eventCounts[i]; event++) {
      annualLoss += costSamples[costIndex++];
    }
    lossSamples[i] = annualLoss;
  }

  lossSamples.sort();
  const { x, yCdf } = empiricalCdfArrays(lossSamples);
  if (x.length === 0) return null;

  return {
    samples: Array.from(lossSamples),
    x,
    yCdf,
    isHistogram: true,
    numRounds: plannedSamples,
  };
}
