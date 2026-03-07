<script>
  import { DIST_CONFIGS, DIST_TYPES } from '../math/distributions.js';

  let {
    selected,
    scenarioActive = false,
    onselectdist,
    onselectscenario,
  } = $props();
</script>

<div class="dist-type-toggle">
  {#each DIST_TYPES as dt (dt)}
    <button
      class="toggle-btn"
      class:active={!scenarioActive && selected === dt}
      onclick={() => onselectdist(dt)}
    >
      {DIST_CONFIGS[dt].label}
    </button>
  {/each}

  <button
    class="toggle-btn"
    class:active={scenarioActive}
    onclick={onselectscenario}
  >
    Scenario Mode
  </button>
</div>

<style>
  .dist-type-toggle {
    display: flex;
    gap: 2px;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    padding: 2px;
    width: fit-content;
  }

  .toggle-btn {
    padding: var(--spacing-1) var(--spacing-4);
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-text-secondary);
    background: transparent;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
    letter-spacing: 0.02em;
  }

  .toggle-btn:hover {
    color: var(--color-text);
  }

  .toggle-btn.active {
    background: var(--color-surface);
    color: var(--color-primary);
    box-shadow: var(--shadow-sm);
  }
</style>
