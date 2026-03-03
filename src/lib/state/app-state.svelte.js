import { SECTIONS, SECTION_TYPES } from '../math/distributions.js';
import { computeDistribution } from '../math/distributions.js';
import { validate } from '../math/validation.js';

// --- Core state ---
let activeSection = $state('frequency');
let view = $state('pdf');
let frequencyParams = $state({ ...SECTIONS.frequency.defaults });
let costParams = $state({ ...SECTIONS.cost.defaults });

// --- Panel mode state ---
let panelModeActive = $state(false);
let frequencyPanelists = $state([]);
let costPanelists = $state([]);
let nextPanelistId = $state(1);

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
  const fields = SECTIONS[sectionKey].fields;
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
  const fields = SECTIONS[sectionKey].fields;
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
      const variance = values.reduce((sum, v) => sum + (v - avg) ** 2, 0) / values.length;
      const stddev = Math.sqrt(variance);
      analytics[field.key] = { avg, min, max, stddev };
    }
  }
  return analytics;
}

// --- Derived state ---
const effectiveFrequencyParams = $derived.by(() => {
  if (!panelModeActive || frequencyPanelists.length === 0) return frequencyParams;
  return averageParams(frequencyPanelists, 'frequency');
});

const effectiveCostParams = $derived.by(() => {
  if (!panelModeActive || costPanelists.length === 0) return costParams;
  return averageParams(costPanelists, 'cost');
});

const effectiveParams = $derived.by(() => {
  if (activeSection === 'frequency') return effectiveFrequencyParams;
  if (activeSection === 'cost') return effectiveCostParams;
  return {};
});

const frequencyValidationErrors = $derived(validate('frequency', effectiveFrequencyParams));
const costValidationErrors = $derived(validate('cost', effectiveCostParams));

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
  if (!isValid) return null;
  if (activeSection === 'loss') {
    return computeDistribution('loss', null, {
      frequencyParams: effectiveFrequencyParams,
      costParams: effectiveCostParams,
    });
  }
  return computeDistribution(activeSection, effectiveParams);
});

const panelAnalytics = $derived.by(() => {
  if (!panelModeActive) return null;
  if (activeSection === 'loss') {
    if (frequencyPanelists.length === 0 && costPanelists.length === 0) return null;
    return {
      frequency: frequencyPanelists.length > 0 ? computeAnalytics(frequencyPanelists, 'frequency') : null,
      cost: costPanelists.length > 0 ? computeAnalytics(costPanelists, 'cost') : null,
    };
  }
  if (activePanelists.length === 0) return null;
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

function makeDefaultPanelists(sectionKey) {
  return [
    {
      id: nextPanelistId++,
      name: 'Expert 1',
      params: { ...SECTIONS[sectionKey].defaults },
    },
    {
      id: nextPanelistId++,
      name: 'Expert 2',
      params: { ...SECTIONS[sectionKey].defaults },
    },
  ];
}

function togglePanelMode() {
  panelModeActive = !panelModeActive;
  if (panelModeActive && frequencyPanelists.length === 0 && costPanelists.length === 0) {
    frequencyPanelists = makeDefaultPanelists('frequency');
    costPanelists = makeDefaultPanelists('cost');
  }
}

function addPanelist() {
  const active = getActivePanelists();
  const sectionKey = activeSection;
  const newPanelist = {
    id: nextPanelistId++,
    name: `Expert ${active.length + 1}`,
    params: { ...SECTIONS[sectionKey].defaults },
  };
  if (activeSection === 'frequency') {
    frequencyPanelists = [...frequencyPanelists, newPanelist];
  } else if (activeSection === 'cost') {
    costPanelists = [...costPanelists, newPanelist];
  }
}

function removePanelist(id) {
  const active = getActivePanelists();
  if (active.length <= 2) return;
  if (activeSection === 'frequency') {
    frequencyPanelists = frequencyPanelists.filter((p) => p.id !== id);
  } else if (activeSection === 'cost') {
    costPanelists = costPanelists.filter((p) => p.id !== id);
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
    get panelModeActive() { return panelModeActive; },
    get panelists() { return activePanelists; },
    get validationErrors() { return validationErrors; },
    get isValid() { return isValid; },
    get effectiveParams() { return effectiveParams; },
    get chartData() { return chartData; },
    get panelAnalytics() { return panelAnalytics; },
    get useDollars() { return useDollars; },
    setActiveSection,
    setView,
    setParam,
    togglePanelMode,
    addPanelist,
    removePanelist,
    setPanelistName,
    setPanelistParam,
  };
}
