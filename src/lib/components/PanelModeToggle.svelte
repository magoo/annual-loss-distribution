<script>
  let { active, ontoggle } = $props();
</script>

<div class="panel-toggle">
  <span class="toggle-label">Panel Mode</span>
  <button
    class="switch"
    class:active
    role="switch"
    aria-checked={active}
    aria-label="Toggle panel mode"
    onclick={ontoggle}
  >
    <span class="switch-thumb"></span>
  </button>
</div>

<style>
  .panel-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
  }

  .toggle-label {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .switch {
    position: relative;
    width: 44px;
    height: 24px;
    background: var(--color-border);
    border-radius: 12px;
    padding: 0;
    transition: background var(--transition-fast);
  }

  .switch.active {
    background: var(--color-primary);
  }

  .switch-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: var(--color-surface);
    border-radius: 50%;
    box-shadow: var(--shadow-sm);
    transition: transform var(--transition-fast);
  }

  .switch.active .switch-thumb {
    transform: translateX(20px);
  }
</style>
