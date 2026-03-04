<script>
  import PlotlyChart from './lib/components/PlotlyChart.svelte';
  import ViewToggle from './lib/components/ViewToggle.svelte';
  import DistributionSelector from './lib/components/DistributionSelector.svelte';
  import ParameterInputs from './lib/components/ParameterInputs.svelte';
  import PanelMode from './lib/components/PanelMode.svelte';
  import PanelAnalytics from './lib/components/PanelAnalytics.svelte';
  import ConfidenceInterval from './lib/components/ConfidenceInterval.svelte';
  import MonteCarloDescription from './lib/components/MonteCarloDescription.svelte';
  import { getState } from './lib/state/app-state.svelte.js';

  const state = getState();
</script>

<main>
  <header>
    <h1>Eliciting an Annual Loss Distribution</h1>
    <p class="subtitle">Visualize and configure annual loss distributions from expert estimates</p>
  </header>

  <section class="input-section">
    <DistributionSelector
      selected={state.activeSection}
      onselect={state.setActiveSection}
    />

    {#if !state.panelActive && state.activeSection !== 'loss'}
      <ParameterInputs
        activeSection={state.activeSection}
        params={state.params}
        validationErrors={state.validationErrors}
        onparamchange={state.setParam}
      />
    {/if}

    {#if state.activeSection !== 'loss'}
      <PanelMode
        panelActive={state.panelActive}
        panelists={state.panelists}
        activeSection={state.activeSection}
        analytics={state.panelAnalytics}
        onadd={state.addPanelist}
        onremove={state.removePanelist}
        onnamchange={state.setPanelistName}
        onparamchange={state.setPanelistParam}
      />
    {/if}

    {#if state.activeSection === 'loss' && state.panelAnalytics}
      <PanelAnalytics sectionKey="frequency" analytics={state.panelAnalytics?.frequency} />
      <PanelAnalytics sectionKey="cost" analytics={state.panelAnalytics?.cost} />
    {/if}
  </section>

  {#if state.activeSection === 'loss'}
    <MonteCarloDescription
      frequencyParams={state.effectiveFrequencyParams}
      costParams={state.effectiveCostParams}
    />
  {/if}

  <section class="chart-section">
    <PlotlyChart chartData={state.chartData} view={state.view} useDollars={state.useDollars} />
    <div class="chart-controls">
      <ViewToggle view={state.view} onchange={state.setView} />
    </div>
  </section>

  <ConfidenceInterval chartData={state.chartData} useDollars={state.useDollars} activeSection={state.activeSection} />
</main>

<footer>
  <a href="https://github.com/magoo/annual-loss-distribution" target="_blank" rel="noopener noreferrer">GitHub</a>
  <span class="separator">&middot;</span>
  <span>Built by Ryan McGeehan</span>
</footer>

<style>
  footer {
    text-align: center;
    margin-top: var(--spacing-8);
    padding-bottom: var(--spacing-12);
    font-size: var(--font-size-sm);
    color: var(--color-text-tertiary);
  }

  footer a {
    color: var(--color-text-tertiary);
    text-decoration: none;
  }

  footer a:hover {
    color: var(--color-text-secondary);
    text-decoration: underline;
  }

  .separator {
    margin: 0 var(--spacing-2);
  }
  main {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-6);
  }

  header {
    text-align: center;
  }

  h1 {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: -0.02em;
  }

  .subtitle {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    margin-top: var(--spacing-1);
  }

  .input-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .chart-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .chart-controls {
    display: flex;
    justify-content: flex-end;
  }

</style>
