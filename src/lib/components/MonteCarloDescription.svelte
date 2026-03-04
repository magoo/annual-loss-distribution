<script>
  import { formatCompact } from '../math/formatting.js';

  let { frequencyParams, costParams } = $props();
</script>

<div class="mc-description">
  <p>
    Running a 10,000-sample Monte Carlo simulation by multiplying the <strong>Frequency</strong> distribution
    (P50: {formatCompact(frequencyParams.p50, false)} incidents, P95: {formatCompact(frequencyParams.p95, false)} incidents)
    by the <strong>Cost</strong> distribution
    (P50: {formatCompact(costParams.p50, true)}, P95: {formatCompact(costParams.p95, true)})
    to produce an annual loss distribution.
    P50 is the median — half of outcomes fall below this value. P95 means only 5% of outcomes exceed it, representing a plausible worst case.
  </p>
</div>

<style>
  .mc-description {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    padding: var(--spacing-4) var(--spacing-5);
  }

  p {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
  }
</style>
