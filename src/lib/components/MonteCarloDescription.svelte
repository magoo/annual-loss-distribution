<script>
  import { formatCompact } from '../math/formatting.js';
  import { DIST_CONFIGS } from '../math/distributions.js';

  let { frequencyParams, costParams, frequencyDistType = 'lognormal', costDistType = 'lognormal', frequencyScenarioMode = false, costScenarioMode = false, scenarios = [] } = $props();

  const freqLabel = $derived(DIST_CONFIGS[frequencyDistType]?.label ?? 'Lognormal');
  const costLabel = $derived(DIST_CONFIGS[costDistType]?.label ?? 'Lognormal');

  function paramSummary(params, distType, useDollars) {
    if (distType === 'pert') {
      return `Min: ${formatCompact(params.min, useDollars)}, Mode: ${formatCompact(params.mode, useDollars)}, Max: ${formatCompact(params.max, useDollars)}`;
    }
    return `P50: ${formatCompact(params.p50, useDollars)}, P95: ${formatCompact(params.p95, useDollars)}, P99: ${formatCompact(params.p99, useDollars)}`;
  }
</script>

<div class="mc-description">
  {#if frequencyScenarioMode && costScenarioMode}
    <p>
      Running a 10,000-round scenario-based Monte Carlo simulation across <strong>{scenarios.length} threat scenario{scenarios.length !== 1 ? 's' : ''}</strong>.
      Each round samples incident counts and costs per scenario, then sums them to produce an annual loss distribution.
    </p>
  {:else if frequencyScenarioMode}
    <p>
      Running a 10,000-round hybrid Monte Carlo simulation. <strong>Frequency</strong> is sampled from <strong>{scenarios.length} threat scenario{scenarios.length !== 1 ? 's' : ''}</strong>,
      while <strong>Cost</strong> uses a {costLabel} distribution ({paramSummary(costParams, costDistType, true)}).
    </p>
  {:else if costScenarioMode}
    <p>
      Running a 10,000-round hybrid Monte Carlo simulation. <strong>Frequency</strong> uses a {freqLabel} distribution ({paramSummary(frequencyParams, frequencyDistType, false)} incidents),
      while <strong>Cost</strong> is sampled from <strong>{scenarios.length} threat scenario{scenarios.length !== 1 ? 's' : ''}</strong>.
    </p>
  {:else}
    <p>
      Running a 100,000-sample Monte Carlo simulation by multiplying the <strong>Frequency</strong> ({freqLabel}: {paramSummary(frequencyParams, frequencyDistType, false)} incidents)
      by the <strong>Cost</strong> ({costLabel}: {paramSummary(costParams, costDistType, true)})
      to produce an annual loss distribution.
      {#if frequencyDistType !== 'pert' || costDistType !== 'pert'}
        P50 is the median — half of outcomes fall below this value. P95 means only 5% of outcomes exceed it. P99 represents a 1-in-100 extreme scenario.
      {/if}
    </p>
  {/if}
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
