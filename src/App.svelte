<script>
  import PlotlyChart from './lib/components/PlotlyChart.svelte';
  import ViewToggle from './lib/components/ViewToggle.svelte';
  import FocusSlider from './lib/components/FocusSlider.svelte';
  import DistributionSelector from './lib/components/DistributionSelector.svelte';
  import SectionDescription from './lib/components/SectionDescription.svelte';
  import DistributionTypeSelector from './lib/components/DistributionTypeSelector.svelte';
  import ModeDescription from './lib/components/ModeDescription.svelte';
  import ParameterInputs from './lib/components/ParameterInputs.svelte';
  import PanelMode from './lib/components/PanelMode.svelte';
  import PanelAnalytics from './lib/components/PanelAnalytics.svelte';
  import ConfidenceInterval from './lib/components/ConfidenceInterval.svelte';
  import ScenarioMode from './lib/components/ScenarioMode.svelte';
  import { getState } from './lib/state/app-state.svelte.js';

  const appState = getState();

  let confidenceLevel = $state(90);
  let focusPercentile = $state(99.5);

  function handleDistributionTypeSelect(distType) {
    appState.disableScenarioModeForActiveSection();
    appState.setDistType(distType);
  }
</script>

<main>
  <header>
    <h1>Eliciting an Annual Loss Distribution</h1>
    <p class="subtitle">Visualize and configure annual loss distributions from expert estimates</p>
  </header>

  <section class="input-section">
    <div class="workflow-start-card">
      <p class="workflow-start-label">Start Here</p>

      <DistributionSelector
        selected={appState.activeSection}
        onselect={appState.setActiveSection}
      />

      <SectionDescription
        activeSection={appState.activeSection}
        chartData={appState.chartData}
        {confidenceLevel}
        frequencyParams={appState.effectiveFrequencyParams}
        costParams={appState.effectiveCostParams}
        frequencyDistType={appState.frequencyDistType}
        costDistType={appState.costDistType}
        frequencyScenarioMode={appState.frequencyScenarioMode}
        costScenarioMode={appState.costScenarioMode}
        frequencyPanelActive={appState.frequencyPanelActive}
        costPanelActive={appState.costPanelActive}
        frequencyPanelists={appState.frequencyPanelists}
        costPanelists={appState.costPanelists}
        scenarios={appState.scenarios}
      />
    </div>

    {#if appState.activeSection !== 'loss'}
      <div class="distribution-mode-card">
        <DistributionTypeSelector
          selected={appState.activeDistType}
          scenarioActive={appState.scenarioMode}
          onselectdist={handleDistributionTypeSelect}
          onselectscenario={appState.enableScenarioModeForActiveSection}
        />

        <ModeDescription
          activeSection={appState.activeSection}
          activeDistType={appState.activeDistType}
          scenarioActive={appState.scenarioMode}
        />
      </div>
    {/if}

    {#if appState.scenarioMode}
      <section class="chart-section">
        <PlotlyChart chartData={appState.chartData} view={appState.view} useDollars={appState.useDollars} activeSection={appState.activeSection} {focusPercentile} />
        <div class="chart-controls">
          <ViewToggle view={appState.view} onchange={appState.setView} />
          <FocusSlider bind:focusPercentile />
        </div>
      </section>

      <ConfidenceInterval
        chartData={appState.chartData}
        useDollars={appState.useDollars}
        activeSection={appState.activeSection}
        bind:confidenceLevel
        compact={appState.activeSection === 'loss'}
      />

      {#if appState.activeSection !== 'loss'}
        <ScenarioMode
          scenarios={appState.scenarios}
          activeSection={appState.activeSection}
          onadd={appState.addScenario}
          onremove={appState.removeScenario}
          onnamchange={appState.setScenarioName}
          onfreqmethod={appState.setScenarioFrequencyMethod}
          onfreqparam={appState.setScenarioFrequencyParam}
          oncostdisttype={appState.setScenarioCostDistType}
          oncostparam={appState.setScenarioCostParam}
        />
      {/if}
    {:else}
      {#if !appState.panelActive && appState.activeSection !== 'loss'}
        <ParameterInputs
          distConfig={appState.activeDistConfig}
          params={appState.params}
          validationErrors={appState.validationErrors}
          onparamchange={appState.setParam}
        />
      {/if}

      {#if appState.activeSection !== 'loss'}
        <PanelMode
          panelActive={appState.panelActive}
          panelists={appState.panelists}
          activeSection={appState.activeSection}
          distConfig={appState.activeDistConfig}
          distType={appState.activeDistType}
          analytics={appState.panelAnalytics}
          onadd={appState.addPanelist}
          onremove={appState.removePanelist}
          onnamchange={appState.setPanelistName}
          onparamchange={appState.setPanelistParam}
        />
      {/if}

      {#if appState.activeSection === 'loss' && appState.panelAnalytics}
        <PanelAnalytics sectionKey="frequency" distType={appState.frequencyDistType} analytics={appState.panelAnalytics?.frequency} />
        <PanelAnalytics sectionKey="cost" distType={appState.costDistType} analytics={appState.panelAnalytics?.cost} />
      {/if}

      <section class="chart-section">
        <PlotlyChart chartData={appState.chartData} view={appState.view} useDollars={appState.useDollars} activeSection={appState.activeSection} {focusPercentile} />
        <div class="chart-controls">
          <ViewToggle view={appState.view} onchange={appState.setView} />
          <FocusSlider bind:focusPercentile />
        </div>
      </section>

      <ConfidenceInterval
        chartData={appState.chartData}
        useDollars={appState.useDollars}
        activeSection={appState.activeSection}
        bind:confidenceLevel
        compact={appState.activeSection === 'loss'}
      />
    {/if}
  </section>
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

  .workflow-start-card {
    background: linear-gradient(180deg, rgba(67, 97, 238, 0.05) 0%, rgba(67, 97, 238, 0) 52%), var(--color-surface);
    border: 1px solid var(--color-border);
    border-top: 3px solid var(--color-primary);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--spacing-4);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .workflow-start-label {
    font-size: var(--font-size-xs);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-primary);
    margin: 0;
  }

  .distribution-mode-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--spacing-4);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .chart-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .chart-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-2);
    justify-content: flex-end;
  }

</style>
