import { describe, expect, it } from 'vitest';
import { getState } from './app-state.svelte.js';

describe('app scenario mode state', () => {
  it('uses a global scenario mode with shared scenario names and separate inputs', () => {
    const state = getState();

    state.setActiveSection('frequency');
    state.disableScenarioModeForActiveSection();
    state.enableScenarioModeForActiveSection();

    try {
      expect(state.scenarioMode).toBe(true);
      expect(state.frequencyScenarioMode).toBe(true);
      expect(state.costScenarioMode).toBe(true);
      expect(state.scenarios.length).toBeGreaterThan(0);

      const scenarioId = state.scenarios[0].id;
      state.setScenarioName(scenarioId, 'Shared response scenario');
      state.setScenarioFrequencyMethod(scenarioId, 'odds');
      state.setScenarioFrequencyParam(scenarioId, 'odds', 4);

      state.setActiveSection('cost');
      expect(state.scenarioMode).toBe(true);
      expect(state.frequencyScenarioMode).toBe(true);
      expect(state.costScenarioMode).toBe(true);
      expect(state.scenarios[0].name).toBe('Shared response scenario');

      state.setScenarioCostDistType(scenarioId, 'lognormal');
      state.setScenarioCostParam(scenarioId, 'p50', 250000);

      const sharedScenario = state.scenarios.find((scenario) => scenario.id === scenarioId);
      expect(sharedScenario.frequencyParams.odds).toBe(4);
      expect(sharedScenario.costParams.p50).toBe(250000);

      state.disableScenarioModeForActiveSection();
      expect(state.scenarioMode).toBe(false);
      expect(state.frequencyScenarioMode).toBe(false);
      expect(state.costScenarioMode).toBe(false);
      expect(state.scenarios).toHaveLength(0);
    } finally {
      state.disableScenarioModeForActiveSection();
      state.setActiveSection('frequency');
    }
  });
});
