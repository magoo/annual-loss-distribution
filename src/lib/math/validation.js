/**
 * Validation rules dispatched by distribution type.
 */

export function validateQuantiles(params) {
  const { p50, p95, p99 } = params;
  const errors = {};

  if (p50 == null || isNaN(p50)) {
    errors.p50 = 'Required';
  } else if (p50 <= 0) {
    errors.p50 = 'Must be greater than 0';
  }

  if (p95 == null || isNaN(p95)) {
    errors.p95 = 'Required';
  } else if (p95 <= 0) {
    errors.p95 = 'Must be greater than 0';
  }

  if (p99 == null || isNaN(p99)) {
    errors.p99 = 'Required';
  } else if (p99 <= 0) {
    errors.p99 = 'Must be greater than 0';
  }

  if (!errors.p50 && !errors.p95) {
    if (p95 <= p50) {
      errors.p95 = 'P95 must be greater than P50';
    }
  }

  if (!errors.p95 && !errors.p99) {
    if (p99 <= p95) {
      errors.p99 = 'P99 must be greater than P95';
    }
  }

  return errors;
}

export function validatePert(params) {
  const { min, mode, max } = params;
  const errors = {};

  if (min == null || isNaN(min)) {
    errors.min = 'Required';
  } else if (min < 0) {
    errors.min = 'Must be 0 or greater';
  }

  if (mode == null || isNaN(mode)) {
    errors.mode = 'Required';
  } else if (mode < 0) {
    errors.mode = 'Must be 0 or greater';
  }

  if (max == null || isNaN(max)) {
    errors.max = 'Required';
  } else if (max <= 0) {
    errors.max = 'Must be greater than 0';
  }

  if (!errors.min && !errors.mode) {
    if (mode <= min) {
      errors.mode = 'Must be greater than minimum';
    }
  }

  if (!errors.mode && !errors.max) {
    if (max <= mode) {
      errors.max = 'Must be greater than most likely';
    }
  }

  return errors;
}

export function validate(section, params, distType) {
  if (section === 'loss') return {};

  switch (distType) {
    case 'pert':
      return validatePert(params);
    case 'lognormal':
    case 'pareto':
      return validateQuantiles(params);
    default:
      return validateQuantiles(params);
  }
}
