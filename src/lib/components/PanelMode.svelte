<script>
  import PanelModeToggle from './PanelModeToggle.svelte';
  import PanelistRow from './PanelistRow.svelte';
  import PanelAnalytics from './PanelAnalytics.svelte';

  let {
    active,
    panelists,
    activeSection,
    analytics,
    ontoggle,
    onadd,
    onremove,
    onnamchange,
    onparamchange,
  } = $props();

  const isLossTab = $derived(activeSection === 'loss');
</script>

<div class="panel-section">
  <PanelModeToggle {active} {ontoggle} />

  {#if active}
    <div class="panel-content">
      {#if !isLossTab}
        <div class="panelists">
          {#each panelists as panelist (panelist.id)}
            <PanelistRow
              {panelist}
              {activeSection}
              canDelete={panelists.length > 2}
              onremove={() => onremove(panelist.id)}
              onnamchange={(name) => onnamchange(panelist.id, name)}
              onparamchange={(key, val) => onparamchange(panelist.id, key, val)}
            />
          {/each}
        </div>

        <button class="add-btn" onclick={onadd}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          Add Expert
        </button>

        <PanelAnalytics sectionKey={activeSection} {analytics} />
      {:else}
        <PanelAnalytics sectionKey="frequency" analytics={analytics?.frequency} />
        <PanelAnalytics sectionKey="cost" analytics={analytics?.cost} />
      {/if}
    </div>
  {/if}
</div>

<style>
  .panel-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .panel-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .panelists {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .add-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2);
    width: 100%;
    padding: var(--spacing-3);
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-primary);
    background: var(--color-primary-light);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
  }

  .add-btn:hover {
    background: var(--color-primary);
    color: var(--color-surface);
  }
</style>
