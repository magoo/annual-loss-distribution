import { fitLognormal } from './lognormal.js';
import { fitPareto } from './pareto.js';
import { fitPert } from './pert.js';

/**
 * Return the theoretical mean for a supported distribution. Pareto models
 * with shape <= 1 intentionally return Infinity because their mean is not
 * finite and they cannot define a bounded compound-frequency workload.
 */
export function distributionMean(distType, params) {
  if (!params) return NaN;

  switch (distType) {
    case 'lognormal': {
      const { mu, sigma } = fitLognormal(params.p50, params.p95);
      return Math.exp(mu + (sigma ** 2) / 2);
    }
    case 'pert': {
      const { alpha, beta, min, max } = fitPert(params.min, params.mode, params.max);
      return min + (max - min) * (alpha / (alpha + beta));
    }
    case 'pareto': {
      const { scale, shape } = fitPareto(params.p50, params.p95);
      return shape > 1 ? (shape * scale) / (shape - 1) : Infinity;
    }
    default:
      return NaN;
  }
}

/**
 * Estimate event-draw work before a simulation begins. For Pareto frequency
 * models without a finite theoretical mean, P95 provides a stable planning
 * proxy; the simulator's independent hard ceiling still rejects an unusually
 * expensive deterministic draw set in full rather than trimming its tail.
 */
export function frequencyWorkRate(distType, params) {
  const mean = distributionMean(distType, params);
  if (Number.isFinite(mean)) return mean;
  if (distType === 'pareto' && Number.isFinite(params?.p95) && params.p95 > 0) {
    return params.p95;
  }
  return NaN;
}
