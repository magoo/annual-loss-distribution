/**
 * Validation rules for each section type.
 * Each returns an object mapping field names to error messages (or null if valid).
 */

export function validateLognormal(params) {
  const { p50, p95 } = params;
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

  if (!Object.keys(errors).length) {
    if (p95 <= p50) {
      errors.p95 = 'P95 must be greater than P50';
    }
  }

  return errors;
}

export function validate(section, params) {
  switch (section) {
    case 'frequency':
    case 'cost':
      return validateLognormal(params);
    case 'loss':
      return {};
    default:
      return {};
  }
}
