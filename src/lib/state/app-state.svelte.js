import { SECTIONS, SECTION_TYPES, DIST_CONFIGS, DIST_TYPES, getDistConfig, DEFAULT_SCENARIOS, SCENARIO_FREQ_CONFIGS, SCENARIO_COST_CONFIGS } from '../math/distributions.js';
import { computeDistribution } from '../math/distributions.js';
import { computeScenarioMC } from '../math/scenario-monte-carlo.js';
import { validate } from '../math/validation.js';

// --- Core state ---
let activeSection = $state('frequency');
let view = $state('pdf');
let frequencyDistType = $state('lognormal');
let costDistType = $state('lognormal');
let frequencyParams = $state({ ...DIST_CONFIGS.lognormal.frequency.defaults });
let costParams = $state({ ...DIST_CONFIGS.lognormal.cost.defaults });

// --- Panel mode state ---
let frequencyPanelists = $state([]);
let costPanelists = $state([]);
let nextPanelistId = $state(1);

// --- Scenario mode state (per-section) ---
let frequencyScenarioMode = $state(false);
let costScenarioMode = $state(false);
let scenarios = $state([]);
let nextScenarioId = $state(1);

// Per-section panel active (derived from panelist count)
const frequencyPanelActive = $derived(frequencyPanelists.length >= 2);
const costPanelActive = $derived(costPanelists.length >= 2);
const activePanelActive = $derived(
  activeSection === 'frequency' ? frequencyPanelActive : costPanelActive
);

// Per-tab derived scenario mode
const activeScenarioMode = $derived(
  activeSection === 'frequency' ? frequencyScenarioMode
  : activeSection === 'cost' ? costScenarioMode
  : (frequencyScenarioMode || costScenarioMode)
);

// --- Derived: active dist type and config ---
const activeDistType = $derived(
  activeSection === 'frequency' ? frequencyDistType :
  activeSection === 'cost' ? costDistType :
  'lognormal'
);

const activeDistConfig = $derived.by(() => {
  if (activeSection === 'loss') return null;
  return getDistConfig(activeDistType, activeSection);
});

// --- Helpers ---
const activePanelists = $derived.by(() => {
  if (activeSection === 'frequency') return frequencyPanelists;
  if (activeSection === 'cost') return costPanelists;
  return [];
});

function getActivePanelists() {
  if (activeSection === 'frequency') return frequencyPanelists;
  if (activeSection === 'cost') return costPanelists;
  return [];
}

function averageParams(panelistList, sectionKey) {
  const distType = sectionKey === 'frequency' ? frequencyDistType : costDistType;
  const config = getDistConfig(distType, sectionKey);
  if (!config) return {};
  const fields = config.fields;
  const averaged = {};
  for (const field of fields) {
    const values = panelistList
      .map((p) => p.params[field.key])
      .filter((v) => v != null && !isNaN(v));
    if (values.length === 0) {
      averaged[field.key] = null;
    } else {
      averaged[field.key] = values.reduce((a, b) => a + b, 0) / values.length;
    }
  }
  return averaged;
}

function computeAnalytics(panelistList, sectionKey) {
  const distType = sectionKey === 'frequency' ? frequencyDistType : costDistType;
  const config = getDistConfig(distType, sectionKey);
  if (!config) return {};
  const fields = config.fields;
  const analytics = {};
  for (const field of fields) {
    const values = panelistList
      .map((p) => p.params[field.key])
      .filter((v) => v != null && !isNaN(v));
    if (values.length === 0) {
      analytics[field.key] = { avg: null, min: null, max: null, stddev: null };
    } else {
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const min = Math.min(...values);
      const max = Math.max(...values);
      const variance = values.reduce((sum, v) => sum + (v - avg) ** 2, 0) / (values.length - 1);
      const stddev = values.length > 1 ? Math.sqrt(variance) : 0;
      analytics[field.key] = { avg, min, max, stddev };
    }
  }
  return analytics;
}

// --- Derived state ---
const effectiveFrequencyParams = $derived.by(() => {
  if (frequencyPanelists.length < 2) return frequencyParams;
  return averageParams(frequencyPanelists, 'frequency');
});

const effectiveCostParams = $derived.by(() => {
  if (costPanelists.length < 2) return costParams;
  return averageParams(costPanelists, 'cost');
});

const effectiveParams = $derived.by(() => {
  if (activeSection === 'frequency') return effectiveFrequencyParams;
  if (activeSection === 'cost') return effectiveCostParams;
  return {};
});

const frequencyValidationErrors = $derived(validate('frequency', effectiveFrequencyParams, frequencyDistType));
const costValidationErrors = $derived(validate('cost', effectiveCostParams, costDistType));

const validationErrors = $derived.by(() => {
  if (activeSection === 'frequency') return frequencyValidationErrors;
  if (activeSection === 'cost') return costValidationErrors;
  return {};
});

const isValid = $derived.by(() => {
  if (activeSection === 'loss') {
    return Object.keys(frequencyValidationErrors).length === 0 &&
           Object.keys(costValidationErrors).length === 0;
  }
  return Object.keys(validationErrors).length === 0;
});

const chartData = $derived.by(() => {
  const freqScen = frequencyScenarioMode && scenarios.length > 0;
  const costScen = costScenarioMode && scenarios.length > 0;

  if (activeSection === 'frequency' && freqScen) {
    return computeScenarioMC(scenarios, 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode: costScen,
    });
  }
  if (activeSection === 'cost' && costScen) {
    // Cost tab needs frequency to generate incident counts for cost sampling
    return computeScenarioMC(scenarios, 'cost', {
      frequencyScenarioMode: true,
      costScenarioMode: true,
    });
  }
  if (activeSection === 'loss' && (freqScen || costScen)) {
    return computeScenarioMC(scenarios, 'loss', {
      frequencyScenarioMode: freqScen,
      costScenarioMode: costScen,
      frequencyParams: effectiveFrequencyParams,
      costParams: effectiveCostParams,
      frequencyDistType,
      costDistType,
    });
  }

  if (!isValid) return null;
  if (activeSection === 'loss') {
    return computeDistribution('loss', null, {
      frequencyParams: effectiveFrequencyParams,
      costParams: effectiveCostParams,
      frequencyDistType,
      costDistType,
    });
  }
  return computeDistribution(activeSection, effectiveParams, null, activeDistType);
});

const panelAnalytics = $derived.by(() => {
  if (activeSection === 'loss') {
    const freq = frequencyPanelists.length >= 2 ? computeAnalytics(frequencyPanelists, 'frequency') : null;
    const cost = costPanelists.length >= 2 ? computeAnalytics(costPanelists, 'cost') : null;
    if (!freq && !cost) return null;
    return { frequency: freq, cost: cost };
  }
  if (activePanelists.length < 2) return null;
  return computeAnalytics(activePanelists, activeSection);
});

const useDollars = $derived(SECTIONS[activeSection].useDollars);

// --- Actions ---
function setActiveSection(section) {
  if (!SECTION_TYPES.includes(section)) return;
  activeSection = section;
}

function setView(v) {
  if (v === 'pdf' || v === 'cdf') {
    view = v;
  }
}

function setParam(key, value) {
  if (activeSection === 'frequency') {
    frequencyParams = { ...frequencyParams, [key]: value };
  } else if (activeSection === 'cost') {
    costParams = { ...costParams, [key]: value };
  }
}

function setDistType(distType) {
  if (!DIST_TYPES.includes(distType)) return;
  if (activeSection === 'loss') return;

  const sectionKey = activeSection;
  const currentDistType = sectionKey === 'frequency' ? frequencyDistType : costDistType;
  if (distType === currentDistType) return;

  const newConfig = getDistConfig(distType, sectionKey);
  if (!newConfig) return;

  // Check if param keys are compatible (lognormal<->pareto share keys, PERT is different)
  const currentConfig = getDistConfig(currentDistType, sectionKey);
  const currentKeys = new Set(currentConfig.fields.map((f) => f.key));
  const newKeys = new Set(newConfig.fields.map((f) => f.key));
  const keysMatch = currentKeys.size === newKeys.size && [...currentKeys].every((k) => newKeys.has(k));

  if (sectionKey === 'frequency') {
    frequencyDistType = distType;
    if (!keysMatch) {
      frequencyParams = { ...newConfig.defaults };
    }
    // Clear panelists when switching dist type (incompatible param structures)
    frequencyPanelists = [];
  } else {
    costDistType = distType;
    if (!keysMatch) {
      costParams = { ...newConfig.defaults };
    }
    costPanelists = [];
  }
}

// --- Scenario actions ---
function seedDefaultScenarios() {
  if (scenarios.length > 0) return;
  scenarios = DEFAULT_SCENARIOS.map((s) => ({
    id: nextScenarioId++,
    name: s.name,
    frequencyMethod: s.frequencyMethod,
    frequencyParams: { ...s.frequencyParams },
    costDistType: s.costDistType,
    costParams: { ...s.costParams },
  }));
}

function enableScenarioModeForActiveSection() {
  if (activeSection === 'frequency') {
    if (frequencyScenarioMode) return;
    frequencyScenarioMode = true;
    frequencyPanelists = [];
    seedDefaultScenarios();
  } else if (activeSection === 'cost') {
    if (costScenarioMode) return;
    costScenarioMode = true;
    costPanelists = [];
    seedDefaultScenarios();
  }
}

function disableScenarioModeForActiveSection() {
  if (activeSection === 'frequency') {
    if (!frequencyScenarioMode) return;
    frequencyScenarioMode = false;
    if (!costScenarioMode) scenarios = [];
  } else if (activeSection === 'cost') {
    if (!costScenarioMode) return;
    costScenarioMode = false;
    if (!frequencyScenarioMode) scenarios = [];
  }
}

function toggleScenarioMode() {
  const sectionScenarioMode = activeSection === 'frequency' ? frequencyScenarioMode
    : activeSection === 'cost' ? costScenarioMode
    : false;

  if (sectionScenarioMode) {
    disableScenarioModeForActiveSection();
  } else {
    enableScenarioModeForActiveSection();
  }
}

function addScenario() {
  scenarios = [...scenarios, {
    id: nextScenarioId++,
    name: `Scenario ${scenarios.length + 1}`,
    frequencyMethod: 'odds',
    frequencyParams: { ...SCENARIO_FREQ_CONFIGS.odds.defaults },
    costDistType: 'lognormal',
    costParams: { ...SCENARIO_COST_CONFIGS.lognormal.defaults },
  }];
}

function removeScenario(id) {
  scenarios = scenarios.filter((s) => s.id !== id);
  if (scenarios.length === 0) {
    frequencyScenarioMode = false;
    costScenarioMode = false;
  }
}

function setScenarioName(id, name) {
  scenarios = scenarios.map((s) => (s.id === id ? { ...s, name } : s));
}

function setScenarioFrequencyMethod(id, method) {
  const config = SCENARIO_FREQ_CONFIGS[method];
  if (!config) return;
  scenarios = scenarios.map((s) =>
    s.id === id ? { ...s, frequencyMethod: method, frequencyParams: { ...config.defaults } } : s
  );
}

function setScenarioFrequencyParam(id, key, value) {
  scenarios = scenarios.map((s) =>
    s.id === id ? { ...s, frequencyParams: { ...s.frequencyParams, [key]: value } } : s
  );
}

function setScenarioCostDistType(id, distType) {
  const config = SCENARIO_COST_CONFIGS[distType];
  if (!config) return;
  scenarios = scenarios.map((s) =>
    s.id === id ? { ...s, costDistType: distType, costParams: { ...config.defaults } } : s
  );
}

function setScenarioCostParam(id, key, value) {
  scenarios = scenarios.map((s) =>
    s.id === id ? { ...s, costParams: { ...s.costParams, [key]: value } } : s
  );
}

function addPanelist() {
  // Mutual exclusivity: adding panelist disables scenario mode for current section
  if (activeSection === 'frequency' && frequencyScenarioMode) {
    frequencyScenarioMode = false;
    if (!costScenarioMode) scenarios = [];
  } else if (activeSection === 'cost' && costScenarioMode) {
    costScenarioMode = false;
    if (!frequencyScenarioMode) scenarios = [];
  }

  const distType = activeSection === 'frequency' ? frequencyDistType : costDistType;
  const config = getDistConfig(distType, activeSection);
  if (!config) return;

  if (activeSection === 'frequency') {
    if (frequencyPanelists.length === 0) {
      frequencyPanelists = [
        { id: nextPanelistId++, name: 'Panelist 1', params: { ...frequencyParams } },
        { id: nextPanelistId++, name: 'Panelist 2', params: { ...config.defaults } },
      ];
      return;
    }
    frequencyPanelists = [...frequencyPanelists, {
      id: nextPanelistId++,
      name: `Panelist ${frequencyPanelists.length + 1}`,
      params: { ...config.defaults },
    }];
  } else if (activeSection === 'cost') {
    if (costPanelists.length === 0) {
      costPanelists = [
        { id: nextPanelistId++, name: 'Panelist 1', params: { ...costParams } },
        { id: nextPanelistId++, name: 'Panelist 2', params: { ...config.defaults } },
      ];
      return;
    }
    costPanelists = [...costPanelists, {
      id: nextPanelistId++,
      name: `Panelist ${costPanelists.length + 1}`,
      params: { ...config.defaults },
    }];
  }
}

function removePanelist(id) {
  if (activeSection === 'frequency') {
    if (frequencyPanelists.length <= 2) {
      frequencyPanelists = [];
    } else {
      frequencyPanelists = frequencyPanelists.filter((p) => p.id !== id);
    }
  } else if (activeSection === 'cost') {
    if (costPanelists.length <= 2) {
      costPanelists = [];
    } else {
      costPanelists = costPanelists.filter((p) => p.id !== id);
    }
  }
}

function setPanelistName(id, name) {
  if (activeSection === 'frequency') {
    frequencyPanelists = frequencyPanelists.map((p) => (p.id === id ? { ...p, name } : p));
  } else if (activeSection === 'cost') {
    costPanelists = costPanelists.map((p) => (p.id === id ? { ...p, name } : p));
  }
}

function setPanelistParam(id, key, value) {
  if (activeSection === 'frequency') {
    frequencyPanelists = frequencyPanelists.map((p) =>
      p.id === id ? { ...p, params: { ...p.params, [key]: value } } : p,
    );
  } else if (activeSection === 'cost') {
    costPanelists = costPanelists.map((p) =>
      p.id === id ? { ...p, params: { ...p.params, [key]: value } } : p,
    );
  }
}

// --- Exports ---
export function getState() {
  return {
    get activeSection() { return activeSection; },
    get view() { return view; },
    get params() { return activeSection === 'frequency' ? frequencyParams : costParams; },
    get panelActive() { return activePanelActive; },
    get panelists() { return activePanelists; },
    get validationErrors() { return validationErrors; },
    get isValid() { return isValid; },
    get effectiveParams() { return effectiveParams; },
    get effectiveFrequencyParams() { return effectiveFrequencyParams; },
    get effectiveCostParams() { return effectiveCostParams; },
    get chartData() { return chartData; },
    get panelAnalytics() { return panelAnalytics; },
    get useDollars() { return useDollars; },
    get frequencyPanelists() { return frequencyPanelists; },
    get costPanelists() { return costPanelists; },
    get frequencyPanelActive() { return frequencyPanelActive; },
    get costPanelActive() { return costPanelActive; },
    get frequencyDistType() { return frequencyDistType; },
    get costDistType() { return costDistType; },
    get activeDistType() { return activeDistType; },
    get activeDistConfig() { return activeDistConfig; },
    get scenarioMode() { return activeScenarioMode; },
    get frequencyScenarioMode() { return frequencyScenarioMode; },
    get costScenarioMode() { return costScenarioMode; },
    get scenarios() { return scenarios; },
    setActiveSection,
    setView,
    setParam,
    setDistType,
    addPanelist,
    removePanelist,
    setPanelistName,
    setPanelistParam,
    toggleScenarioMode,
    enableScenarioModeForActiveSection,
    disableScenarioModeForActiveSection,
    addScenario,
    removeScenario,
    setScenarioName,
    setScenarioFrequencyMethod,
    setScenarioFrequencyParam,
    setScenarioCostDistType,
    setScenarioCostParam,
  };
}
