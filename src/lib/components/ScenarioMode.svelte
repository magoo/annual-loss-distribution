<script>
  import ScenarioRow from './ScenarioRow.svelte';

  let {
    scenarios,
    activeSection,
    onadd,
    onremove,
    onnamchange,
    onfreqmethod,
    onfreqparam,
    oncostdisttype,
    oncostparam,
  } = $props();

  let showMiniCharts = $state(false);
</script>

<div class="scenario-section">
  <div class="toolbar">
    <button
      class="preview-toggle"
      class:active={showMiniCharts}
      onclick={() => showMiniCharts = !showMiniCharts}
      title={showMiniCharts ? 'Hide previews' : 'Show previews'}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 3C4.5 3 1.7 5.3 1 8c.7 2.7 3.5 5 7 5s6.3-2.3 7-5c-.7-2.7-3.5-5-7-5Z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.3"/>
      </svg>
      Previews
    </button>
  </div>

  <div class="scenarios">
    {#each scenarios as scenario (scenario.id)}
      <ScenarioRow
        {scenario}
        {activeSection}
        showMiniChart={showMiniCharts}
        onremove={() => onremove(scenario.id)}
        onnamchange={(name) => onnamchange(scenario.id, name)}
        onfreqmethod={(method) => onfreqmethod(scenario.id, method)}
        onfreqparam={(key, val) => onfreqparam(scenario.id, key, val)}
        oncostdisttype={(dt) => oncostdisttype(scenario.id, dt)}
        oncostparam={(key, val) => oncostparam(scenario.id, key, val)}
      />
    {/each}
  </div>

  <button class="add-btn" onclick={onadd}>
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    Add Scenario
  </button>
</div>

<style>
  .scenario-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .toolbar {
    display: flex;
    justify-content: flex-end;
  }

  .preview-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-1);
    padding: var(--spacing-1) var(--spacing-2);
    font-size: var(--font-size-xs);
    font-weight: 500;
    color: var(--color-text-tertiary);
    background: transparent;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .preview-toggle:hover {
    color: var(--color-text-secondary);
    background: var(--color-bg);
  }

  .preview-toggle.active {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }

  .scenarios {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .add-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2);
    width: 100%;
    padding: var(--spacing-3);
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-primary);
    background: var(--color-primary-light);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
  }

  .add-btn:hover {
    background: var(--color-primary);
    color: var(--color-surface);
  }
</style>
