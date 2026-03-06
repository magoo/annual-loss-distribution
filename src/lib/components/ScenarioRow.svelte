<script>
  import ParameterField from './ParameterField.svelte';
  import ScenarioMiniChart from './ScenarioMiniChart.svelte';
  import { validate } from '../math/validation.js';
  import { SCENARIO_FREQ_METHODS, SCENARIO_FREQ_CONFIGS, SCENARIO_COST_CONFIGS, DIST_TYPES } from '../math/distributions.js';

  let {
    scenario,
    activeSection,
    showMiniChart = false,
    onremove,
    onnamchange,
    onfreqmethod,
    onfreqparam,
    oncostdisttype,
    oncostparam,
  } = $props();

  const isFrequency = $derived(activeSection === 'frequency');
  const miniChartDistType = $derived(isFrequency ? scenario.frequencyMethod : scenario.costDistType);
  const miniChartParams = $derived(isFrequency ? scenario.frequencyParams : scenario.costParams);

  // Frequency tab: method config and fields
  const freqConfig = $derived(SCENARIO_FREQ_CONFIGS[scenario.frequencyMethod]);
  const freqFields = $derived(freqConfig?.fields ?? []);
  const freqErrors = $derived(validate('frequency', scenario.frequencyParams, scenario.frequencyMethod));

  // Cost tab: dist config and fields
  const costConfig = $derived(SCENARIO_COST_CONFIGS[scenario.costDistType]);
  const costFields = $derived(costConfig?.fields ?? []);
  const costErrors = $derived(validate('cost', scenario.costParams, scenario.costDistType));
</script>

<div class="scenario-row">
  <div class="scenario-header">
    <input
      type="text"
      class="name-input"
      value={scenario.name}
      oninput={(e) => onnamchange(e.target.value)}
      placeholder="Scenario name"
    />

    {#if isFrequency}
      <div class="method-selector">
        {#each SCENARIO_FREQ_METHODS as method}
          <button
            class="method-btn"
            class:active={scenario.frequencyMethod === method}
            onclick={() => onfreqmethod(method)}
          >
            {SCENARIO_FREQ_CONFIGS[method].label}
          </button>
        {/each}
      </div>
    {:else}
      <div class="method-selector">
        {#each DIST_TYPES as dt}
          <button
            class="method-btn"
            class:active={scenario.costDistType === dt}
            onclick={() => oncostdisttype(dt)}
          >
            {SCENARIO_COST_CONFIGS[dt].label}
          </button>
        {/each}
      </div>
    {/if}

    <button
      class="remove-btn"
      onclick={onremove}
      title="Remove scenario"
      aria-label="Remove scenario"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </button>
  </div>

  {#if showMiniChart}
    <div class="mini-chart-row">
      <ScenarioMiniChart
        section={isFrequency ? 'frequency' : 'cost'}
        distType={miniChartDistType}
        params={miniChartParams}
      />
    </div>
  {/if}

  <div class="fields-row">
    {#if isFrequency}
      {#each freqFields as field (field.key)}
        <ParameterField
          label={field.label}
          help={field.help}
          value={scenario.frequencyParams[field.key]}
          error={freqErrors[field.key]}
          onchange={(v) => onfreqparam(field.key, v)}
        />
      {/each}
    {:else}
      {#each costFields as field (field.key)}
        <ParameterField
          label={field.label}
          help={field.help}
          value={scenario.costParams[field.key]}
          error={costErrors[field.key]}
          onchange={(v) => oncostparam(field.key, v)}
        />
      {/each}
    {/if}
  </div>
</div>

<style>
  .scenario-row {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    padding: var(--spacing-4);
    border: 1.5px solid var(--color-border);
  }

  .scenario-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    margin-bottom: var(--spacing-3);
    flex-wrap: wrap;
  }

  .name-input {
    flex: 1;
    min-width: 120px;
    font-weight: 600;
  }

  .method-selector {
    display: flex;
    gap: 1px;
    background: var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .method-btn {
    padding: var(--spacing-1) var(--spacing-2);
    font-size: var(--font-size-xs);
    font-weight: 500;
    background: var(--color-surface);
    color: var(--color-text-secondary);
    border: none;
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .method-btn.active {
    background: var(--color-primary);
    color: var(--color-surface);
  }

  .method-btn:hover:not(.active) {
    background: var(--color-bg);
  }

  .remove-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: transparent;
    border-radius: var(--radius-sm);
    color: var(--color-text-tertiary);
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }

  .remove-btn:hover {
    background: var(--color-error-light);
    color: var(--color-error);
  }

  .mini-chart-row {
    margin-bottom: var(--spacing-2);
  }

  .fields-row {
    display: flex;
    gap: var(--spacing-4);
  }

  @media (max-width: 480px) {
    .fields-row {
      flex-direction: column;
    }
  }
</style>
