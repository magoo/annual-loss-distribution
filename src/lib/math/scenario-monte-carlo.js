import { jStat } from 'jstat';
import { fitLognormalOLS } from './lognormal.js';
import { fitParetoOLS } from './pareto.js';
import { fitPert } from './pert.js';

const DEFAULT_SEED = 54321;
const NUM_ROUNDS = 10000;
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
 * Build an inverse-CDF sampler for a given distribution type and params.
 * Returns a function(rng) => sample, or null if params are invalid.
 */
function buildSampler(distType, params) {
  switch (distType) {
    case 'lognormal': {
      if (params.p50 <= 0 || params.p95 <= params.p50 || params.p99 <= params.p95) return null;
      const { mu, sigma } = fitLognormalOLS(params.p50, params.p95, params.p99);
      if (sigma <= 0 || !isFinite(mu) || !isFinite(sigma)) return null;
      return (rng) => jStat.lognormal.inv(rng(), mu, sigma);
    }
    case 'pert': {
      if (params.min >= params.mode || params.mode >= params.max || params.min < 0) return null;
      const { alpha, beta, min, max } = fitPert(params.min, params.mode, params.max);
      const range = max - min;
      if (alpha <= 0 || beta <= 0 || range <= 0) return null;
      return (rng) => min + range * jStat.beta.inv(rng(), alpha, beta);
    }
    case 'pareto': {
      if (params.p50 <= 0 || params.p95 <= params.p50 || params.p99 <= params.p95) return null;
      const { scale, shape } = fitParetoOLS(params.p50, params.p95, params.p99);
      if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;
      return (rng) => jStat.pareto.inv(rng(), scale, shape);
    }
    default:
      return null;
  }
}

/**
 * Compute empirical CDF arrays from sorted samples at evenly-spaced x points.
 */
function empiricalCdfArrays(sortedSamples) {
  const n = sortedSamples.length;
  if (n === 0) return { x: [], yCdf: [] };

  const lower = sortedSamples[Math.floor(n * 0.001)] || sortedSamples[0];
  const upper = sortedSamples[Math.min(Math.floor(n * 0.999), n - 1)];

  if (lower <= 0 || upper <= lower) {
    // For integer/zero-heavy data (frequency), use linear spacing
    const xMin = Math.max(0, sortedSamples[0]);
    const xMax = sortedSamples[n - 1];
    if (xMax <= xMin) return { x: [xMin], yCdf: [1] };

    const step = (xMax - xMin) / (NUM_PLOT_POINTS - 1);
    const x = [];
    const yCdf = [];
    let sIdx = 0;
    for (let i = 0; i < NUM_PLOT_POINTS; i++) {
      const xVal = xMin + i * step;
      x.push(xVal);
      while (sIdx < n && sortedSamples[sIdx] <= xVal) sIdx++;
      yCdf.push(sIdx / n);
    }
    return { x, yCdf };
  }

  // Log-spaced for positive continuous data
  const logLower = Math.log(lower);
  const logUpper = Math.log(upper);
  const logStep = (logUpper - logLower) / (NUM_PLOT_POINTS - 1);
  const x = [];
  const yCdf = [];
  let sIdx = 0;
  for (let i = 0; i < NUM_PLOT_POINTS; i++) {
    const xVal = Math.exp(logLower + i * logStep);
    x.push(xVal);
    while (sIdx < n && sortedSamples[sIdx] <= xVal) sIdx++;
    yCdf.push(sIdx / n);
  }
  return { x, yCdf };
}

/**
 * Run scenario-based Monte Carlo simulation.
 * Supports hybrid mode where frequency and/or cost can come from scenarios or a single distribution.
 *
 * @param {Array} scenarios - Array of scenario objects
 * @param {'frequency'|'cost'|'loss'} activeSection - Which tab is active
 * @param {object} [options] - Hybrid mode options
 * @param {boolean} [options.frequencyScenarioMode] - Whether frequency uses scenarios
 * @param {boolean} [options.costScenarioMode] - Whether cost uses scenarios
 * @param {object} [options.frequencyParams] - Single dist params when freq scenario off
 * @param {object} [options.costParams] - Single dist params when cost scenario off
 * @param {string} [options.frequencyDistType] - Dist type when freq scenario off
 * @param {string} [options.costDistType] - Dist type when cost scenario off
 * @returns {{ samples: number[], x: number[], yCdf: number[], isHistogram: true } | null}
 */
export function computeScenarioMC(scenarios, activeSection, options = {}) {
  if (!scenarios || scenarios.length === 0) return null;

  const {
    frequencyScenarioMode = true,
    costScenarioMode = true,
    frequencyParams = null,
    costParams = null,
    frequencyDistType = 'lognormal',
    costDistType = 'lognormal',
  } = options;

  const rng = createRng(DEFAULT_SEED);

  // Pre-build scenario samplers
  const scenarioSamplers = scenarios.map((s) => {
    let freqSampler = null;
    if (frequencyScenarioMode) {
      if (s.frequencyMethod === 'odds') {
        const odds = s.frequencyParams?.odds;
        if (!odds || odds <= 0) return null;
        freqSampler = { type: 'odds', prob: 1 / odds };
      } else {
        const sampler = buildSampler(s.frequencyMethod, s.frequencyParams);
        if (!sampler) return null;
        freqSampler = { type: 'dist', sample: sampler };
      }
    }

    let costSampler = null;
    if (costScenarioMode) {
      costSampler = buildSampler(s.costDistType, s.costParams);
      if (!costSampler) return null;
    }

    return { freqSampler, costSampler };
  });

  // If any scenario has invalid params, bail
  if (scenarioSamplers.some((s) => s === null)) return null;

  // Build single-distribution samplers for hybrid mode
  let singleFreqSampler = null;
  if (!frequencyScenarioMode && frequencyParams) {
    singleFreqSampler = buildSampler(frequencyDistType, frequencyParams);
    if (!singleFreqSampler) return null;
  }

  let singleCostSampler = null;
  if (!costScenarioMode && costParams) {
    singleCostSampler = buildSampler(costDistType, costParams);
    if (!singleCostSampler) return null;
  }

  // Determine if we need cost sampling (not needed when only viewing frequency)
  const needCost = activeSection !== 'frequency';

  const frequencySamples = new Float64Array(NUM_ROUNDS);
  const lossSamples = needCost ? new Float64Array(NUM_ROUNDS) : null;
  const costsList = needCost ? [] : null;

  for (let round = 0; round < NUM_ROUNDS; round++) {
    let totalIncidents = 0;
    let totalLoss = 0;

    if (frequencyScenarioMode) {
      // Scenario-based frequency: each scenario contributes incidents
      for (let si = 0; si < scenarioSamplers.length; si++) {
        const { freqSampler, costSampler } = scenarioSamplers[si];

        let count;
        if (freqSampler.type === 'odds') {
          count = rng() < freqSampler.prob ? 1 : 0;
        } else {
          const raw = freqSampler.sample(rng);
          count = Math.max(0, Math.round(raw));
        }

        totalIncidents += count;

        if (needCost) {
          for (let k = 0; k < count; k++) {
            let cost;
            if (costScenarioMode) {
              cost = Math.max(0, costSampler(rng));
            } else {
              cost = Math.max(0, singleCostSampler(rng));
            }
            costsList.push(cost);
            totalLoss += cost;
          }
        }
      }
    } else {
      // Single-distribution frequency
      const rawFreq = singleFreqSampler(rng);
      const count = Math.max(0, Math.round(rawFreq));
      totalIncidents = count;

      if (needCost) {
        for (let k = 0; k < count; k++) {
          let cost;
          if (costScenarioMode) {
            // Pick a random scenario's cost distribution
            const si = Math.floor(rng() * scenarioSamplers.length);
            cost = Math.max(0, scenarioSamplers[si].costSampler(rng));
          } else {
            cost = Math.max(0, singleCostSampler(rng));
          }
          costsList.push(cost);
          totalLoss += cost;
        }
      }
    }

    frequencySamples[round] = totalIncidents;
    if (lossSamples) lossSamples[round] = totalLoss;
  }

  // Return based on active section
  let samples;
  if (activeSection === 'frequency') {
    samples = Array.from(frequencySamples);
  } else if (activeSection === 'cost') {
    samples = costsList;
  } else {
    samples = Array.from(lossSamples);
  }

  if (samples.length === 0) return null;

  // Sort for CDF
  const sorted = Float64Array.from(samples);
  sorted.sort();

  const { x, yCdf } = empiricalCdfArrays(sorted);

  return { samples, x, yCdf, isHistogram: true };
}
