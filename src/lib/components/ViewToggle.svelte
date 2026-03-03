<script>
  let { view, onchange } = $props();
</script>

<div class="view-toggle">
  <button
    class="toggle-btn"
    class:active={view === 'pdf'}
    onclick={() => onchange('pdf')}
  >
    PDF
  </button>
  <button
    class="toggle-btn"
    class:active={view === 'cdf'}
    onclick={() => onchange('cdf')}
  >
    CDF
  </button>
</div>

<style>
  .view-toggle {
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
