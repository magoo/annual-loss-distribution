import { computeLognormal } from './lognormal.js';
import { computePert } from './pert.js';
import { computePareto } from './pareto.js';
import { computeAnnualLoss } from './monte-carlo.js';

/**
 * Section identity: label and formatting.
 */
export const SECTIONS = {
  frequency: { label: 'Frequency', useDollars: false },
  cost: { label: 'Cost', useDollars: true },
  loss: { label: 'Calculate', useDollars: true },
};

export const SECTION_TYPES = ['frequency', 'cost', 'loss'];

export const DIST_TYPES = ['lognormal', 'pert', 'pareto'];

/**
 * Distribution configs keyed by dist type, then section.
 * Each provides defaults, fields, and guidance text.
 */
export const DIST_CONFIGS = {
  lognormal: {
    label: 'Lognormal',
    frequency: {
      defaults: { p50: 1, p95: 10, p99: 50 },
      fields: [
        { key: 'p50', label: 'P50 Median', help: '50th percentile of incidents per year' },
        { key: 'p95', label: 'P95', help: '95th percentile of incidents per year' },
        { key: 'p99', label: 'P99', help: '99th percentile of incidents per year' },
      ],
      guidance: 'In a typical year, how many times do you expect this incident to occur? (P50) In a particularly bad year — one that only happens 1 in 20 times — how many would you expect? (P95) In an extreme year — 1 in 100 — how many? (P99)',
    },
    cost: {
      defaults: { p50: 50000, p95: 500000, p99: 2000000 },
      fields: [
        { key: 'p50', label: 'P50 Median ($)', help: '50th percentile of incident cost' },
        { key: 'p95', label: 'P95 ($)', help: '95th percentile of incident cost' },
        { key: 'p99', label: 'P99 ($)', help: '99th percentile of incident cost' },
      ],
      guidance: 'When this incident occurs, what\'s the typical cost? (P50) In a worst-case scenario — 1 in 20 times — what would it cost? (P95) In an extreme case — 1 in 100 — what\'s the maximum plausible cost? (P99)',
    },
  },
  pert: {
    label: 'PERT',
    frequency: {
      defaults: { min: 0, mode: 1, max: 10 },
      fields: [
        { key: 'min', label: 'Minimum', help: 'Best-case incidents per year' },
        { key: 'mode', label: 'Most Likely', help: 'Most common incidents per year' },
        { key: 'max', label: 'Maximum', help: 'Worst-case incidents per year' },
      ],
      guidance: 'What is the fewest incidents you\'d expect in a year? (Min) What is the most common number? (Most Likely) What is the absolute worst case? (Max)',
    },
    cost: {
      defaults: { min: 1000, mode: 50000, max: 500000 },
      fields: [
        { key: 'min', label: 'Minimum ($)', help: 'Best-case incident cost' },
        { key: 'mode', label: 'Most Likely ($)', help: 'Most common incident cost' },
        { key: 'max', label: 'Maximum ($)', help: 'Worst-case incident cost' },
      ],
      guidance: 'What is the lowest plausible cost per incident? (Min) What is the most common cost? (Most Likely) What is the absolute worst-case cost? (Max)',
    },
  },
  pareto: {
    label: 'Pareto',
    frequency: {
      defaults: { p50: 1, p95: 10, p99: 50 },
      fields: [
        { key: 'p50', label: 'P50 Median', help: '50th percentile of incidents per year' },
        { key: 'p95', label: 'P95', help: '95th percentile of incidents per year' },
        { key: 'p99', label: 'P99', help: '99th percentile of incidents per year' },
      ],
      guidance: 'In a typical year, how many incidents? (P50) In a bad year — 1 in 20? (P95) In an extreme year — 1 in 100? (P99)',
    },
    cost: {
      defaults: { p50: 50000, p95: 500000, p99: 2000000 },
      fields: [
        { key: 'p50', label: 'P50 Median ($)', help: '50th percentile of incident cost' },
        { key: 'p95', label: 'P95 ($)', help: '95th percentile of incident cost' },
        { key: 'p99', label: 'P99 ($)', help: '99th percentile of incident cost' },
      ],
      guidance: 'What is the typical incident cost? (P50) A bad scenario — 1 in 20? (P95) An extreme scenario — 1 in 100? (P99)',
    },
  },
};

/**
 * Scenario frequency methods (includes 'odds' in addition to standard dist types).
 */
export const SCENARIO_FREQ_METHODS = ['odds', 'lognormal', 'pert', 'pareto'];

export const SCENARIO_FREQ_CONFIGS = {
  odds: {
    label: 'Odds',
    defaults: { odds: 10 },
    fields: [{ key: 'odds', label: '1 in N years', help: 'Chance per year (e.g. 10 = once every 10 years)' }],
  },
  lognormal: {
    label: 'Lognormal',
    defaults: { ...DIST_CONFIGS.lognormal.frequency.defaults },
    fields: DIST_CONFIGS.lognormal.frequency.fields,
  },
  pert: {
    label: 'PERT',
    defaults: { ...DIST_CONFIGS.pert.frequency.defaults },
    fields: DIST_CONFIGS.pert.frequency.fields,
  },
  pareto: {
    label: 'Pareto',
    defaults: { ...DIST_CONFIGS.pareto.frequency.defaults },
    fields: DIST_CONFIGS.pareto.frequency.fields,
  },
};

export const SCENARIO_COST_CONFIGS = {
  lognormal: {
    label: 'Lognormal',
    defaults: { ...DIST_CONFIGS.lognormal.cost.defaults },
    fields: DIST_CONFIGS.lognormal.cost.fields,
  },
  pert: {
    label: 'PERT',
    defaults: { ...DIST_CONFIGS.pert.cost.defaults },
    fields: DIST_CONFIGS.pert.cost.fields,
  },
  pareto: {
    label: 'Pareto',
    defaults: { ...DIST_CONFIGS.pareto.cost.defaults },
    fields: DIST_CONFIGS.pareto.cost.fields,
  },
};

export const DEFAULT_SCENARIOS = [
  { name: 'Product Exploit', frequencyMethod: 'odds', frequencyParams: { odds: 3 }, costDistType: 'lognormal', costParams: { p50: 100000, p95: 1000000, p99: 5000000 } },
  { name: 'Malicious Insider', frequencyMethod: 'odds', frequencyParams: { odds: 10 }, costDistType: 'lognormal', costParams: { p50: 200000, p95: 2000000, p99: 10000000 } },
  { name: 'DDoS', frequencyMethod: 'odds', frequencyParams: { odds: 2 }, costDistType: 'lognormal', costParams: { p50: 20000, p95: 200000, p99: 1000000 } },
  { name: 'Supply Chain', frequencyMethod: 'odds', frequencyParams: { odds: 20 }, costDistType: 'lognormal', costParams: { p50: 200000, p95: 2000000, p99: 10000000 } },
  { name: 'Credential Leak / Theft', frequencyMethod: 'odds', frequencyParams: { odds: 2 }, costDistType: 'lognormal', costParams: { p50: 30000, p95: 300000, p99: 1500000 } },
  { name: 'Compromised Software Download', frequencyMethod: 'odds', frequencyParams: { odds: 15 }, costDistType: 'lognormal', costParams: { p50: 50000, p95: 500000, p99: 3000000 } },
  { name: 'Social Engineering', frequencyMethod: 'odds', frequencyParams: { odds: 3 }, costDistType: 'lognormal', costParams: { p50: 25000, p95: 250000, p99: 1000000 } },
  { name: 'Zero Day Targeting Employee', frequencyMethod: 'odds', frequencyParams: { odds: 50 }, costDistType: 'lognormal', costParams: { p50: 100000, p95: 1000000, p99: 5000000 } },
  { name: 'Exposed and Exploited Service', frequencyMethod: 'odds', frequencyParams: { odds: 5 }, costDistType: 'lognormal', costParams: { p50: 50000, p95: 500000, p99: 2000000 } },
  { name: 'Ransomware', frequencyMethod: 'odds', frequencyParams: { odds: 5 }, costDistType: 'lognormal', costParams: { p50: 100000, p95: 1000000, p99: 10000000 } },
];

/**
 * Get the distribution config for a given dist type and section.
 */
export function getDistConfig(distType, section) {
  return DIST_CONFIGS[distType]?.[section] ?? null;
}

/**
 * Unified entry point for computing distribution data.
 * @param {'frequency' | 'cost' | 'loss'} section
 * @param {object} params - Section-specific parameters
 * @param {object} [allParams] - All params (needed for loss MC simulation)
 * @param {string} [distType] - Distribution type (lognormal, pert, pareto)
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeDistribution(section, params, allParams, distType) {
  if (section === 'loss') {
    return computeAnnualLoss(allParams);
  }

  switch (distType) {
    case 'lognormal':
      return computeLognormal(params);
    case 'pert':
      return computePert(params);
    case 'pareto':
      return computePareto(params);
    default:
      return computeLognormal(params);
  }
}
