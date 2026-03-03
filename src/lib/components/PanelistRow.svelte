<script>
  import { SECTIONS } from '../math/distributions.js';
  import ParameterField from './ParameterField.svelte';
  import { validate } from '../math/validation.js';

  let { panelist, activeSection, canDelete, onremove, onnamchange, onparamchange } = $props();

  const fields = $derived(SECTIONS[activeSection].fields);
  const errors = $derived(validate(activeSection, panelist.params));
</script>

<div class="panelist-row">
  <div class="panelist-header">
    <input
      type="text"
      class="name-input"
      value={panelist.name}
      oninput={(e) => onnamchange(e.target.value)}
      placeholder="Expert name"
    />
    <button
      class="remove-btn"
      disabled={!canDelete}
      onclick={onremove}
      title="Remove panelist"
      aria-label="Remove panelist"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </button>
  </div>
  <div class="fields-row">
    {#each fields as field (field.key)}
      <ParameterField
        label={field.label}
        help={field.help}
        value={panelist.params[field.key]}
        error={errors[field.key]}
        onchange={(v) => onparamchange(field.key, v)}
      />
    {/each}
  </div>
</div>

<style>
  .panelist-row {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    padding: var(--spacing-4);
    border: 1.5px solid var(--color-border);
  }

  .panelist-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    margin-bottom: var(--spacing-3);
  }

  .name-input {
    flex: 1;
    border: none;
    padding: var(--spacing-1) 0;
    font-weight: 600;
    font-size: var(--font-size-base);
    color: var(--color-text);
    background: transparent;
    outline: none;
  }

  .name-input:focus {
    box-shadow: none;
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
  }

  .remove-btn:hover:not(:disabled) {
    background: var(--color-error-light);
    color: var(--color-error);
  }

  .remove-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
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
