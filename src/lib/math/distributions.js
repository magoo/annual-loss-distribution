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
