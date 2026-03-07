<script>
  let { focusPercentile = $bindable(99.5) } = $props();

  const normalized = $derived(Number(focusPercentile).toFixed(1));
  const fullTail = $derived(Number(normalized) >= 100);
</script>

<div class="focus-slider">
  <label class="focus-label" for="focus-slider">
    {#if fullTail}
      Showing full tail
    {:else}
      Showing up to P{normalized}
    {/if}
  </label>
  <input
    id="focus-slider"
    type="range"
    min="95"
    max="100"
    step="0.1"
    bind:value={focusPercentile}
    aria-label="Adjust chart tail focus percentile"
  />
</div>

<style>
  .focus-slider {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
  }

  .focus-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    white-space: nowrap;
    min-width: 11.5rem;
    text-align: right;
  }

  input[type="range"] {
    width: 130px;
    accent-color: var(--color-primary);
  }

  @media (max-width: 480px) {
    .focus-slider {
      width: 100%;
    }

    .focus-label {
      min-width: 0;
      text-align: left;
      flex: 1;
    }

    input[type="range"] {
      width: 120px;
    }
  }
</style>
