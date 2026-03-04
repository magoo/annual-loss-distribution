<script>
  import { interpolatePercentile } from '../math/percentile.js';
  import { formatValue, formatCompact } from '../math/formatting.js';

  let { chartData, useDollars, activeSection, confidenceLevel = $bindable(90) } = $props();
  let copied = $state(false);
  let copyTimeout;

  const lowerP = $derived((100 - confidenceLevel) / 2 / 100);
  const upperP = $derived(1 - lowerP);

  const lowerBound = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, lowerP) : 0
  );
  const median = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, 0.5) : 0
  );
  const upperBound = $derived(
    chartData ? interpolatePercentile(chartData.x, chartData.yCdf, upperP) : 0
  );

  const sectionNoun = $derived(
    activeSection === 'frequency'
      ? 'incidents per year'
      : activeSection === 'cost'
        ? 'incident costs'
        : 'annual losses'
  );

  const summaryText = $derived(
    `There is a ${confidenceLevel}% confidence that ${sectionNoun} fall between ${formatCompact(lowerBound, useDollars)} and ${formatCompact(upperBound, useDollars)}, with a median of ${formatCompact(median, useDollars)}.`
  );

  function copyToClipboard() {
    navigator.clipboard.writeText(summaryText);
    copied = true;
    clearTimeout(copyTimeout);
    copyTimeout = setTimeout(() => { copied = false; }, 2000);
  }
</script>

{#if chartData}
  <div class="ci-card">
    <h3 class="ci-title">Confidence Interval</h3>

    <div class="slider-row">
      <label class="slider-label" for="ci-slider">{confidenceLevel}%</label>
      <input
        id="ci-slider"
        type="range"
        min="50"
        max="95"
        step="1"
        bind:value={confidenceLevel}
      />
    </div>

    <div class="bounds-row">
      <div class="bound">
        <span class="bound-percentile">P{((100 - confidenceLevel) / 2).toFixed(1)}</span>
        <span class="bound-label">Lower Bound</span>
        <span class="bound-value">{formatValue(lowerBound, useDollars)}</span>
      </div>
      <div class="bound">
        <span class="bound-percentile">P50</span>
        <span class="bound-label">Median</span>
        <span class="bound-value">{formatValue(median, useDollars)}</span>
      </div>
      <div class="bound">
        <span class="bound-percentile">P{(100 - (100 - confidenceLevel) / 2).toFixed(1)}</span>
        <span class="bound-label">Upper Bound</span>
        <span class="bound-value">{formatValue(upperBound, useDollars)}</span>
      </div>
    </div>

    <div class="summary-row">
      <p class="summary-text">{summaryText}</p>
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

  .slider-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
  }

  .slider-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-primary);
    min-width: 3.5em;
    text-align: right;
  }

  input[type="range"] {
    flex: 1;
    accent-color: var(--color-primary);
    cursor: pointer;
  }

  .bounds-row {
    display: flex;
    gap: var(--spacing-4);
  }

  .bound {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-1);
  }

  .bound-percentile {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    font-weight: 500;
  }

  .bound-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 500;
  }

  .bound-value {
    font-size: var(--font-size-lg);
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

  @media (max-width: 480px) {
    .bounds-row {
      flex-direction: column;
      gap: var(--spacing-3);
    }
  }
</style>
