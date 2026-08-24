import { describe, expect, it } from 'vitest';
import { getState } from './app-state.svelte.js';

describe('app workflow state', () => {
  it('starts on frequency and gates later steps until prerequisites are reviewed', () => {
    const state = getState();

    expect(state.activeSection).toBe('frequency');
    expect(state.frequencyReviewed).toBe(false);
    expect(state.costReviewed).toBe(false);
    expect(state.canVisitSection('frequency')).toBe(true);
    expect(state.canVisitSection('cost')).toBe(false);
    expect(state.canVisitSection('loss')).toBe(false);
    expect(state.requiredSectionFor('cost')).toBe('frequency');
    expect(state.requiredSectionFor('loss')).toBe('frequency');

    state.setActiveSection('cost');
    expect(state.activeSection).toBe('frequency');

    state.setActiveSection('loss');
    expect(state.activeSection).toBe('frequency');
  });

  it('allows intentional override without marking skipped steps reviewed', () => {
    const state = getState();

    state.forceActiveSection('loss');

    expect(state.activeSection).toBe('loss');
    expect(state.frequencyReviewed).toBe(false);
    expect(state.costReviewed).toBe(false);

    state.forceActiveSection('frequency');
  });

  it('marks frequency reviewed and advances to cost', () => {
    const state = getState();

    state.markActiveSectionReviewed();

    expect(state.frequencyReviewed).toBe(true);
    expect(state.costReviewed).toBe(false);
    expect(state.activeSection).toBe('cost');
    expect(state.canVisitSection('cost')).toBe(true);
    expect(state.canVisitSection('loss')).toBe(false);
    expect(state.requiredSectionFor('loss')).toBe('cost');

    state.setActiveSection('loss');
    expect(state.activeSection).toBe('cost');
  });

  it('marks cost reviewed and advances to calculate', () => {
    const state = getState();

    state.markActiveSectionReviewed();

    expect(state.frequencyReviewed).toBe(true);
    expect(state.costReviewed).toBe(true);
    expect(state.activeSection).toBe('loss');
    expect(state.canVisitSection('loss')).toBe(true);
    expect(state.requiredSectionFor('loss')).toBeNull();
  });
});

describe('app scenario mode state', () => {
  it('uses a global scenario mode with shared scenario names and separate inputs', () => {
    const state = getState();

    state.forceActiveSection('frequency');
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

      state.forceActiveSection('cost');
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
      expect(state.scenarios.length).toBeGreaterThan(0);

      state.enableScenarioModeForActiveSection();
      expect(state.scenarios[0].name).toBe('Shared response scenario');
    } finally {
      state.disableScenarioModeForActiveSection();
      state.forceActiveSection('frequency');
    }
  });

  it('does not review a panel while any panelist has incomplete parameters', () => {
    const state = getState();
    state.disableScenarioModeForActiveSection();
    state.forceActiveSection('frequency');
    state.setDistType('lognormal');
    if (!state.frequencyPanelActive) state.addPanelist();

    const panelistCount = state.frequencyPanelists.length;
    state.setDistType('pareto');
    expect(state.frequencyPanelists).toHaveLength(panelistCount);

    state.enableScenarioModeForActiveSection();
    expect(state.frequencyPanelActive).toBe(false);
    expect(state.frequencyPanelists).toHaveLength(panelistCount);
    state.disableScenarioModeForActiveSection();
    expect(state.frequencyPanelActive).toBe(true);

    const panelistId = state.frequencyPanelists[0].id;
    state.setPanelistParam(panelistId, 'p50', null);

    expect(state.isValid).toBe(false);
    state.markActiveSectionReviewed();
    expect(state.activeSection).toBe('frequency');
  });
});
