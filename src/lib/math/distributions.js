import { computeLognormal } from './lognormal.js';
import { computeAnnualLoss } from './monte-carlo.js';

/**
 * Section metadata: labels, default parameters, field definitions, and formatting.
 */
export const SECTIONS = {
  frequency: {
    label: 'Frequency',
    useDollars: false,
    defaults: { p50: 1, p95: 10 },
    fields: [
      { key: 'p50', label: 'P50 Median', help: '50th percentile of incidents per year' },
      { key: 'p95', label: 'P95', help: '95th percentile of incidents per year' },
    ],
    guidance: 'In a typical year, how many times do you expect this incident to occur? (P50) In a particularly bad year — one that only happens 1 in 20 times — how many would you expect? (P95)',
  },
  cost: {
    label: 'Cost',
    useDollars: true,
    defaults: { p50: 50000, p95: 500000 },
    fields: [
      { key: 'p50', label: 'P50 Median ($)', help: '50th percentile of incident cost' },
      { key: 'p95', label: 'P95 ($)', help: '95th percentile of incident cost' },
    ],
    guidance: 'When this incident occurs, what\'s the typical cost? (P50) In a worst-case scenario — one that only happens 1 in 20 times — what would the cost be? (P95)',
  },
  loss: {
    label: 'Annual Loss',
    useDollars: true,
    defaults: {},
    fields: [],
  },
};

export const SECTION_TYPES = ['frequency', 'cost', 'loss'];

/**
 * Unified entry point for computing distribution data.
 * @param {'frequency' | 'cost' | 'loss'} section
 * @param {object} params - Section-specific parameters
 * @param {object} [allParams] - All params (needed for loss MC simulation)
 * @returns {{ x: number[], yPdf: number[], yCdf: number[] } | null}
 */
export function computeDistribution(section, params, allParams) {
  switch (section) {
    case 'frequency':
    case 'cost':
      return computeLognormal(params);
    case 'loss':
      return computeAnnualLoss(allParams);
    default:
      return null;
  }
}
