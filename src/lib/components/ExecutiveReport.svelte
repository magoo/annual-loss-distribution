<script>
  import { interpolatePercentile } from '../math/percentile.js';
  import { formatCompact } from '../math/formatting.js';
  import { DIST_CONFIGS } from '../math/distributions.js';

  let {
    chartData,
    effectiveFrequencyParams,
    effectiveCostParams,
    frequencyPanelists,
    costPanelists,
    frequencyPanelActive,
    costPanelActive,
    frequencyDistType = 'lognormal',
    costDistType = 'lognormal',
    confidenceLevel,
  } = $props();

  let copied = $state(false);
  let copyTimeout;

  const freqLabel = $derived(DIST_CONFIGS[frequencyDistType]?.label ?? 'Lognormal');
  const costDistLabel = $derived(DIST_CONFIGS[costDistType]?.label ?? 'Lognormal');

  const lowerP = $derived((100 - confidenceLevel) / 2 / 100);
  const upperP = $derived(1 - lowerP);

  const median = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, 0.5) : 0
  );
  const lowerBound = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, lowerP) : 0
  );
  const upperBound = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, upperP) : 0
  );

  function paramDesc(params, distType, useDollars) {
    if (distType === 'pert') {
      return `min ${formatCompact(params.min, useDollars)}, mode ${formatCompact(params.mode, useDollars)}, max ${formatCompact(params.max, useDollars)}`;
    }
    return `P50: ${formatCompact(params.p50, useDollars)}, P95: ${formatCompact(params.p95, useDollars)}, P99: ${formatCompact(params.p99, useDollars)}`;
  }

  const frequencySentence = $derived.by(() => {
    const desc = paramDesc(effectiveFrequencyParams, frequencyDistType, false);

    if (frequencyPanelActive) {
      const names = frequencyPanelists.map((p) => p.name).join(', ');
      return `A panel of ${frequencyPanelists.length} experts (${names}) estimated incident frequency using a ${freqLabel} distribution (${desc} incidents).`;
    }
    return `Incident frequency is modeled as a ${freqLabel} distribution (${desc} incidents).`;
  });

  const costSentence = $derived.by(() => {
    const desc = paramDesc(effectiveCostParams, costDistType, true);

    if (costPanelActive) {
      const names = costPanelists.map((p) => p.name).join(', ');
      return `A panel of ${costPanelists.length} experts (${names}) estimated incident cost using a ${costDistLabel} distribution (${desc}).`;
    }
    return `Incident cost is modeled as a ${costDistLabel} distribution (${desc}).`;
  });

  const lossSentence = $derived(
    `A Monte Carlo simulation of 100,000 samples produces an annual loss distribution with a median of ${formatCompact(median, true)}.`
  );

  const ciSentence = $derived(
    `There is ${confidenceLevel}% confidence that annual losses fall between ${formatCompact(lowerBound, true)} and ${formatCompact(upperBound, true)}.`
  );

  const reportText = $derived(
    [frequencySentence, costSentence, lossSentence, ciSentence].filter(Boolean).join(' ')
  );

  function copyToClipboard() {
    navigator.clipboard.writeText(reportText);
    copied = true;
    clearTimeout(copyTimeout);
    copyTimeout = setTimeout(() => { copied = false; }, 2000);
  }
</script>

{#if chartData}
  <div class="ci-card">
    <h3 class="ci-title">Executive Report</h3>

    <div class="summary-row">
      <p class="summary-text">{reportText}</p>
      <button class="copy-btn" onclick={copyToClipboard} title="Copy to clipboard">
        {#if copied}
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        {:else}
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" stroke-width="1.5"/>
          </svg>
        {/if}
      </button>
    </div>
  </div>
{/if}

<style>
  .ci-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    padding: var(--spacing-5);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .ci-title {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  .summary-row {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-3);
    background: var(--color-bg);
    border-radius: var(--radius-md);
    padding: var(--spacing-3) var(--spacing-4);
  }

  .summary-text {
    flex: 1;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
  }

  .copy-btn {
    flex-shrink: 0;
    background: none;
    color: var(--color-text-tertiary);
    padding: var(--spacing-1);
    border-radius: var(--radius-sm);
    transition: color var(--transition-fast);
  }

  .copy-btn:hover {
    color: var(--color-primary);
  }
</style>
