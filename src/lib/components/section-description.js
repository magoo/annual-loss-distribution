import { formatCompact } from '../math/formatting.js';
import { DIST_CONFIGS, computeDistribution } from '../math/distributions.js';
import { interpolatePercentile } from '../math/percentile.js';
import { computeScenarioMC } from '../math/scenario-monte-carlo.js';

function formatParamValue(value, useDollars) {
  return Number.isFinite(value) ? formatCompact(value, useDollars) : 'n/a';
}

function formatIncidentValue(value) {
  return Number.isFinite(value) ? formatCompact(Math.max(0, Math.round(value)), false) : 'n/a';
}

function hasChartData(chartData) {
  return Boolean(
    chartData &&
    Array.isArray(chartData.x) &&
    Array.isArray(chartData.yCdf) &&
    chartData.x.length > 0
  );
}

function confidenceBounds(chartData, confidenceLevel) {
  if (!hasChartData(chartData)) return null;

  const lowerP = (100 - confidenceLevel) / 2 / 100;
  const upperP = 1 - lowerP;
  return {
    lower: interpolatePercentile(chartData.x, chartData.yCdf, lowerP),
    upper: interpolatePercentile(chartData.x, chartData.yCdf, upperP),
  };
}

function distributionLabel(distType) {
  return DIST_CONFIGS[distType]?.label ?? 'Lognormal';
}

function scenarioNamesList(scenarios = []) {
  const names = scenarios
    .map((scenario) => scenario?.name?.trim())
    .filter(Boolean);
  return names.length > 0 ? names.join(', ') : 'Unnamed scenarios';
}

function scenarioCountLabel(scenarios = []) {
  const count = scenarios.length;
  return `${count} threat scenario${count === 1 ? '' : 's'}`;
}

function percentileBullets(params, useDollars) {
  return [
    `P50 (typical): ${formatParamValue(params.p50, useDollars)}`,
    `P95 (high): ${formatParamValue(params.p95, useDollars)}`,
    `P99 (extreme): ${formatParamValue(params.p99, useDollars)}`,
  ];
}

function pertBullets(params, useDollars) {
  return [
    `Minimum: ${formatParamValue(params.min, useDollars)}`,
    `Most likely: ${formatParamValue(params.mode, useDollars)}`,
    `Maximum: ${formatParamValue(params.max, useDollars)}`,
  ];
}

function distributionBullets(params = {}, distType, useDollars) {
  if (distType === 'pert') {
    return pertBullets(params, useDollars);
  }
  return percentileBullets(params, useDollars);
}

function buildInputSourceBullet(panelActive, panelists = []) {
  if (!panelActive || panelists.length === 0) {
    return 'Input source: direct analyst estimate';
  }

  const names = panelists
    .map((panelist) => panelist?.name?.trim())
    .filter(Boolean);

  if (names.length > 0) {
    return `Input source: panel of ${panelists.length} expert${panelists.length === 1 ? '' : 's'} (${names.join(', ')})`;
  }

  return `Input source: panel of ${panelists.length} expert${panelists.length === 1 ? '' : 's'}`;
}

function simulationIntro(frequencyScenarioMode, costScenarioMode) {
  if (frequencyScenarioMode && costScenarioMode) {
    return 'This executive summary reflects a scenario-based Monte Carlo model that simulates 10,000 potential years of loss outcomes.';
  }

  if (frequencyScenarioMode || costScenarioMode) {
    return 'This executive summary reflects a hybrid Monte Carlo model that simulates 10,000 potential years and combines scenario-driven inputs with distribution-driven inputs.';
  }

  return 'This executive summary reflects a 100,000-sample Monte Carlo model that combines incident frequency and incident cost to estimate annual loss outcomes.';
}

function simulationBullets(frequencyScenarioMode, costScenarioMode, scenarios) {
  const bullets = [];

  if (frequencyScenarioMode && costScenarioMode) {
    bullets.push('Simulation mode: 10,000-round scenario-based Monte Carlo');
    bullets.push(`Scenario set: ${scenarioCountLabel(scenarios)} (${scenarioNamesList(scenarios)})`);
    return bullets;
  }

  if (frequencyScenarioMode) {
    bullets.push('Simulation mode: 10,000-round hybrid Monte Carlo');
    bullets.push(`Scenario set: Frequency sampled from ${scenarioCountLabel(scenarios)} (${scenarioNamesList(scenarios)})`);
    bullets.push('Cost modeling: Distribution-based');
    return bullets;
  }

  if (costScenarioMode) {
    bullets.push('Simulation mode: 10,000-round hybrid Monte Carlo');
    bullets.push(`Scenario set: Cost sampled from ${scenarioCountLabel(scenarios)} (${scenarioNamesList(scenarios)})`);
    bullets.push('Frequency modeling: Distribution-based');
    return bullets;
  }

  bullets.push('Simulation mode: 100,000-sample distribution-based Monte Carlo');
  bullets.push('Method: Frequency and cost are sampled and multiplied in each run to form annual-loss outcomes');
  return bullets;
}

function computeFrequencyChartData({
  frequencyParams = {},
  frequencyDistType = 'lognormal',
  frequencyScenarioMode = false,
  costScenarioMode = false,
  scenarios = [],
  costParams = {},
  costDistType = 'lognormal',
}) {
  if (frequencyScenarioMode && scenarios.length > 0) {
    return computeScenarioMC(scenarios, 'frequency', {
      frequencyScenarioMode: true,
      costScenarioMode,
      frequencyParams,
      costParams,
      frequencyDistType,
      costDistType,
    });
  }

  return computeDistribution('frequency', frequencyParams, null, frequencyDistType);
}

function computeCostChartData({
  frequencyParams = {},
  costParams = {},
  frequencyDistType = 'lognormal',
  costDistType = 'lognormal',
  frequencyScenarioMode = false,
  costScenarioMode = false,
  scenarios = [],
}) {
  if (costScenarioMode && scenarios.length > 0) {
    return computeScenarioMC(scenarios, 'cost', {
      frequencyScenarioMode,
      costScenarioMode: true,
      frequencyParams,
      costParams,
      frequencyDistType,
      costDistType,
    });
  }

  return computeDistribution('cost', costParams, null, costDistType);
}

function computeLossChartData({
  frequencyParams = {},
  costParams = {},
  frequencyDistType = 'lognormal',
  costDistType = 'lognormal',
  frequencyScenarioMode = false,
  costScenarioMode = false,
  scenarios = [],
}) {
  if ((frequencyScenarioMode || costScenarioMode) && scenarios.length > 0) {
    return computeScenarioMC(scenarios, 'loss', {
      frequencyScenarioMode,
      costScenarioMode,
      frequencyParams,
      costParams,
      frequencyDistType,
      costDistType,
    });
  }

  return computeDistribution('loss', null, {
    frequencyParams,
    costParams,
    frequencyDistType,
    costDistType,
  });
}

function confidenceNarrative({
  lossChartData = null,
  frequencyChartData,
  costChartData,
  confidenceLevel,
}) {
  const incident = confidenceBounds(frequencyChartData, confidenceLevel);
  const cost = confidenceBounds(costChartData, confidenceLevel);
  const loss = confidenceBounds(lossChartData, confidenceLevel);

  const incidentRange = incident
    ? `${formatIncidentValue(incident.lower)} and ${formatIncidentValue(incident.upper)}`
    : 'n/a and n/a';
  const costRange = cost
    ? `${formatParamValue(cost.lower, true)} and ${formatParamValue(cost.upper, true)}`
    : 'n/a and n/a';
  const lossRange = loss
    ? `${formatParamValue(loss.lower, true)} and ${formatParamValue(loss.upper, true)}`
    : 'n/a and n/a';

  return [
    `There is a ${confidenceLevel}% belief that between ${incidentRange} incidents will take place at costs between ${costRange} per incident, with an expected total annual loss between ${lossRange}.`,
  ];
}

function confidenceCopyLines(confidenceStatements) {
  if (!confidenceStatements || confidenceStatements.length === 0) {
    return [];
  }

  return [
    'Confidence Interval Summary:',
    ...confidenceStatements.map((line) => `- ${line}`),
  ];
}

function calculateSummary({
  frequencyParams = {},
  costParams = {},
  frequencyDistType = 'lognormal',
  costDistType = 'lognormal',
  frequencyScenarioMode = false,
  costScenarioMode = false,
  scenarios = [],
  chartData = null,
  confidenceLevel = 90,
  frequencyPanelActive = false,
  costPanelActive = false,
  frequencyPanelists = [],
  costPanelists = [],
}) {
  const freqLabel = distributionLabel(frequencyDistType);
  const costLabel = distributionLabel(costDistType);

  const sections = [
    {
      title: 'Simulation Setup',
      bullets: simulationBullets(frequencyScenarioMode, costScenarioMode, scenarios),
    },
  ];

  const frequencySectionBullets = [
    buildInputSourceBullet(frequencyPanelActive, frequencyPanelists),
  ];

  if (frequencyScenarioMode) {
    frequencySectionBullets.push(`Frequency method: Scenario-based sampling from ${scenarioCountLabel(scenarios)}`);
  } else {
    frequencySectionBullets.push(`Distribution: ${freqLabel}`);
    frequencySectionBullets.push(...distributionBullets(frequencyParams, frequencyDistType, false));
  }

  sections.push({
    title: 'Frequency Inputs',
    bullets: frequencySectionBullets,
  });

  const costSectionBullets = [
    buildInputSourceBullet(costPanelActive, costPanelists),
  ];

  if (costScenarioMode) {
    costSectionBullets.push(`Cost method: Scenario-based sampling from ${scenarioCountLabel(scenarios)}`);
  } else {
    costSectionBullets.push(`Distribution: ${costLabel}`);
    costSectionBullets.push(...distributionBullets(costParams, costDistType, true));
  }

  sections.push({
    title: 'Cost Inputs',
    bullets: costSectionBullets,
  });

  const frequencyChartData = computeFrequencyChartData({
    frequencyParams,
    frequencyDistType,
    frequencyScenarioMode,
    costScenarioMode,
    scenarios,
    costParams,
    costDistType,
  });

  const costChartData = computeCostChartData({
    frequencyParams,
    costParams,
    frequencyDistType,
    costDistType,
    frequencyScenarioMode,
    costScenarioMode,
    scenarios,
  });

  const resolvedLossChartData = hasChartData(chartData)
    ? chartData
    : computeLossChartData({
        frequencyParams,
        costParams,
        frequencyDistType,
        costDistType,
        frequencyScenarioMode,
        costScenarioMode,
        scenarios,
      });

  const confidenceStatements = confidenceNarrative({
    lossChartData: resolvedLossChartData,
    frequencyChartData,
    costChartData,
    confidenceLevel,
  });

  const intro = simulationIntro(frequencyScenarioMode, costScenarioMode);
  const copyLines = [
    'Executive Summary',
    intro,
    '',
    ...confidenceCopyLines(confidenceStatements),
  ];
  for (const section of sections) {
    copyLines.push(`${section.title}:`);
    for (const bullet of section.bullets) {
      copyLines.push(`- ${bullet}`);
    }
  }

  return {
    mode: 'executive',
    title: 'Executive Summary',
    intro,
    confidenceNarrative: confidenceStatements,
    sections,
    copyText: copyLines.join('\n'),
  };
}

export function getSectionDescription({
  activeSection,
  frequencyParams = {},
  costParams = {},
  frequencyDistType = 'lognormal',
  costDistType = 'lognormal',
  frequencyScenarioMode = false,
  costScenarioMode = false,
  scenarios = [],
  chartData = null,
  confidenceLevel = 90,
  frequencyPanelActive = false,
  costPanelActive = false,
  frequencyPanelists = [],
  costPanelists = [],
}) {
  if (activeSection === 'frequency') {
    return {
      mode: 'plain',
      text: 'Use this section to estimate how many incidents you expect over the next year. These annual incident counts become the Frequency input for the Monte Carlo simulation that estimates total yearly losses.',
    };
  }

  if (activeSection === 'cost') {
    return {
      mode: 'plain',
      text: 'Use this section to estimate the typical and high-end cost of a single incident. These per-incident loss values become the Cost input for the Monte Carlo simulation that estimates total yearly losses.',
    };
  }

  return calculateSummary({
    frequencyParams,
    costParams,
    frequencyDistType,
    costDistType,
    frequencyScenarioMode,
    costScenarioMode,
    scenarios,
    chartData,
    confidenceLevel,
    frequencyPanelActive,
    costPanelActive,
    frequencyPanelists,
    costPanelists,
  });
}
