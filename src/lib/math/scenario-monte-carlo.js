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

const DEFAULT_SEED = 54321;
const NUM_ROUNDS = 10000;

/**
 * Build an inverse-CDF sampler for a given distribution type and params.
 * Returns a function(rng) => sample, or null if params are invalid.
 */
function buildSampler(distType, params) {
  if (!params) return null;
  switch (distType) {
    case 'lognormal': {
      if (params.p50 <= 0 || params.p95 <= params.p50) return null;
      const { mu, sigma } = fitLognormal(params.p50, params.p95);
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
      if (params.p50 <= 0 || params.p95 <= params.p50) return null;
      const { scale, shape } = fitPareto(params.p50, params.p95);
      if (scale <= 0 || shape <= 0 || !isFinite(scale) || !isFinite(shape)) return null;
      return (rng) => jStat.pareto.inv(rng(), scale, shape);
    }
    default:
      return null;
  }
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
 * @returns {{ samples: number[], x: number[], yCdf: number[], isHistogram: true, numRounds: number } | null}
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
  const needCost = activeSection !== 'frequency';

  // Pre-build scenario samplers
  const scenarioSamplers = scenarios.map((s) => {
    let freqSampler = null;
    if (frequencyScenarioMode) {
      if (s.frequencyMethod === 'odds') {
        const odds = s.frequencyParams?.odds;
        if (!Number.isFinite(odds) || odds < 1) return null;
        freqSampler = { type: 'odds', prob: 1 / odds, workRate: 1 / odds };
      } else {
        const sampler = buildSampler(s.frequencyMethod, s.frequencyParams);
        if (!sampler) return null;
        freqSampler = {
          type: 'dist',
          sample: sampler,
          workRate: frequencyWorkRate(s.frequencyMethod, s.frequencyParams),
        };
      }
    }

    let costSampler = null;
    if (costScenarioMode && needCost) {
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

  const workRate = frequencyScenarioMode
    ? scenarioSamplers.reduce((sum, sampler) => sum + sampler.freqSampler.workRate, 0)
    : frequencyWorkRate(frequencyDistType, frequencyParams);
  if (!Number.isFinite(workRate) || workRate < 0) return null;

  let singleCostSampler = null;
  if (needCost && !costScenarioMode && costParams) {
    singleCostSampler = buildSampler(costDistType, costParams);
    if (!singleCostSampler) return null;
  }
  const plannedRounds = needCost
    ? Math.min(
        NUM_ROUNDS,
        Math.max(MIN_SIMULATION_ROUNDS, Math.floor(TARGET_EVENT_DRAWS / Math.max(1, workRate))),
      )
    : NUM_ROUNDS;
  if (needCost && plannedRounds * workRate > MAX_TOTAL_EVENT_DRAWS) return null;

  const frequencySamples = [];
  const lossSamples = needCost ? [] : null;
  const costsList = needCost ? [] : null;
  let totalEventDraws = 0;

  for (let round = 0; round < plannedRounds; round++) {
    let totalIncidents = 0;
    let totalLoss = 0;
    const scenarioCounts = frequencyScenarioMode ? [] : null;

    if (frequencyScenarioMode) {
      // Determine the full year's incident count before drawing any costs so
      // the work budget can stop cleanly between simulated years.
      for (let si = 0; si < scenarioSamplers.length; si++) {
        const { freqSampler } = scenarioSamplers[si];

        let count;
        if (freqSampler.type === 'odds') {
          count = rng() < freqSampler.prob ? 1 : 0;
        } else {
          const raw = freqSampler.sample(rng);
          count = Math.max(0, Math.round(raw));
        }

        if (!Number.isSafeInteger(count) || count > MAX_EVENTS_PER_ROUND) return null;

        totalIncidents += count;
        if (!Number.isSafeInteger(totalIncidents) || totalIncidents > MAX_EVENTS_PER_ROUND) return null;
        scenarioCounts.push(count);
      }
    } else {
      // Single-distribution frequency
      const rawFreq = singleFreqSampler(rng);
      const count = Math.max(0, Math.round(rawFreq));
      if (!Number.isSafeInteger(count) || count > MAX_EVENTS_PER_ROUND) return null;
      totalIncidents = count;

    }

    if (needCost) {
      totalEventDraws += totalIncidents;
      if (totalEventDraws > MAX_TOTAL_EVENT_DRAWS) return null;

      if (frequencyScenarioMode) {
        for (let si = 0; si < scenarioSamplers.length; si++) {
          const count = scenarioCounts[si];
          const { costSampler } = scenarioSamplers[si];
          for (let k = 0; k < count; k++) {
            const cost = costScenarioMode
              ? Math.max(0, costSampler(rng))
              : Math.max(0, singleCostSampler(rng));
            if (!Number.isFinite(cost)) return null;
            costsList.push(cost);
            totalLoss += cost;
          }
        }
      } else {
        for (let k = 0; k < totalIncidents; k++) {
          let cost;
          if (costScenarioMode) {
            // Pick a random scenario's cost distribution
            const si = Math.floor(rng() * scenarioSamplers.length);
            cost = Math.max(0, scenarioSamplers[si].costSampler(rng));
          } else {
            cost = Math.max(0, singleCostSampler(rng));
          }
          if (!Number.isFinite(cost)) return null;
          costsList.push(cost);
          totalLoss += cost;
        }
      }
    }

    frequencySamples.push(totalIncidents);
    if (lossSamples) lossSamples.push(totalLoss);
  }

  // Return based on active section
  let samples;
  if (activeSection === 'frequency') {
    samples = frequencySamples;
  } else if (activeSection === 'cost') {
    samples = costsList;
  } else {
    samples = lossSamples;
  }

  if (samples.length === 0) return null;

  // Sort for CDF
  const sorted = Float64Array.from(samples);
  sorted.sort();

  const { x, yCdf } = empiricalCdfArrays(sorted);
  if (x.length === 0) return null;

  return { samples, x, yCdf, isHistogram: true, numRounds: frequencySamples.length };
}
