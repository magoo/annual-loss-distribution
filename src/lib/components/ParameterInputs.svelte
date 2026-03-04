<script>
  import ParameterField from './ParameterField.svelte';

  let { distConfig, params, validationErrors, onparamchange } = $props();

  const fields = $derived(distConfig?.fields ?? []);
  const guidance = $derived(distConfig?.guidance ?? '');
</script>

<div class="params-card">
  {#if guidance}
    <p class="guidance">{guidance}</p>
  {/if}
  <div class="fields-row">
    {#each fields as field (field.key)}
      <ParameterField
        label={field.label}
        help={field.help}
        value={params[field.key]}
        error={validationErrors[field.key]}
        onchange={(v) => onparamchange(field.key, v)}
      />
    {/each}
  </div>
</div>

<style>
  .params-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    padding: var(--spacing-5);
  }

  .guidance {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
    margin-bottom: var(--spacing-4);
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
