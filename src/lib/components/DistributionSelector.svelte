<script>
  import { SECTIONS, SECTION_TYPES } from '../math/distributions.js';

  let { selected, steps = [], onselect } = $props();

  const renderedSteps = $derived(
    steps.length > 0
      ? steps
      : SECTION_TYPES.map((type, index) => ({
          type,
          label: SECTIONS[type].label,
          number: index + 1,
          current: selected === type,
          reviewed: false,
          locked: false,
          available: true,
        }))
  );

  function stepStatus(step) {
    if (step.current) return 'Current';
    if (step.reviewed) return 'Reviewed';
    if (step.locked) return 'Locked';
    return 'Available';
  }
</script>

<div class="workflow-stepper" role="tablist" aria-label="Modeling workflow">
  {#each renderedSteps as step (step.type)}
    <button
      class="workflow-step"
      class:active={step.current}
      class:reviewed={step.reviewed}
      class:locked={step.locked && !step.current}
      role="tab"
      aria-selected={step.current}
      aria-disabled={step.locked && !step.current}
      onclick={() => onselect(step.type)}
    >
      <span class="step-number">{step.number}</span>
      <span class="step-copy">
        <span class="step-label">{step.label}</span>
        <span class="step-status">{stepStatus(step)}</span>
      </span>
    </button>
  {/each}
</div>

<style>
  .workflow-stepper {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--spacing-2);
  }

  .workflow-step {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
    min-width: 0;
    min-height: 64px;
    padding: var(--spacing-3);
    text-align: left;
    color: var(--color-text-secondary);
    background: var(--color-surface);
    border: 1.5px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    transition: all var(--transition-fast);
  }

  .workflow-step:hover {
    color: var(--color-text);
    border-color: var(--color-border-focus);
  }

  .workflow-step.active {
    color: var(--color-primary);
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-light);
  }

  .workflow-step.locked {
    color: var(--color-text-tertiary);
    background: var(--color-bg);
  }

  .workflow-step.locked:hover {
    color: var(--color-text-secondary);
  }

  .step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    border-radius: 999px;
    font-size: var(--font-size-sm);
    font-weight: 700;
    color: var(--color-text-secondary);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
  }

  .workflow-step.active .step-number,
  .workflow-step.reviewed .step-number {
    color: var(--color-surface);
    background: var(--color-primary);
    border-color: var(--color-primary);
  }

  .workflow-step.locked .step-number {
    color: var(--color-text-tertiary);
    background: var(--color-surface);
    border-color: var(--color-border);
  }

  .step-copy {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .step-label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: currentColor;
    overflow-wrap: anywhere;
  }

  .step-status {
    font-size: var(--font-size-xs);
    font-weight: 600;
    color: var(--color-text-tertiary);
  }

  .workflow-step.active .step-status,
  .workflow-step.reviewed .step-status {
    color: var(--color-primary);
  }

  @media (max-width: 640px) {
    .workflow-stepper {
      grid-template-columns: 1fr;
    }
  }
</style>
