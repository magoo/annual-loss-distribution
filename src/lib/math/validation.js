/**
 * Validation rules dispatched by distribution type.
 */

function isMissingNumber(value) {
  return value == null || Number.isNaN(value);
}

function isNonFinite(value) {
  return !Number.isFinite(value);
}

export function validateQuantiles(params) {
  const { p50, p95, p99 } = params;
  const errors = {};

  if (isMissingNumber(p50)) {
    errors.p50 = 'Required';
  } else if (isNonFinite(p50)) {
    errors.p50 = 'Must be a finite number';
  } else if (p50 <= 0) {
    errors.p50 = 'Must be greater than 0';
  }

  if (isMissingNumber(p95)) {
    errors.p95 = 'Required';
  } else if (isNonFinite(p95)) {
    errors.p95 = 'Must be a finite number';
  } else if (p95 <= 0) {
    errors.p95 = 'Must be greater than 0';
  }

  if (isMissingNumber(p99)) {
    errors.p99 = 'Required';
  } else if (isNonFinite(p99)) {
    errors.p99 = 'Must be a finite number';
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

  if (isMissingNumber(min)) {
    errors.min = 'Required';
  } else if (isNonFinite(min)) {
    errors.min = 'Must be a finite number';
  } else if (min < 0) {
    errors.min = 'Must be 0 or greater';
  }

  if (isMissingNumber(mode)) {
    errors.mode = 'Required';
  } else if (isNonFinite(mode)) {
    errors.mode = 'Must be a finite number';
  } else if (mode < 0) {
    errors.mode = 'Must be 0 or greater';
  }

  if (isMissingNumber(max)) {
    errors.max = 'Required';
  } else if (isNonFinite(max)) {
    errors.max = 'Must be a finite number';
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

export function validateOdds(params) {
  const { odds } = params;
  const errors = {};

  if (isMissingNumber(odds)) {
    errors.odds = 'Required';
  } else if (isNonFinite(odds)) {
    errors.odds = 'Must be a finite number';
  } else if (odds <= 0) {
    errors.odds = 'Must be greater than 0';
  }

  return errors;
}

export function validate(section, params, distType) {
  if (section === 'loss') return {};

  if (distType === 'odds') {
    return validateOdds(params);
  }

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
