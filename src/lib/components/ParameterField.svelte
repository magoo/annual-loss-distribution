<script>
  let { label, help, value, error, onchange } = $props();

  let touched = $state(false);
  let showError = $derived(touched && error);
  const inputId = `field-${Math.random().toString(36).slice(2, 8)}`;

  function handleInput(e) {
    const raw = e.target.value;
    if (raw === '' || raw === '-') {
      onchange(null);
      return;
    }
    const num = parseFloat(raw);
    onchange(isNaN(num) ? null : num);
  }

  function handleBlur() {
    touched = true;
  }
</script>

<div class="field">
  <label class="label" for={inputId}>{label}</label>
  <input
    id={inputId}
    type="number"
    class:error={showError}
    value={value ?? ''}
    oninput={handleInput}
    onblur={handleBlur}
    step="any"
  />
  <div class="hint-slot">
    {#if showError}
      <span class="error-text">{error}</span>
    {:else if help}
      <span class="help-text">{help}</span>
    {/if}
  </div>
</div>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-1);
    flex: 1;
    min-width: 0;
  }

  .label {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-text);
  }

  .hint-slot {
    min-height: 1.25rem;
    transition: opacity var(--transition-fast);
  }

  .help-text {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
  }

  .error-text {
    font-size: var(--font-size-xs);
    color: var(--color-error);
    font-weight: 500;
  }
</style>
