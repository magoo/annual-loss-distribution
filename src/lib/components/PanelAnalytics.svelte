<script>
  import { SECTIONS } from '../math/distributions.js';

  let { sectionKey, analytics } = $props();

  const section = $derived(SECTIONS[sectionKey]);
  const fields = $derived(section.fields);
  const sectionLabel = $derived(section.label);
  const useDollars = $derived(section.useDollars);

  function fmt(v) {
    if (v == null || isNaN(v)) return '—';
    if (useDollars) {
      return '$' + v.toLocaleString('en-US', { maximumFractionDigits: 0 });
    }
    return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
</script>

{#if analytics}
  <div class="analytics-card">
    <h3 class="analytics-title">Panel Analytics — {sectionLabel}</h3>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Average</th>
            <th>Min</th>
            <th>Max</th>
            <th>Std Dev</th>
          </tr>
        </thead>
        <tbody>
          {#each fields as field (field.key)}
            <tr>
              <td class="param-name">{field.label}</td>
              <td>{fmt(analytics[field.key]?.avg)}</td>
              <td>{fmt(analytics[field.key]?.min)}</td>
              <td>{fmt(analytics[field.key]?.max)}</td>
              <td>{fmt(analytics[field.key]?.stddev)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
{/if}

<style>
  .analytics-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    padding: var(--spacing-5);
  }

  .analytics-title {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: var(--spacing-3);
  }

  .table-wrapper {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
  }

  th {
    text-align: left;
    font-weight: 500;
    color: var(--color-text-secondary);
    padding: var(--spacing-2) var(--spacing-3);
    border-bottom: 1.5px solid var(--color-border);
    white-space: nowrap;
  }

  td {
    padding: var(--spacing-2) var(--spacing-3);
    color: var(--color-text);
    border-bottom: 1px solid var(--color-bg);
    font-variant-numeric: tabular-nums;
  }

  .param-name {
    font-weight: 500;
  }
</style>
