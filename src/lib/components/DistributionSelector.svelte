<script>
  import { SECTIONS, SECTION_TYPES } from '../math/distributions.js';

  let { selected, onselect } = $props();
</script>

<div class="tabs" role="tablist">
  {#each SECTION_TYPES as type}
    <button
      class="tab"
      class:active={selected === type}
      role="tab"
      aria-selected={selected === type}
      onclick={() => onselect(type)}
    >
      {SECTIONS[type].label}
    </button>
  {/each}
</div>

<style>
  .tabs {
    display: flex;
    gap: 2px;
    background: var(--color-bg);
    border-radius: var(--radius-lg);
    padding: 3px;
  }

  .tab {
    flex: 1;
    padding: var(--spacing-2) var(--spacing-4);
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--color-text-secondary);
    background: transparent;
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
  }

  .tab:hover {
    color: var(--color-text);
  }

  .tab.active {
    background: var(--color-surface);
    color: var(--color-primary);
    box-shadow: var(--shadow-sm);
  }
</style>
