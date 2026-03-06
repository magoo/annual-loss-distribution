<script>
  let { active, ontoggle } = $props();
</script>

<div class="scenario-toggle">
  <span class="toggle-label">Scenario Mode</span>
  <button
    class="toggle-switch"
    class:active
    onclick={ontoggle}
    role="switch"
    aria-checked={active}
    aria-label="Toggle scenario mode"
  >
    <span class="toggle-knob"></span>
  </button>
</div>

<style>
  .scenario-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
  }

  .toggle-label {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .toggle-switch {
    position: relative;
    width: 40px;
    height: 22px;
    background: var(--color-border);
    border-radius: 11px;
    padding: 0;
    cursor: pointer;
    transition: background var(--transition-fast);
  }

  .toggle-switch.active {
    background: var(--color-primary);
  }

  .toggle-knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    background: var(--color-surface);
    border-radius: 50%;
    transition: transform var(--transition-fast);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  }

  .toggle-switch.active .toggle-knob {
    transform: translateX(18px);
  }
</style>
