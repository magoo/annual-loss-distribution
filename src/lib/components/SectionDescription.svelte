<script>
  import { getSectionDescription } from './section-description.js';

  let {
    activeSection,
    frequencyParams = {},
    costParams = {},
    frequencyDistType = 'lognormal',
    costDistType = 'lognormal',
    frequencyScenarioMode = false,
    costScenarioMode = false,
    scenarios = [],
    chartData = null,
    confidenceLevel = 90,
    frequencyPanelActive = false,
    costPanelActive = false,
    frequencyPanelists = [],
    costPanelists = [],
  } = $props();

  let copied = $state(false);
  let copyTimeout;

  const description = $derived.by(() => getSectionDescription({
    activeSection,
    frequencyParams,
    costParams,
    frequencyDistType,
    costDistType,
    frequencyScenarioMode,
    costScenarioMode,
    scenarios,
    chartData,
    confidenceLevel,
    frequencyPanelActive,
    costPanelActive,
    frequencyPanelists,
    costPanelists,
  }));

  function copyToClipboard() {
    if (!description.copyText) return;

    navigator.clipboard.writeText(description.copyText);
    copied = true;
    clearTimeout(copyTimeout);
    copyTimeout = setTimeout(() => { copied = false; }, 2000);
  }
</script>

<div class="section-description" role="note" aria-live="polite">
  {#if description.mode === 'executive'}
    <div class="summary-header">
      <h3 class="summary-title">{description.title}</h3>
      <button class="copy-btn" onclick={copyToClipboard} title="Copy summary">
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

    <div class="summary-lead">
      <p class="summary-intro">{description.intro}</p>

      {#if description.confidenceNarrative?.length}
        <div class="confidence-narrative">
          {#each description.confidenceNarrative as sentence}
            <p>{sentence}</p>
          {/each}
        </div>
      {/if}
    </div>

    <div class="summary-groups">
      {#each description.sections as section (section.title)}
        <section class="summary-group">
          <h4>{section.title}</h4>
          <ul>
            {#each section.bullets as bullet}
              <li>{bullet}</li>
            {/each}
          </ul>
        </section>
      {/each}
    </div>
  {:else}
    <p>{description.text}</p>
  {/if}
</div>

<style>
  .section-description p {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
    margin: 0;
  }

  .summary-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-3);
    margin-bottom: 0;
  }

  .summary-title {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  .summary-lead {
    display: grid;
    gap: var(--spacing-4);
    margin: var(--spacing-2) 0 var(--spacing-3);
  }

  .section-description p.summary-intro {
    margin: 0;
  }

  .confidence-narrative {
    display: grid;
    gap: var(--spacing-1);
  }

  .confidence-narrative p {
    color: var(--color-text-secondary);
  }

  .summary-groups {
    display: grid;
    gap: var(--spacing-3);
  }

  .summary-group h4 {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text);
    margin: 0 0 var(--spacing-1);
  }

  .summary-group ul {
    margin: 0;
    padding-left: 1.1rem;
    display: grid;
    gap: 2px;
  }

  .summary-group li {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.5;
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
